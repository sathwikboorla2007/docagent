"""Audit log viewing endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.security.audit import get_audit_logs

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/log")
def get_log(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get paginated audit log entries for the current user."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    logs, total = get_audit_logs(
        db=db,
        user_id=user.id,
        page=page,
        per_page=per_page,
        action=action,
        resource_type=resource_type,
    )

    entries = []
    for log in logs:
        entries.append({
            "id": log.id,
            "user_id": log.user_id,
            "actor": log.actor,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "result": log.result,
        })

    return {
        "entries": entries,
        "total": total,
        "page": page,
        "per_page": per_page,
    }
