"""
P9 — Secure Personal Document & Bureaucracy Management Agent
Main FastAPI application entry point.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.database import init_db, engine, SessionLocal
from backend.security.middleware import SecurityMiddleware
from backend.api.users import router as users_router
from backend.api.documents import router as documents_router
from backend.api.submissions import router as submissions_router
from backend.api.audit_routes import router as audit_router
from backend.api.chat import router as chat_router
from backend.api.reminders import router as reminders_router


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and start background scheduler on startup."""
    # Initialize database tables
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialized")

    # Seed domain requirements if empty
    from backend.database import DomainRequirement
    db = SessionLocal()
    try:
        count = db.query(DomainRequirement).count()
        if count == 0:
            print("📋 Seeding domain requirements from YAML configs...")
            _seed_domain_requirements(db)
            print("✅ Domain requirements seeded")
        else:
            print(f"📋 Domain requirements already loaded ({count} entries)")
    finally:
        db.close()

    # Start reminder scheduler (background)
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(_check_reminders, 'interval', minutes=5, id='reminder_check')
        scheduler.start()
        print("⏰ Reminder scheduler started (every 5 min)")
    except Exception as e:
        print(f"⚠️  Scheduler not started: {e}")

    print("🚀 DocuAgent is ready!")
    print("   Open http://localhost:8000 in your browser")
    yield

    # Shutdown
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
    print("👋 DocuAgent shutting down")


def _seed_domain_requirements(db):
    """Load YAML domain configs into the domain_requirements table."""
    import yaml
    from backend.database import DomainRequirement
    from uuid import uuid4

    config_dir = os.path.join(PROJECT_ROOT, "config", "domains")
    if not os.path.exists(config_dir):
        print(f"⚠️  Config directory not found: {config_dir}")
        return

    for filename in os.listdir(config_dir):
        if not filename.endswith(('.yaml', '.yml')):
            continue
        filepath = os.path.join(config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            domain = config.get('domain', filename.replace('.yaml', ''))

            # Seed required documents
            for doc in config.get('required_documents', []):
                req = DomainRequirement(
                    id=str(uuid4()),
                    domain=domain,
                    doc_type=doc.get('type', ''),
                    description=doc.get('description', ''),
                    is_conditional=False,
                    condition_expr=None,
                    priority=doc.get('priority', 0),
                )
                db.add(req)

            # Seed conditional requirements
            for cond in config.get('conditional_requirements', []):
                for req_doc in cond.get('then_require', []):
                    req = DomainRequirement(
                        id=str(uuid4()),
                        domain=domain,
                        doc_type=req_doc.get('type', '') if isinstance(req_doc, dict) else str(req_doc),
                        description=req_doc.get('description', '') if isinstance(req_doc, dict) else str(req_doc),
                        is_conditional=True,
                        condition_expr=cond.get('condition', ''),
                        priority=0,
                    )
                    db.add(req)

            db.commit()
            print(f"   ✅ Loaded {domain} config")

        except Exception as e:
            print(f"   ⚠️  Error loading {filename}: {e}")
            db.rollback()


def _check_reminders():
    """Background job: check and fire due reminders."""
    from backend.services.reminder_service import ReminderService
    db = SessionLocal()
    try:
        service = ReminderService(db)
        due = service.check_and_send_due_reminders()
        if due:
            print(f"🔔 Sent {len(due)} reminder(s)")
    except Exception as e:
        print(f"⚠️  Reminder check error: {e}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DocuAgent — Secure Bureaucracy Management Agent",
    description="Production-grade agentic AI for navigating bureaucratic processes with bank-level security.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (permissive for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (auth + audit logging)
app.add_middleware(SecurityMiddleware)

# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(submissions_router)
app.include_router(audit_router)
app.include_router(chat_router)
app.include_router(reminders_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
from datetime import datetime

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "DocuAgent",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------
frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/styles.css")
    async def serve_css():
        return FileResponse(os.path.join(frontend_dir, "styles.css"), media_type="text/css")

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(os.path.join(frontend_dir, "app.js"), media_type="application/javascript")
else:
    @app.get("/")
    async def no_frontend():
        return {"message": "DocuAgent API is running. Frontend not found at ./frontend/"}


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[os.path.join(PROJECT_ROOT, "backend")],
    )
