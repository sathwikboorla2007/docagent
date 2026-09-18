"""Document upload, listing, retrieval, and deletion endpoints."""

import json
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.services.document_service import DocumentService
from backend.security.audit import log_action
from backend.security.pii_masking import mask_value

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    metadata_json: Optional[str] = Form(None),
    expires_at: Optional[str] = Form(None),
    linked_domains_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a document with encryption and PII masking."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    content = await file.read()
    metadata = json.loads(metadata_json) if metadata_json else None
    linked_domains = json.loads(linked_domains_json) if linked_domains_json else None

    # Parse expires_at if provided
    exp = None
    if expires_at:
        from datetime import datetime
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            pass

    service = DocumentService(db)
    doc = service.upload_document(
        user_id=user.id,
        doc_type=doc_type,
        file_content=content,
        filename=file.filename or "unknown",
        metadata=metadata,
        expires_at=exp,
        linked_domains=linked_domains,
    )

    return _doc_to_response(doc)


@router.get("")
@router.get("/")
def list_documents(request: Request, db: Session = Depends(get_db)):
    """List all documents for the current user (PII masked)."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = DocumentService(db)
    docs = service.get_user_documents(user.id)

    log_action(db, user.id, "user", "read", "document", None, "success", "Listed documents")

    return {
        "documents": [_doc_to_response(d) for d in docs],
        "total": len(docs),
    }


@router.get("/{doc_id}")
def get_document(doc_id: str, request: Request, db: Session = Depends(get_db)):
    """Get a single document by ID (PII masked)."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = DocumentService(db)
    doc = service.get_document(user.id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    log_action(db, user.id, "user", "read", "document", doc_id, "success", f"Accessed document {doc_id}")

    return _doc_to_response(doc)


@router.delete("/{doc_id}")
def delete_document(doc_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a document."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = DocumentService(db)
    success = service.delete_document(user.id, doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"message": "Document deleted", "id": doc_id}


def _doc_to_response(doc) -> dict:
    """Convert a Document model to a response dict with masked PII."""
    import json as _json

    pii_masked = None
    if doc.pii_fields_masked:
        try:
            pii_masked = _json.loads(doc.pii_fields_masked)
        except (ValueError, TypeError):
            pii_masked = {}

    linked = None
    if doc.linked_domains:
        try:
            linked = _json.loads(doc.linked_domains)
        except (ValueError, TypeError):
            linked = []

    return {
        "id": doc.id,
        "doc_type": doc.doc_type,
        "original_filename": doc.original_filename,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
        "pii_fields_masked": pii_masked,
        "linked_domains": linked,
    }
