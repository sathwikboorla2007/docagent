"""User registration, login, and profile endpoints."""

import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import User, get_db
from backend.schemas import UserCreate, UserLogin, UserResponse
from backend.security.access_control import hash_password, verify_password, create_session_token
from backend.security.audit import log_action
from backend.security.pii_masking import mask_value

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("/register")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    email_hash = hashlib.sha256(user_in.email.lower().encode()).hexdigest()

    # Check if email already registered
    existing = db.query(User).filter(User.email_hash == email_hash).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=user_in.name,
        email_hash=email_hash,
        password_hash=hash_password(user_in.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create session token
    token = create_session_token(user.id)
    user.session_token = token
    db.commit()

    log_action(db, user.id, "user", "create", "user", user.id, "success", "User registered")

    return {
        "id": user.id,
        "name": user.name,
        "email_masked": mask_value(user_in.email, "email"),
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "session_token": token,
    }


@router.post("/login")
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    email_hash = hashlib.sha256(user_in.email.lower().encode()).hexdigest()

    user = db.query(User).filter(User.email_hash == email_hash).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        log_action(db, None, "user", "login", "session", None, "denied", f"Failed login attempt for {mask_value(user_in.email, 'email')}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create new session token
    token = create_session_token(user.id)
    user.session_token = token
    db.commit()

    log_action(db, user.id, "user", "login", "session", user.id, "success", "User logged in")

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email_masked": mask_value(user_in.email, "email"),
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "session_token": token,
    }


@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    """Get current user profile."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    log_action(db, user.id, "user", "read", "user", user.id, "success", "Profile accessed")

    return {
        "id": user.id,
        "name": user.name,
        "email_masked": f"****@****.***",  # email is stored hashed, can't reverse
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
