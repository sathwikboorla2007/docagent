from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from backend.security.access_control import get_current_user
from backend.security.audit import log_action
from backend.database import SessionLocal
import time

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        # Skip auth for these paths
        skip_auth = (
            path.startswith("/api/users/register") or
            path.startswith("/api/users/login") or
            path.startswith("/api/health") or
            path.startswith("/frontend") or
            path == "/"
        )
        
        db = SessionLocal()
        user = None
        
        try:
            # 1. Extract Authorization header and validate session
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                user = get_current_user(db, token)
                if user:
                    request.state.user = user
                    
            # 2. Check protected routes
            if path.startswith("/api/") and not skip_auth:
                if not user:
                    # Log unauthorized access attempt
                    log_action(
                        db=db,
                        user_id=None,
                        actor="system",
                        action="access_denied",
                        resource_type="endpoint",
                        resource_id=path,
                        result="denied",
                        details=f"Method: {method}, Path: {path}, Error: Missing or invalid token",
                        ip_address=request.client.host if request.client else None
                    )
                    return JSONResponse(status_code=401, content={"detail": "Unauthorized: Invalid or missing token"})
            
            # 3. Proceed with request
            response = await call_next(request)
            
            # 4. Log the API request
            if path.startswith("/api/"):
                log_action(
                    db=db,
                    user_id=user.id if user else None,
                    actor="user" if user else "system",
                    action="api_request",
                    resource_type="endpoint",
                    resource_id=path,
                    result="success" if response.status_code < 400 else "error",
                    details=f"Method: {method}, Path: {path}, Status: {response.status_code}",
                    ip_address=request.client.host if request.client else None
                )
                
            return response
            
        except Exception as e:
            # Log unexpected errors
            log_action(
                db=db,
                user_id=user.id if user else None,
                actor="system",
                action="api_error",
                resource_type="endpoint",
                resource_id=path,
                result="error",
                details=f"Method: {method}, Path: {path}, Error: {str(e)}",
                ip_address=request.client.host if request.client else None
            )
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
            
        finally:
            db.close()
