import json
import datetime
from sqlalchemy.orm import Session
from backend.database import Reminder, Document

class ReminderService:
    def __init__(self, db: Session):
        self.db = db
        
    def create_reminder(self, user_id, reminder_type, message, due_date, domain=None, submission_id=None) -> Reminder:
        # Avoid creating exact duplicate active reminder
        existing = self.db.query(Reminder).filter(
            Reminder.user_id == user_id,
            Reminder.reminder_type == reminder_type,
            Reminder.message == message,
            Reminder.is_sent == False
        ).first()
        if existing:
            return existing

        reminder = Reminder(
            user_id=user_id,
            reminder_type=reminder_type,
            message=message,
            due_date=due_date,
            domain=domain,
            submission_id=submission_id,
            is_sent=False
        )
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder
        
    def get_user_reminders(self, user_id: str) -> list[Reminder]:
        return self.db.query(Reminder).filter(
            Reminder.user_id == user_id
        ).order_by(Reminder.is_sent.asc(), Reminder.due_date.asc()).all()
        
    def check_and_send_due_reminders(self) -> list[Reminder]:
        now = datetime.datetime.utcnow()
        due_reminders = self.db.query(Reminder).filter(Reminder.due_date <= now, Reminder.is_sent == False).all()
        for r in due_reminders:
            r.is_sent = True
        self.db.commit()
        return due_reminders

    def dismiss_reminder(self, user_id: str, reminder_id: str) -> bool:
        reminder = self.db.query(Reminder).filter(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id
        ).first()
        if reminder:
            reminder.is_sent = True
            self.db.commit()
            return True
        return False

    def delete_reminder(self, user_id: str, reminder_id: str) -> bool:
        reminder = self.db.query(Reminder).filter(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id
        ).first()
        if reminder:
            self.db.delete(reminder)
            self.db.commit()
            return True
        return False
        
    def schedule_document_expiry_check(self, user_id: str) -> list[Reminder]:
        """Check for documents expiring within 90 days or already expired and create reminders."""
        now = datetime.datetime.utcnow()
        ninety_days = now + datetime.timedelta(days=90)
        docs = self.db.query(Document).filter(
            Document.user_id == user_id,
            Document.expires_at.isnot(None)
        ).all()
        
        created = []
        for doc in docs:
            filename = doc.original_filename or doc.doc_type
            doc_name = doc.doc_type.replace('_', ' ').title()
            
            # Format domain if available
            domain_label = None
            if doc.linked_domains:
                try:
                    domains = json.loads(doc.linked_domains)
                    if isinstance(domains, list) and domains:
                        domain_label = ", ".join(d.replace('_', ' ').title() for d in domains)
                except Exception:
                    domain_label = str(doc.linked_domains)

            if doc.expires_at <= now:
                # Already expired
                exp_date_str = doc.expires_at.strftime('%Y-%m-%d')
                r = self.create_reminder(
                    user_id=user_id,
                    reminder_type="expiry",
                    message=f"Urgent: Your {doc_name} ({filename}) expired on {exp_date_str}. Please re-upload.",
                    due_date=now,
                    domain=domain_label
                )
                created.append(r)
            elif doc.expires_at <= ninety_days:
                # Expiring soon
                days_left = (doc.expires_at - now).days
                exp_date_str = doc.expires_at.strftime('%Y-%m-%d')
                r = self.create_reminder(
                    user_id=user_id,
                    reminder_type="expiry",
                    message=f"Reminder: Your {doc_name} ({filename}) expires in {days_left} days on {exp_date_str}.",
                    due_date=max(now, doc.expires_at - datetime.timedelta(days=14)),
                    domain=domain_label
                )
                created.append(r)
                
        return created
