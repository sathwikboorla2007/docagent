# 🛂 DocuAgent

### Autonomous AI Bureaucracy Copilot

Stop searching for documents.
Stop repeating information.
Stop figuring out government requirements manually.

DocuAgent understands your request,
finds the documents you already have,
checks requirements,
identifies missing information,
and guides you through the workflow.

# DocuAgent — Autonomous Document & Bureaucracy Management Agent

> **Bank-Grade Secure Personal Document Vault & Autonomous Bureaucracy Copilot**

DocuAgent is an intelligent, privacy-first personal document management and bureaucracy copilot. It combines an autonomous AI agent capable of proactive requirement gap analysis and cross-domain document reuse ("Don't Ask Twice") with zero-knowledge, bank-grade encryption (AES-GCM-256) and tamper-evident cryptographic audit trails.

---

## 🌟 Key Features

1. **Autonomous Bureaucracy Copilot**
   - Natural language workflow execution for **Schengen Visa**, **Home Loan**, and **GST Registration**.
   - Proactive **Gap Analysis**: Identifies missing documents, detects expired certificates, and calculates financial eligibility (e.g., minimum balance criteria).
   - **Cross-Domain Reuse ("Don't Ask Twice")**: Documents uploaded for one process (e.g., Passport for Schengen Visa) automatically satisfy requirements across others (e.g., Identity/Address Proof for Home Loan or GST).
   - One-click application submission with readiness scoring.

2. **Bank-Level Security & Zero-Knowledge Vault**
   - **AES-GCM-256 Encryption**: Every document payload and sensitive metadata block is encrypted with unique initialization vectors (IV) and authentication tags.
   - **Zero-Knowledge PII Masking**: Automatically detects and masks sensitive identifiers (Passports, PAN, Aadhaar, SSN, Credit Cards) before display.
   - **Cryptographic Audit Trail**: Every access, encryption, decryption, and verification event is immutably logged with SHA-256 hash chains.

3. **Proactive Expiry & Deadline Reminders**
   - Automated 90-day expiry scanning for time-sensitive documents (Passports, Insurance, Tax Certificates).
   - Dismissible alerts with direct renewal recommendations.

4. **Modern Obsidian/Cyberpunk Glassmorphism UI**
   - 5 Dedicated Views: **Copilot Chat**, **Document Vault**, **Submissions Tracker**, **Reminders Dashboard**, and **Security Audit Trail**.
   - Dynamic 4-stage pipeline visualization (Ready ➔ Missing ➔ In Progress ➔ Completed).
   - Drag-and-drop document upload with automatic PII masking preview.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Virtual environment (included in `./venv`)

### 2. Launch the Application
```bash
# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies if needed
pip install -r requirements.txt

# Start the server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### 3. Demo Credentials
DocuAgent comes pre-seeded with a comprehensive test profile:
- **Email**: `demo@example.com`
- **Password**: `demo123`

Pre-seeded documents in the demo account:
- Passport (Valid through 2030)
- Bank Statement (3-month average: ₹1,50,000)
- Travel Insurance Policy
- Salary Slip (Verified)

---

## 🧪 Running Automated Tests

Run the full integration and feature test suite:
```bash
# Run comprehensive 10-point test suite
python test_all_features.py

# Run legacy integration suite
python test_integration.py
```

Both test suites verify:
- Health and Authentication
- Schengen Visa gap analysis & eligibility checks
- Cross-domain reuse (Passport & Bank statement reused for Home Loan)
- Document Vault encryption & zero-knowledge PII masking
- Reminders scanning & dismissal
- Submissions tracking & audit trail verification

---

## 📁 System Architecture

```
bureaucracy-agent/
├── backend/
│   ├── main.py                  # FastAPI application entrypoint & static routes
│   ├── database.py              # SQLite models (User, Document, AuditLog, etc.)
│   ├── schemas.py               # Pydantic validation schemas
│   ├── security/
│   │   ├── encryption.py        # AES-GCM-256 cryptography engine
│   │   ├── pii_masking.py       # PII identification & masking
│   │   ├── access_control.py    # JWT & role-based access
│   │   └── audit.py             # Immutable audit logger
│   ├── agents/
│   │   ├── orchestrator.py      # Multi-domain agent workflow orchestrator
│   │   ├── requirement_matcher.py # Gap analyzer & eligibility calculator
│   │   └── nl_parser.py         # Intent & entity parser
│   ├── services/
│   │   ├── document_service.py  # Vault & cross-domain requirement mapping
│   │   ├── reminder_service.py  # Proactive expiry monitoring engine
│   │   └── state_store.py       # User session & domain state persistence
│   └── api/                     # REST API routers (chat, docs, submissions, reminders, audit)
├── config/domains/              # YAML domain requirements (schengen_visa, home_loan, gst_registration)
├── frontend/                    # Vanilla HTML5/CSS3/ES6 interactive frontend
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── seed_data.py                 # Demo database seeder
```

---

## 🔒 Security Specifications
- **Payload Encryption**: AES-256 in Galois/Counter Mode (GCM).
- **Authentication**: Salted SHA-256 passwords and bearer session tokens.
- **Audit Tamper-Resistance**: SHA-256 checksums on all system transactions.
