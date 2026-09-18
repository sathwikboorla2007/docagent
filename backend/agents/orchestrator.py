"""
Orchestrator Agent — State machine that coordinates the full bureaucratic workflow.
States: PARSE -> REQUIREMENTS -> GAP_ANALYSIS -> PROPOSE_ACTIONS -> EXECUTE -> SCHEDULE -> COMPLETE
"""

from sqlalchemy.orm import Session
from backend.database import User, Submission, Document
from backend.agents.nl_parser import NLParser
from backend.agents.requirement_matcher import RequirementMatcher
from backend.services.document_service import DocumentService
from backend.services.state_store import StateStore
from backend.services.reminder_service import ReminderService
from backend.security.audit import log_action
from datetime import datetime, timedelta

# Singleton state store
_state_store = StateStore()


class Orchestrator:
    """Main orchestrator agent that processes user messages and coordinates sub-agents."""

    STATES = ["PARSE", "REQUIREMENTS", "GAP_ANALYSIS", "PROPOSE_ACTIONS", "EXECUTE", "SCHEDULE", "COMPLETE"]

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.parser = NLParser()
        self.matcher = RequirementMatcher()
        self.doc_service = DocumentService(db)
        self.state_store = _state_store
        self.reminder_service = ReminderService(db)

    def process_message(self, message: str) -> dict:
        """
        Process a natural-language message through the full pipeline.
        Returns a dict matching the ChatResponse schema.
        """
        # ── Step 1: PARSE ──
        parsed = self.parser.parse(message)
        intent = parsed.get("intent", "general_query")
        domain = parsed.get("domain")
        entities = parsed.get("entities", {})

        log_action(self.db, self.user.id, "agent", "parse", "chat", None, "success",
                   f"Intent: {intent}, Domain: {domain}")

        # ── Handle special intents ──
        if intent == "check_status":
            return self._handle_check_status()

        if intent == "upload_document":
            return self._handle_upload_prompt()

        if intent == "list_documents":
            return self._handle_list_documents()

        if intent == "submit_application":
            target_domain = domain or self.state_store.get_session(self.user.id).get("active_domain", "schengen_visa")
            return self._handle_submit_application(target_domain, entities)

        # ── Recover domain from session context if not detected directly ──
        if not domain:
            session_data = self.state_store.get_session(self.user.id)
            if session_data and "active_domain" in session_data:
                # If message contains clarifying entities (like income or dates)
                if entities:
                    domain = session_data["active_domain"]

        # ── Step 2: REQUIREMENTS (if domain detected) ──
        if domain:
            self.state_store.update_session(self.user.id, {"active_domain": domain})
            return self._handle_domain_workflow(domain, entities, parsed)

        # ── Default: general query ──
        return {
            "response": (
                "👋 Welcome! I'm DocuAgent, your bureaucracy management assistant.\n\n"
                "I can help you with:\n"
                "• 🛂 **Schengen Visa** — Travel to Europe\n"
                "• 🏠 **Home Loan** — Residential property financing\n"
                "• 📋 **GST Registration** — Business tax registration\n\n"
                "Just tell me what you need, e.g.:\n"
                "- *\"I'm planning a 3-week trip to France and Italy in December\"*\n"
                "- *\"I want to apply for a home loan of ₹50 lakhs\"*\n"
                "- *\"I need to register for GST as a freelancer\"*"
            ),
            "actions_taken": None,
            "requirements": None,
            "suggestions": ["Apply for Schengen Visa", "Apply for Home Loan", "Register for GST"],
            "workflow_state": "COMPLETE",
            "domain": None,
        }

    def _handle_check_status(self) -> dict:
        """Handle status check intent."""
        submissions = self.db.query(Submission).filter(
            Submission.user_id == self.user.id
        ).order_by(Submission.updated_at.desc()).all()

        if not submissions:
            response = "You don't have any active submissions. Would you like to start a new application?"
        else:
            lines = ["📋 **Your Submissions:**\n"]
            for sub in submissions:
                status_emoji = {"draft": "📝", "submitted": "📤", "in_review": "🔍",
                                "approved": "✅", "rejected": "❌", "withdrawn": "⏹️"}.get(sub.status, "❓")
                lines.append(f"{status_emoji} **{sub.domain.replace('_', ' ').title()}** "
                             f"({sub.external_ref_id}) — Status: **{sub.status.upper()}**")
            response = "\n".join(lines)

        return {
            "response": response,
            "actions_taken": [{"action": "check_status", "result": f"{len(submissions)} submissions found"}],
            "requirements": None,
            "suggestions": None,
            "workflow_state": "COMPLETE",
            "domain": None,
        }

    def _handle_upload_prompt(self) -> dict:
        """Handle upload document intent."""
        return {
            "response": (
                "📄 To upload a document, go to the **Documents** tab and click **Upload**.\n\n"
                "You can upload:\n"
                "• Passport, PAN Card, Aadhaar\n"
                "• Bank Statements, Salary Slips\n"
                "• Travel Insurance, Hotel Bookings\n"
                "• Property Documents\n\n"
                "All uploads are **encrypted at rest** and PII is automatically masked."
            ),
            "actions_taken": None,
            "requirements": None,
            "suggestions": ["Go to Documents", "Check my documents"],
            "workflow_state": "COMPLETE",
            "domain": None,
        }

    def _handle_list_documents(self) -> dict:
        """Handle list documents intent."""
        docs = self.doc_service.get_user_documents(self.user.id)
        if not docs:
            response = "You haven't uploaded any documents yet. Go to the Documents tab to get started!"
        else:
            lines = ["📁 **Your Documents:**\n"]
            for doc in docs:
                status_emoji = {"verified": "✅", "pending": "⏳", "expired": "❌"}.get(doc.status, "❓")
                lines.append(f"{status_emoji} **{doc.doc_type.replace('_', ' ').title()}** "
                             f"({doc.original_filename or 'N/A'}) — {doc.status}")
            response = "\n".join(lines)

        return {
            "response": response,
            "actions_taken": [{"action": "list_documents", "result": f"{len(docs)} documents found"}],
            "requirements": None,
            "suggestions": ["Upload a document", "Apply for visa"],
            "workflow_state": "COMPLETE",
            "domain": None,
        }

    def _handle_domain_workflow(self, domain: str, entities: dict, parsed: dict) -> dict:
        """Handle a domain-specific workflow: requirements + gap analysis."""
        actions_taken = []

        # ── Step 2: REQUIREMENTS ──
        try:
            checklist = self.matcher.get_requirements(domain, entities)
            # Convert RequirementChecklist to list of dicts for gap analysis
            req_list = []
            if hasattr(checklist, 'required_documents'):
                for item in checklist.required_documents:
                    req_list.append({
                        "doc_type": item.doc_type,
                        "description": item.description,
                    })
                if checklist.conditional_requirements:
                    for item in checklist.conditional_requirements:
                        req_list.append({
                            "doc_type": item.doc_type,
                            "description": item.description,
                        })
            else:
                # Fallback if checklist is a list
                req_list = checklist if isinstance(checklist, list) else []

            actions_taken.append({"action": "fetch_requirements", "result": f"{len(req_list)} requirements loaded"})
        except Exception as e:
            req_list = []
            actions_taken.append({"action": "fetch_requirements", "result": f"Error: {e}"})

        # ── Step 3: GAP ANALYSIS ──
        gap = self.doc_service.get_gap_analysis(self.user.id, req_list)
        actions_taken.append({
            "action": "gap_analysis",
            "result": f"{len(gap['met'])} met, {len(gap['missing'])} missing, {len(gap['expired'])} expired"
        })

        # ── Step 4: PROPOSE ACTIONS ──
        display_name = domain.replace("_", " ").title()
        response_text = self._build_response_text(display_name, entities, req_list, gap)

        # ── Step 5: SCHEDULE reminders ──
        try:
            exp_reminders = self.reminder_service.schedule_document_expiry_check(self.user.id)
            if exp_reminders:
                actions_taken.append({
                    "action": "schedule_reminders",
                    "result": f"Scheduled {len(exp_reminders)} document reminder(s)"
                })
        except Exception:
            pass

        suggestions = []
        if gap["missing"]:
            suggestions.append("Upload missing documents")
        if gap["completion_pct"] == 100:
            suggestions.append("Submit application")
        suggestions.append("Check submission status")

        # Check for existing submission
        existing_sub = self.db.query(Submission).filter(
            Submission.user_id == self.user.id,
            Submission.domain == domain,
            Submission.status.in_(["draft", "submitted", "in_review"]),
        ).first()
        if existing_sub:
            suggestions.insert(0, f"Check status of {existing_sub.external_ref_id}")

        # Save context
        self.state_store.set_context(self.user.id, domain, {"entities": entities})

        # Build requirements dict for response
        requirements_dict = {
            "domain": domain,
            "display_name": display_name,
            "total_required": len(req_list),
            "documents_met": gap["met"],
            "documents_missing": gap["missing"],
            "documents_expired": gap["expired"],
            "completion_percentage": gap["completion_pct"],
        }

        log_action(self.db, self.user.id, "agent", "gap_analysis", "submission", None, "success",
                   f"{domain}: {gap['completion_pct']}% complete, {len(gap['missing'])} missing")

        return {
            "response": response_text,
            "actions_taken": actions_taken,
            "requirements": requirements_dict,
            "suggestions": suggestions,
            "workflow_state": "PROPOSE_ACTIONS",
            "domain": domain,
        }

    def _build_response_text(self, display_name: str, entities: dict, requirements: list, gap: dict) -> str:
        """Build a natural, helpful response message."""
        lines = [f"🎯 **{display_name}**\n"]

        # Acknowledge extracted entities
        if entities:
            details = []
            if entities.get("countries"):
                details.append(f"Countries: {', '.join(entities['countries'])}")
            if entities.get("duration_days"):
                details.append(f"Duration: {entities['duration_days']} days")
            if entities.get("amount"):
                details.append(f"Amount: ₹{entities['amount']:,.0f}")
            if entities.get("income"):
                details.append(f"Income: ₹{entities['income']:,.0f}/month")
            if entities.get("month"):
                details.append(f"Travel month: {entities['month']}")
            if details:
                lines.append("📌 " + " | ".join(details) + "\n")

        # Document checklist
        lines.append("**📋 Document Checklist:**\n")
        for req in gap.get("met", []):
            lines.append(f"  ✅ {req['description']}")
        for req in gap.get("expired", []):
            lines.append(f"  ⚠️ {req['description']} *(expired — please re-upload)*")
        for req in gap.get("missing", []):
            lines.append(f"  ❌ {req['description']} *(missing)*")

        # Progress
        pct = gap.get("completion_pct", 0)
        lines.append(f"\n**Progress: {pct}%** — {len(gap['met'])} of {len(requirements)} documents ready")

        # Next steps
        lines.append("")
        if pct >= 100:
            lines.append("🎉 **All documents ready!** You can now submit your application.")
        elif gap["missing"]:
            lines.append(f"📤 **Next step:** Upload the {len(gap['missing'])} missing document(s) to proceed.")
        if gap["expired"]:
            lines.append(f"⚠️ {len(gap['expired'])} document(s) have expired and need to be re-uploaded.")

        return "\n".join(lines)

    def _handle_submit_application(self, domain: str, entities: dict) -> dict:
        """Handle application submission directly from chat."""
        from uuid import uuid4
        import json
        from backend.security.encryption import encrypt_string

        # Load requirements and perform gap analysis
        checklist = self.matcher.get_requirements(domain, entities)
        req_list = []
        if hasattr(checklist, 'required_documents'):
            for item in checklist.required_documents:
                req_list.append({"doc_type": item.doc_type, "description": item.description})
            if checklist.conditional_requirements:
                for item in checklist.conditional_requirements:
                    req_list.append({"doc_type": item.doc_type, "description": item.description})
        else:
            req_list = checklist if isinstance(checklist, list) else []

        gap = self.doc_service.get_gap_analysis(self.user.id, req_list)
        display_name = domain.replace("_", " ").title()

        if gap["completion_pct"] < 100:
            response_text = (
                f"⚠️ **Cannot submit {display_name} application yet.**\n\n"
                f"You are currently at **{gap['completion_pct']}% completion**.\n\n"
                f"Please upload the following missing document(s) first:\n"
                + "\n".join(f"• ❌ {m['description']}" for m in gap["missing"])
            )
            return {
                "response": response_text,
                "actions_taken": [{"action": "submission_check", "result": "blocked_by_missing_documents"}],
                "requirements": {
                    "domain": domain,
                    "display_name": display_name,
                    "total_required": len(req_list),
                    "documents_met": gap["met"],
                    "documents_missing": gap["missing"],
                    "documents_expired": gap["expired"],
                    "completion_percentage": gap["completion_pct"],
                },
                "suggestions": ["Upload missing documents", "Check my documents"],
                "workflow_state": "GAP_ANALYSIS",
                "domain": domain,
            }

        # Check for existing draft to upgrade or create new submission
        sub = self.db.query(Submission).filter(
            Submission.user_id == self.user.id,
            Submission.domain == domain,
            Submission.status == "draft"
        ).first()

        prefix = domain[:3].upper()
        now = datetime.utcnow()

        if sub:
            sub.status = "submitted"
            sub.updated_at = now
            ext_ref = sub.external_ref_id
        else:
            ext_ref = f"{prefix}-{now.year}-{uuid4().hex[:4].upper()}"
            sub = Submission(
                user_id=self.user.id,
                domain=domain,
                status="submitted",
                application_data=encrypt_string(json.dumps(entities or {})),
                external_ref_id=ext_ref,
                notes="Submitted via DocuAgent Chat",
            )
            self.db.add(sub)

        self.db.commit()
        self.db.refresh(sub)

        # Schedule follow-up reminder
        self.reminder_service.create_reminder(
            user_id=self.user.id,
            reminder_type="followup",
            message=f"Follow up on your {display_name} application ({ext_ref})",
            due_date=now + timedelta(days=3),
            domain=domain,
            submission_id=sub.id,
        )

        log_action(self.db, self.user.id, "agent", "submit", "submission", sub.id, "success",
                   f"Submitted {domain} application {ext_ref}")

        response_text = (
            f"🎉 **Application Submitted Successfully!**\n\n"
            f"• **Domain:** {display_name}\n"
            f"• **Reference ID:** `{ext_ref}`\n"
            f"• **Status:** `SUBMITTED`\n\n"
            f"Your application package and all encrypted documents have been filed securely. "
            f"I have scheduled an automated status check and reminder for you."
        )

        return {
            "response": response_text,
            "actions_taken": [
                {"action": "submit_application", "result": f"Submitted {ext_ref}"},
                {"action": "schedule_reminder", "result": "Follow-up scheduled in 3 days"}
            ],
            "requirements": {
                "domain": domain,
                "display_name": display_name,
                "total_required": len(req_list),
                "documents_met": gap["met"],
                "documents_missing": [],
                "documents_expired": [],
                "completion_percentage": 100.0,
            },
            "suggestions": ["Check submission status", "Track my application", "View audit log"],
            "workflow_state": "COMPLETE",
            "domain": domain,
        }
