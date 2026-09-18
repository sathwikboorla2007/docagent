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
