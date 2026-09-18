"""Document storage service with encryption, PII masking, and gap analysis."""

import json
import datetime
from sqlalchemy.orm import Session
from backend.database import Document
from backend.security.encryption import encrypt_data, encrypt_string, decrypt_string
from backend.security.pii_masking import detect_pii_fields, mask_dict
from backend.security.audit import log_action


DOC_TYPE_ALIASES = {
    "identity_proof": ["passport", "pan_card", "aadhaar_card", "id_card"],
    "address_proof": ["passport", "aadhaar_card", "electricity_bill", "utility_bill", "rent_agreement"],
    "address_proof_business": ["electricity_bill", "rent_agreement", "property_tax_receipt", "utility_bill"],
    "salary_slips": ["salary_slip", "salary_slips"],
    "property_documents": ["property_documents", "sale_deed", "title_deed"],
    "business_proof": ["business_registration", "gstin", "shop_act_license", "incorporation_certificate"],
}

DEFAULT_DOMAIN_LINKS = {
    "passport": ["schengen_visa", "home_loan"],
    "bank_statement": ["schengen_visa", "home_loan", "gst_registration"],
    "pan_card": ["home_loan", "gst_registration"],
    "aadhaar_card": ["home_loan", "gst_registration"],
    "passport_photo": ["schengen_visa", "home_loan", "gst_registration"],
    "travel_insurance": ["schengen_visa"],
    "flight_itinerary": ["schengen_visa"],
    "hotel_booking": ["schengen_visa"],
    "salary_slip": ["home_loan"],
    "salary_slips": ["home_loan"],
    "form_16": ["home_loan"],
    "property_documents": ["home_loan"],
    "business_registration": ["gst_registration", "home_loan"],
    "electricity_bill": ["home_loan", "gst_registration"],
}


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    def upload_document(
        self,
        user_id: str,
        doc_type: str,
        file_content: bytes,
        filename: str,
        metadata: dict = None,
        expires_at=None,
        linked_domains: list = None,
    ) -> Document:
        """Upload a document with encryption and PII detection."""
        # Encrypt file content
        encrypted_blob = encrypt_data(file_content)

        # Process metadata: detect PII, mask, encrypt
        encrypted_metadata = None
        pii_fields_masked = None
        if metadata:
            pii_fields = detect_pii_fields(metadata)
            if pii_fields:
                masked = mask_dict(metadata, pii_fields)
                pii_fields_masked = json.dumps(masked)
            encrypted_metadata = encrypt_string(json.dumps(metadata))

        # Auto-detect linked domains if not explicitly provided
        if not linked_domains:
            linked_domains = DEFAULT_DOMAIN_LINKS.get(doc_type, [])

        # Serialize linked domains
        linked_domains_json = json.dumps(linked_domains) if linked_domains else None

        doc = Document(
            user_id=user_id,
            doc_type=doc_type,
            original_filename=filename,
            status="pending",
            encrypted_blob=encrypted_blob,
            encrypted_metadata=encrypted_metadata,
            pii_fields_masked=pii_fields_masked,
            expires_at=expires_at,
            linked_domains=linked_domains_json,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        log_action(self.db, user_id, "user", "upload", "document", doc.id, "success",
                   f"Uploaded {doc_type}: {filename}")

        return doc

    def get_user_documents(self, user_id: str) -> list:
        """Get all documents for a user."""
        return self.db.query(Document).filter(Document.user_id == user_id).all()

    def get_document(self, user_id: str, doc_id: str):
        """Get a specific document, verifying ownership."""
        return self.db.query(Document).filter(
            Document.id == doc_id, Document.user_id == user_id
        ).first()

    def delete_document(self, user_id: str, doc_id: str) -> bool:
        """Delete a document after verifying ownership."""
        doc = self.get_document(user_id, doc_id)
        if doc:
            self.db.delete(doc)
            self.db.commit()
            log_action(self.db, user_id, "user", "delete", "document", doc_id, "success",
                       f"Deleted document {doc_id}")
            return True
        return False

    def check_document_exists(self, user_id: str, doc_type: str):
        """Check if a user has a document of a given type."""
        return self.db.query(Document).filter(
            Document.user_id == user_id, Document.doc_type == doc_type
        ).first()

    def get_gap_analysis(self, user_id: str, required_docs: list) -> dict:
        """
        Compare required documents against user's stored documents.
        Supports intelligent aliasing (e.g. identity_proof met by passport or pan_card).
        Returns: {met: [...], missing: [...], expired: [...], completion_pct: float}
        """
        user_docs = self.get_user_documents(user_id)
        now = datetime.datetime.utcnow()

        # Build lookup by doc_type
        user_doc_map = {}
        for doc in user_docs:
            user_doc_map[doc.doc_type] = doc

        met = []
        missing = []
        expired = []

        for req in required_docs:
            # Handle both dict and RequirementItem objects
            if isinstance(req, dict):
                doc_type = req.get("doc_type") or req.get("type", "")
                description = req.get("description", doc_type)
            else:
                doc_type = getattr(req, "doc_type", "") or getattr(req, "type", "")
                description = getattr(req, "description", doc_type)

            req_info = {"doc_type": doc_type, "description": description}

            # Check direct match or alias match
            doc = None
            if doc_type in user_doc_map:
                doc = user_doc_map[doc_type]
            elif doc_type in DOC_TYPE_ALIASES:
                for alias in DOC_TYPE_ALIASES[doc_type]:
                    if alias in user_doc_map:
                        doc = user_doc_map[alias]
                        req_info["reused_from"] = alias
                        break

            if doc:
                if doc.expires_at and doc.expires_at < now:
                    req_info["status"] = "expired"
                    expired.append(req_info)
                elif doc.status in ("verified", "pending"):
                    req_info["status"] = "met"
                    met.append(req_info)
                else:
                    req_info["status"] = "missing"
                    missing.append(req_info)
            else:
                req_info["status"] = "missing"
                missing.append(req_info)

        total = len(required_docs)
        completion_pct = (len(met) / total) * 100 if total > 0 else 100.0

        return {
            "met": met,
            "missing": missing,
            "expired": expired,
            "completion_pct": round(completion_pct, 1),
        }
