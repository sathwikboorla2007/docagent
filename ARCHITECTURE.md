# Architecture & Interface Specification
# ======================================
# This file defines EXACT interfaces for all modules.
# Every backend file MUST use these exact imports, class names, and function signatures.

## Project Structure
```
bureaucracy-agent/
├── requirements.txt
├── seed_data.py
├── bureaucracy_agent.db          (auto-created)
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── schemas.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── pii_masking.py
│   │   ├── access_control.py
│   │   ├── audit.py
│   │   └── middleware.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── requirement_matcher.py
│   │   └── nl_parser.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_service.py
│   │   ├── state_store.py
│   │   └── reminder_service.py
│   └── api/
│       ├── __init__.py
│       ├── documents.py
│       ├── submissions.py
│       ├── users.py
│       ├── audit_routes.py
│       └── chat.py
├── config/
│   └── domains/
│       ├── schengen_visa.yaml
│       ├── home_loan.yaml
│       └── gst_registration.yaml
└── frontend/
    ├── index.html
    ├── styles.css
    └── app.js
```

## 1. Database Models (backend/database.py)

```python
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
```

## 2. Pydantic Schemas (backend/schemas.py)

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# -- Users --
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email_masked: str
    role: str
    created_at: datetime

# -- Documents --
class DocumentUpload(BaseModel):
    doc_type: str
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    linked_domains: Optional[List[str]] = None

class DocumentResponse(BaseModel):
    id: str
    doc_type: str
    original_filename: Optional[str]
    status: str
    uploaded_at: datetime
    expires_at: Optional[datetime]
    pii_fields_masked: Optional[Dict[str, str]]
    linked_domains: Optional[List[str]]

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

# -- Submissions --
class SubmissionCreate(BaseModel):
    domain: str
    application_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class SubmissionUpdate(BaseModel):
    status: Optional[str] = None
    application_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class SubmissionResponse(BaseModel):
    id: str
    domain: str
    status: str
    created_at: datetime
    updated_at: datetime
    external_ref_id: Optional[str]
    notes: Optional[str]

class SubmissionStatusResponse(BaseModel):
    id: str
    domain: str
    status: str
    updated_at: datetime
    external_ref_id: Optional[str]

# -- Chat --
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    actions_taken: Optional[List[Dict[str, Any]]] = None
    requirements: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    workflow_state: Optional[str] = None
    domain: Optional[str] = None

# -- Audit --
class AuditLogEntry(BaseModel):
    id: str
    user_id: Optional[str]
    actor: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[str]
    timestamp: datetime
    result: str

class AuditLogResponse(BaseModel):
    entries: List[AuditLogEntry]
    total: int
    page: int
    per_page: int

# -- Reminders --
class ReminderResponse(BaseModel):
    id: str
    reminder_type: str
    message: str
    due_date: datetime
    domain: Optional[str]
    is_sent: bool

# -- Requirements --
class RequirementItem(BaseModel):
    doc_type: str
    description: str
    is_conditional: bool = False
    condition_expr: Optional[str] = None
    status: Optional[str] = None   # met | missing | expired

class RequirementChecklist(BaseModel):
    domain: str
    display_name: str
    required_documents: List[RequirementItem]
    conditional_requirements: Optional[List[RequirementItem]] = None

class GapAnalysisResult(BaseModel):
    domain: str
    total_required: int
    documents_met: List[RequirementItem]
    documents_missing: List[RequirementItem]
    documents_expired: List[RequirementItem]
    completion_percentage: float
```

## 3. Security Layer Interfaces

### encryption.py
```python
# MASTER_KEY loaded from env var BUREAUCRACY_MASTER_KEY or a default (for demo)
def get_encryption_key() -> bytes: ...
def encrypt_data(plaintext: bytes) -> bytes: ...       # returns nonce + ciphertext + tag
def decrypt_data(ciphertext: bytes) -> bytes: ...
def encrypt_string(text: str) -> str: ...              # returns base64-encoded encrypted
def decrypt_string(encrypted: str) -> str: ...
```

### pii_masking.py
```python
MASKING_PATTERNS = {
    "passport_number": r"[A-Z]\d{7}",
    "aadhaar": r"\d{12}",
    "pan": r"[A-Z]{5}\d{4}[A-Z]",
    "bank_account": r"\d{9,18}",
    "phone": r"\+?\d{10,13}",
    "email": r"[^@]+@[^@]+\.[^@]+",
    "credit_card": r"\d{13,19}",
}
def mask_value(value: str, field_type: str = None) -> str: ...  # "AB1234567" -> "****4567"
def mask_dict(data: dict, fields_to_mask: list = None) -> dict: ...
def detect_pii_fields(data: dict) -> list[str]: ...
def unmask_value(masked: str, original: str, permission_granted: bool = False) -> str: ...
```

### access_control.py
```python
from backend.database import User, get_db
def hash_password(password: str) -> str: ...
def verify_password(password: str, hashed: str) -> bool: ...
def create_session_token(user_id: str) -> str: ...
def get_current_user(db: Session, token: str) -> User | None: ...
def verify_resource_access(db: Session, user: User, resource_type: str, resource_id: str) -> bool: ...
def require_role(user: User, required_role: str) -> bool: ...
```

### audit.py
```python
from backend.database import AuditLog, SessionLocal
def log_action(
    db,
    user_id: str | None,
    actor: str,           # "user" | "agent" | "system"
    action: str,          # "create" | "read" | "update" | "delete" | "login" | "upload" | "submit" | "access_denied"
    resource_type: str | None = None,
    resource_id: str | None = None,
    result: str = "success",
    details: str | None = None,
    ip_address: str | None = None,
) -> AuditLog: ...
```

### middleware.py
```python
# FastAPI middleware class: SecurityMiddleware(BaseHTTPMiddleware)
# - Extracts Authorization header
# - Validates session token
# - Injects user into request.state
# - Auto-logs every request to audit trail
# - Skips auth for: POST /api/users/register, POST /api/users/login, GET /frontend files, GET /api/health
```

## 4. Domain Config YAML Schema
```yaml
domain: string                        # machine name, e.g. "schengen_visa"
display_name: string                  # human-readable name
description: string                   # overview
required_documents:
  - type: string                      # doc_type matching Document.doc_type
    description: string
    expiry_check: bool                 # whether to check expiry
    min_validity_days: int             # min days of validity remaining
conditional_requirements:
  - condition: string                 # expression like "trip_duration > 90"
    then_require:
      - type: string
        description: string
eligibility_rules:                    # (optional) for domains like home_loan
  - rule: string                      # expression like "monthly_income * 60 >= loan_amount"
    message: string                   # human-readable explanation
extraction_patterns:                  # NL extraction hints
  field_name: regex_pattern
```

## 5. API Endpoints Contract

### Users
```
POST /api/users/register    Body: UserCreate       -> UserResponse + session_token
POST /api/users/login       Body: UserLogin        -> {user: UserResponse, session_token: str}
GET  /api/users/me          Auth required          -> UserResponse
```

### Documents
```
POST   /api/documents/upload    Auth + Form(file, doc_type, metadata_json?, expires_at?, linked_domains_json?)  -> DocumentResponse
GET    /api/documents           Auth    -> DocumentListResponse
GET    /api/documents/{id}      Auth    -> DocumentResponse
DELETE /api/documents/{id}      Auth    -> {message, id}
```

### Submissions
```
POST   /api/submissions/create      Auth + Body: SubmissionCreate     -> SubmissionResponse
GET    /api/submissions             Auth                              -> {submissions: List[SubmissionResponse]}
GET    /api/submissions/{id}/status Auth                              -> SubmissionStatusResponse
PUT    /api/submissions/{id}        Auth + Body: SubmissionUpdate     -> SubmissionResponse
DELETE /api/submissions/{id}        Auth                              -> {message, id}
```

### Chat (Agent)
```
POST /api/chat    Auth + Body: ChatMessage    -> ChatResponse
```

### Audit
```
GET /api/audit/log    Auth + Query(?page, ?per_page, ?action, ?resource_type)    -> AuditLogResponse
```

### Reminders
```
GET /api/reminders    Auth    -> {reminders: List[ReminderResponse]}
```

### Health
```
GET /api/health    -> {status: "ok", timestamp: ...}
```

## 6. Services Interfaces

### DocumentService (backend/services/document_service.py)
```python
class DocumentService:
    def __init__(self, db: Session): ...
    def upload_document(self, user_id, doc_type, file_content, filename, metadata=None, expires_at=None, linked_domains=None) -> Document: ...
    def get_user_documents(self, user_id) -> list[Document]: ...
    def get_document(self, user_id, doc_id) -> Document | None: ...
    def delete_document(self, user_id, doc_id) -> bool: ...
    def check_document_exists(self, user_id, doc_type) -> Document | None: ...
    def get_gap_analysis(self, user_id, required_docs: list[dict]) -> dict: ...
    # gap_analysis returns: {met: [...], missing: [...], expired: [...], completion_pct: float}
```

### StateStore (backend/services/state_store.py)
```python
class StateStore:
    """In-memory + DB-backed session state for user workflows"""
    def __init__(self): ...
    def get_session(self, user_id: str) -> dict: ...
    def update_session(self, user_id: str, data: dict): ...
    def clear_session(self, user_id: str): ...
    def get_context(self, user_id: str, domain: str) -> dict: ...
    def set_context(self, user_id: str, domain: str, context: dict): ...
```

### ReminderService (backend/services/reminder_service.py)
```python
class ReminderService:
    def __init__(self, db: Session): ...
    def create_reminder(self, user_id, reminder_type, message, due_date, domain=None, submission_id=None) -> Reminder: ...
    def get_user_reminders(self, user_id) -> list[Reminder]: ...
    def check_and_send_due_reminders(self) -> list[Reminder]: ...
    def schedule_document_expiry_check(self, user_id): ...
```

## 7. Agents Interfaces

### NLParser (backend/agents/nl_parser.py)
```python
class NLParser:
    def parse(self, message: str) -> dict:
        """Returns: {
            intent: str,           # new_application | check_status | upload_document | general_query | list_documents
            domain: str | None,    # schengen_visa | home_loan | gst_registration
            entities: {            # extracted entities
                countries: list[str],
                duration_days: int | None,
                amount: float | None,
                currency: str | None,
                income: float | None,
                month: str | None,
                ...
            },
            confidence: float,
            raw_message: str,
        }"""
```

### RequirementMatcher (backend/agents/requirement_matcher.py)
```python
class RequirementMatcher:
    def __init__(self, config_dir: str = "config/domains"): ...
    def load_configs(self): ...
    def get_requirements(self, domain: str, context: dict = None) -> RequirementChecklist: ...
    def evaluate_eligibility(self, domain: str, context: dict) -> dict: ...
    def list_domains(self) -> list[str]: ...
```

### Orchestrator (backend/agents/orchestrator.py)
```python
class Orchestrator:
    """State machine: PARSE -> REQUIREMENTS -> GAP_ANALYSIS -> PROPOSE_ACTIONS -> EXECUTE -> SCHEDULE -> COMPLETE"""
    def __init__(self, db: Session, user: User): ...
    def process_message(self, message: str) -> ChatResponse: ...
    # Internally calls NLParser, RequirementMatcher, DocumentService, StateStore
    # Returns ChatResponse with response text, actions taken, requirements, suggestions
```
