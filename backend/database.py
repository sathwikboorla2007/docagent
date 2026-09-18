import os
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, LargeBinary, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./bureaucracy_agent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    email_hash = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")       # user | admin
    session_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    doc_type = Column(String, nullable=False)    # passport, bank_statement, travel_insurance, etc.
    original_filename = Column(String, nullable=True)
    status = Column(String, default="pending")   # pending | verified | expired
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    encrypted_blob = Column(LargeBinary, nullable=True)
    encrypted_metadata = Column(Text, nullable=True)   # encrypted JSON string
    pii_fields_masked = Column(Text, nullable=True)     # JSON: {"passport_number": "****5678"}
    linked_domains = Column(Text, nullable=True)        # JSON array: ["schengen_visa", "home_loan"]

class DomainRequirement(Base):
    __tablename__ = "domain_requirements"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    domain = Column(String, nullable=False)
    doc_type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_conditional = Column(Boolean, default=False)
    condition_expr = Column(String, nullable=True)      # e.g. "trip_duration > 90"
    priority = Column(Integer, default=0)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    domain = Column(String, nullable=False)
    status = Column(String, default="draft")    # draft | submitted | in_review | approved | rejected
    application_data = Column(Text, nullable=True)      # encrypted JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    external_ref_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, nullable=True)
    actor = Column(String, nullable=False)      # user | agent | system
    action = Column(String, nullable=False)     # create | read | update | delete | login | upload | submit | etc.
    resource_type = Column(String, nullable=True)  # document | submission | user | session
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)       # JSON with extra context
    timestamp = Column(DateTime, default=datetime.utcnow)
    result = Column(String, nullable=False)     # success | denied | error
    ip_address = Column(String, nullable=True)

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    domain = Column(String, nullable=True)
    submission_id = Column(String, nullable=True)
    reminder_type = Column(String, nullable=False)   # expiry | deadline | appointment | followup
    message = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
