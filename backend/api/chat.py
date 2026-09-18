"""Chat endpoint — routes messages through the Orchestrator agent."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import ChatMessage
from backend.agents.orchestrator import Orchestrator
from backend.security.audit import log_action

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("")
@router.post("/")
def chat(message_in: ChatMessage, request: Request, db: Session = Depends(get_db)):
    """Process a natural-language message through the orchestrator agent."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        orchestrator = Orchestrator(db=db, user=user)
        response = orchestrator.process_message(message_in.message)

        log_action(db, user.id, "agent", "chat", "chat", None, "success",
                   f"Processed: {message_in.message[:100]}")

        return response
    except Exception as e:
        log_action(db, user.id, "system", "chat_error", "chat", None, "error", str(e))
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
