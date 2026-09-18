import os
from datetime import datetime, timedelta
import bcrypt as _bcrypt
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from backend.database import User, get_db

SECRET_KEY = os.getenv("BUREAUCRACY_SECRET_KEY", "bureaucracy-agent-secret-key-demo")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = _bcrypt.gensalt()
    hashed = _bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return _bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def create_session_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(db: Session, token: str) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except JWTError:
        return None
    except Exception:
        return None

def verify_resource_access(db: Session, user: User, resource_type: str, resource_id: str) -> bool:
    if user.role == "admin":
        return True
        
    try:
        if resource_type == "document":
            from backend.database import Document
            doc = db.query(Document).filter(Document.id == resource_id).first()
            return doc is not None and doc.user_id == user.id
        elif resource_type == "submission":
            from backend.database import Submission
            sub = db.query(Submission).filter(Submission.id == resource_id).first()
            return sub is not None and sub.user_id == user.id
        elif resource_type == "user":
            return user.id == resource_id
    except Exception:
        pass
        
    return False

def require_role(user: User, required_role: str) -> bool:
    if not user:
        return False
    if user.role == "admin":
        return True
    return user.role == required_role
