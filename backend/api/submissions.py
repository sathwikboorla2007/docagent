"""Submission creation, status tracking, update, and withdrawal endpoints."""

import json
import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.database import get_db, Submission
from backend.security.encryption import encrypt_string, decrypt_string
from backend.security.audit import log_action

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])


class SubmissionCreateBody(BaseModel):
    domain: str
    application_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class SubmissionUpdateBody(BaseModel):
    status: Optional[str] = None
    application_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


@router.post("/create")
def create_submission(body: SubmissionCreateBody, request: Request, db: Session = Depends(get_db)):
    """Create a new application submission."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Generate external reference ID
    prefix = body.domain[:3].upper() if body.domain else "APP"
    ext_ref = f"{prefix}-{datetime.datetime.utcnow().year}-{uuid4().hex[:4].upper()}"

    # Encrypt application data
    enc_data = None
    if body.application_data:
        enc_data = encrypt_string(json.dumps(body.application_data))

    sub = Submission(
        user_id=user.id,
        domain=body.domain,
        status="draft",
        application_data=enc_data,
        external_ref_id=ext_ref,
        notes=body.notes,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    log_action(db, user.id, "agent", "create", "submission", sub.id, "success",
               f"Created {body.domain} submission {ext_ref}")

    return _sub_to_response(sub)


@router.get("")
@router.get("/")
def list_submissions(request: Request, db: Session = Depends(get_db)):
    """List all submissions for the current user."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    subs = db.query(Submission).filter(Submission.user_id == user.id).order_by(Submission.created_at.desc()).all()

    log_action(db, user.id, "user", "read", "submission", None, "success", "Listed submissions")

    return {"submissions": [_sub_to_response(s) for s in subs]}


@router.get("/{sub_id}/status")
def get_submission_status(sub_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Get submission status — STATEFUL: auto-advances status based on time elapsed.
    submitted -> in_review (after 1 min) -> approved (after 3 min).
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sub = db.query(Submission).filter(Submission.id == sub_id, Submission.user_id == user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Simulate state progression
    now = datetime.datetime.utcnow()
    if sub.status == "submitted" and sub.updated_at:
        elapsed = (now - sub.updated_at).total_seconds()
        if elapsed > 180:
            sub.status = "approved"
            sub.updated_at = now
            db.commit()
            log_action(db, user.id, "system", "update", "submission", sub.id, "success", "Auto-approved")
        elif elapsed > 60:
            sub.status = "in_review"
            sub.updated_at = now
            db.commit()
            log_action(db, user.id, "system", "update", "submission", sub.id, "success", "Auto-advanced to review")
    elif sub.status == "in_review" and sub.updated_at:
        elapsed = (now - sub.updated_at).total_seconds()
        if elapsed > 120:
            sub.status = "approved"
            sub.updated_at = now
            db.commit()
            log_action(db, user.id, "system", "update", "submission", sub.id, "success", "Auto-approved after review")

    return {
        "id": sub.id,
        "domain": sub.domain,
        "status": sub.status,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
        "external_ref_id": sub.external_ref_id,
    }


@router.put("/{sub_id}")
def update_submission(sub_id: str, body: SubmissionUpdateBody, request: Request, db: Session = Depends(get_db)):
    """Update a submission's status or data."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sub = db.query(Submission).filter(Submission.id == sub_id, Submission.user_id == user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    if body.status:
        sub.status = body.status
    if body.application_data:
        sub.application_data = encrypt_string(json.dumps(body.application_data))
    if body.notes is not None:
        sub.notes = body.notes

    sub.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(sub)

    log_action(db, user.id, "user", "update", "submission", sub.id, "success",
               f"Updated submission to {sub.status}")

    return _sub_to_response(sub)


@router.delete("/{sub_id}")
def withdraw_submission(sub_id: str, request: Request, db: Session = Depends(get_db)):
    """Withdraw a submission."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sub = db.query(Submission).filter(Submission.id == sub_id, Submission.user_id == user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub.status = "withdrawn"
    sub.updated_at = datetime.datetime.utcnow()
    db.commit()

    log_action(db, user.id, "user", "delete", "submission", sub.id, "success", "Submission withdrawn")

    return {"message": "Submission withdrawn", "id": sub.id}


def _sub_to_response(sub) -> dict:
    return {
        "id": sub.id,
        "domain": sub.domain,
        "status": sub.status,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
        "external_ref_id": sub.external_ref_id,
        "notes": sub.notes,
    }
