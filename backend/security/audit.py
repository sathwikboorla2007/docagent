import json
from datetime import datetime
from backend.database import AuditLog, SessionLocal
from typing import Tuple, List, Optional

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
) -> Optional[AuditLog]:
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            result=result,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry
    except Exception as e:
        # Never crash the main request on audit log failure
        db.rollback()
        print(f"Warning: Failed to log audit action: {e}")
        return None

def get_audit_logs(
    db, 
    user_id: str = None, 
    page: int = 1, 
    per_page: int = 50, 
    action: str = None, 
    resource_type: str = None
) -> Tuple[List[AuditLog], int]:
    try:
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
            
        total = query.count()
        
        offset = (page - 1) * per_page
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(per_page).all()
        
        return logs, total
    except Exception as e:
        print(f"Error querying audit logs: {e}")
        return [], 0
