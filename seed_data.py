"""
Seed script — Creates a demo user with pre-existing documents to showcase
the "don't ask twice" feature and provide a rich starting state for demos.

Run: python seed_data.py
"""

import os
import sys
import json
from datetime import datetime, timedelta
from uuid import uuid4

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import init_db, SessionLocal, User, Document, Submission, AuditLog, Reminder
from backend.security.access_control import hash_password, create_session_token
from backend.security.encryption import encrypt_data, encrypt_string
from backend.security.pii_masking import mask_value
from backend.security.audit import log_action


def seed():
    """Seed the database with demo data."""
    print("🌱 Seeding demo data...")

    init_db()
    db = SessionLocal()

    try:
        # Check if demo user already exists
        existing = db.query(User).filter(User.name == "Demo User").first()
        if existing:
            print("⚠️  Demo data already exists. Skipping seed.")
            print(f"   Demo user ID: {existing.id}")
            print(f"   Login: demo@example.com / demo123")
            return

        # ── 1. Create demo user ────────────────────────────────────────
        import hashlib
        email = "demo@example.com"
        user = User(
            id=str(uuid4()),
            name="Demo User",
            email_hash=hashlib.sha256(email.encode()).hexdigest(),
            password_hash=hash_password("demo123"),
            role="user",
            session_token=None,
        )
        db.add(user)
        db.flush()
        print(f"   👤 Created demo user: {user.id}")
        print(f"   📧 Login: demo@example.com / demo123")

        # ── 2. Create pre-existing documents ───────────────────────────
        # Passport (verified, not expired) — reusable across domains
        passport_metadata = {
            "passport_number": "AB1234567",
            "full_name": "Demo User",
            "nationality": "Indian",
            "date_of_birth": "1990-05-15",
            "place_of_issue": "Mumbai",
        }
        passport = Document(
            id=str(uuid4()),
            user_id=user.id,
            doc_type="passport",
            original_filename="passport_scan.pdf",
            status="verified",
            uploaded_at=datetime.utcnow() - timedelta(days=30),
            expires_at=datetime.utcnow() + timedelta(days=365 * 3),  # Valid for 3 more years
            encrypted_blob=encrypt_data(b"[Simulated encrypted passport scan]"),
            encrypted_metadata=encrypt_string(json.dumps(passport_metadata)),
            pii_fields_masked=json.dumps({
                "passport_number": mask_value("AB1234567", "passport_number"),
                "date_of_birth": "****-**-15",
            }),
            linked_domains=json.dumps(["schengen_visa", "home_loan"]),
        )
        db.add(passport)

        # Bank statement (verified, recent)
        bank_metadata = {
            "bank_name": "State Bank of India",
            "account_number": "12345678901234",
            "ifsc": "SBIN0001234",
            "balance": "₹8,50,000",
            "period": "Last 3 months",
        }
        bank_stmt = Document(
            id=str(uuid4()),
            user_id=user.id,
            doc_type="bank_statement",
            original_filename="sbi_statement_3months.pdf",
            status="verified",
            uploaded_at=datetime.utcnow() - timedelta(days=7),
            expires_at=datetime.utcnow() + timedelta(days=83),  # 3 month validity
            encrypted_blob=encrypt_data(b"[Simulated encrypted bank statement]"),
            encrypted_metadata=encrypt_string(json.dumps(bank_metadata)),
            pii_fields_masked=json.dumps({
                "account_number": mask_value("12345678901234", "bank_account"),
            }),
            linked_domains=json.dumps(["schengen_visa", "home_loan"]),
        )
        db.add(bank_stmt)

        # PAN card (verified, no expiry)
        pan_metadata = {
            "pan_number": "ABCDE1234F",
            "full_name": "Demo User",
        }
        pan = Document(
            id=str(uuid4()),
            user_id=user.id,
            doc_type="pan_card",
            original_filename="pan_card.jpg",
            status="verified",
            uploaded_at=datetime.utcnow() - timedelta(days=60),
            expires_at=None,
            encrypted_blob=encrypt_data(b"[Simulated encrypted PAN card image]"),
            encrypted_metadata=encrypt_string(json.dumps(pan_metadata)),
            pii_fields_masked=json.dumps({
                "pan_number": mask_value("ABCDE1234F", "pan"),
            }),
            linked_domains=json.dumps(["home_loan", "gst_registration"]),
        )
        db.add(pan)

        # Passport photo (verified)
        photo = Document(
            id=str(uuid4()),
            user_id=user.id,
            doc_type="passport_photo",
            original_filename="passport_photo.jpg",
            status="verified",
            uploaded_at=datetime.utcnow() - timedelta(days=15),
            expires_at=datetime.utcnow() + timedelta(days=165),  # 6 month validity
            encrypted_blob=encrypt_data(b"[Simulated encrypted passport photo]"),
            encrypted_metadata=encrypt_string(json.dumps({"dimensions": "35x45mm", "background": "white"})),
            pii_fields_masked=json.dumps({}),
            linked_domains=json.dumps(["schengen_visa", "home_loan", "gst_registration"]),
        )
        db.add(photo)

        print(f"   📄 Created 4 pre-existing documents (passport, bank statement, PAN, photo)")

        # ── 3. Create a draft submission ───────────────────────────────
        submission = Submission(
            id=str(uuid4()),
            user_id=user.id,
            domain="schengen_visa",
            status="draft",
            application_data=encrypt_string(json.dumps({
                "destination_countries": ["France", "Italy"],
                "trip_duration_days": 21,
                "travel_month": "December",
                "purpose": "Tourism",
            })),
            created_at=datetime.utcnow() - timedelta(days=2),
            updated_at=datetime.utcnow() - timedelta(days=2),
            external_ref_id=f"VIS-2024-{str(uuid4())[:4].upper()}",
            notes="Initial draft — waiting for travel insurance and hotel booking",
        )
        db.add(submission)
        print(f"   📋 Created draft Schengen visa submission")

        # ── 4. Create reminders ────────────────────────────────────────
        reminders = [
            Reminder(
                id=str(uuid4()),
                user_id=user.id,
                domain="schengen_visa",
                reminder_type="deadline",
                message="Schengen visa appointment window opens in 2 weeks. Ensure all documents are ready.",
                due_date=datetime.utcnow() + timedelta(days=14),
                is_sent=False,
            ),
            Reminder(
                id=str(uuid4()),
                user_id=user.id,
                domain="schengen_visa",
                reminder_type="expiry",
                message="Bank statement will expire in 83 days. Upload a fresh one before visa appointment.",
                due_date=datetime.utcnow() + timedelta(days=75),
                is_sent=False,
            ),
        ]
        for r in reminders:
            db.add(r)
        print(f"   ⏰ Created 2 reminders")

        # ── 5. Create seed audit log entries ───────────────────────────
        seed_audits = [
            ("user", "login", "session", None, "success", "Demo user login"),
            ("user", "upload", "document", passport.id, "success", "Uploaded passport scan"),
            ("system", "verify", "document", passport.id, "success", "Auto-verified passport"),
            ("user", "upload", "document", bank_stmt.id, "success", "Uploaded bank statement"),
            ("system", "verify", "document", bank_stmt.id, "success", "Auto-verified bank statement"),
            ("user", "upload", "document", pan.id, "success", "Uploaded PAN card"),
            ("system", "verify", "document", pan.id, "success", "Auto-verified PAN card"),
            ("user", "upload", "document", photo.id, "success", "Uploaded passport photo"),
            ("agent", "create", "submission", submission.id, "success", "Created Schengen visa draft"),
            ("system", "encrypt", "document", passport.id, "success", "Encrypted passport data at rest"),
            ("system", "pii_mask", "document", passport.id, "success", "Masked PII fields: passport_number"),
            ("agent", "gap_analysis", "submission", submission.id, "success", "Identified 4 missing documents"),
        ]

        base_time = datetime.utcnow() - timedelta(days=2)
        for i, (actor, action, res_type, res_id, result, details) in enumerate(seed_audits):
            audit = AuditLog(
                id=str(uuid4()),
                user_id=user.id,
                actor=actor,
                action=action,
                resource_type=res_type,
                resource_id=res_id,
                details=details,
                timestamp=base_time + timedelta(minutes=i * 5),
                result=result,
                ip_address="127.0.0.1",
            )
            db.add(audit)

        print(f"   📝 Created {len(seed_audits)} audit log entries")

        # ── Commit all ─────────────────────────────────────────────────
        db.commit()
        print("\n✅ Seed data created successfully!")
        print("━" * 50)
        print("  Login credentials:  demo@example.com / demo123")
        print("  Pre-loaded docs:    Passport, Bank Statement, PAN, Photo")
        print("  Draft submission:   Schengen Visa (France, Italy)")
        print("  Active reminders:   2 upcoming")
        print("  Audit trail:        12 entries")
        print("━" * 50)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Seed failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
