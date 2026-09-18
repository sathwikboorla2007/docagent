"""Reminders endpoint — list, dismiss, and scan proactive reminders."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services.reminder_service import ReminderService
from backend.security.audit import log_action

router = APIRouter(prefix="/api/reminders", tags=["Reminders"])


@router.get("")
@router.get("/")
def get_reminders(request: Request, db: Session = Depends(get_db)):
    """Get all reminders for the authenticated user."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = ReminderService(db)
    reminders = service.get_user_reminders(user.id)

    log_action(db, user.id, "user", "read", "reminder", None, "success", "Listed reminders")

    return {
        "reminders": [
            {
                "id": r.id,
                "reminder_type": r.reminder_type,
                "message": r.message,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "domain": r.domain,
                "is_sent": r.is_sent,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reminders
        ],
        "total": len(reminders),
    }


@router.post("/{reminder_id}/dismiss")
def dismiss_reminder(reminder_id: str, request: Request, db: Session = Depends(get_db)):
    """Mark a reminder as dismissed/completed."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = ReminderService(db)
    success = service.dismiss_reminder(user.id, reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")

    log_action(db, user.id, "user", "update", "reminder", reminder_id, "success", "Dismissed reminder")
    return {"message": "Reminder dismissed", "id": reminder_id}


@router.delete("/{reminder_id}")
def delete_reminder(reminder_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a reminder."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = ReminderService(db)
    success = service.delete_reminder(user.id, reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")

    log_action(db, user.id, "user", "delete", "reminder", reminder_id, "success", "Deleted reminder")
    return {"message": "Reminder deleted", "id": reminder_id}


@router.post("/scan")
def scan_expirations(request: Request, db: Session = Depends(get_db)):
    """Proactively scan documents for expiration and generate reminders."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = ReminderService(db)
    created = service.schedule_document_expiry_check(user.id)

    log_action(db, user.id, "system", "scan", "reminder", None, "success", f"Scanned documents, created {len(created)} reminders")
    return {
        "message": f"Scan completed. {len(created)} reminder(s) generated.",
        "count": len(created),
    }
