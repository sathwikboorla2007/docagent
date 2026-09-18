"""Comprehensive test suite verifying all DocuAgent features."""

import sys
import os
import urllib.request
import json
import io
import mimetypes
import uuid

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = "http://127.0.0.1:8000"

def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", body, headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def upload_file(doc_type, filename, content_bytes, token=None, linked_domains=None):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    buf = io.BytesIO()
    
    # file field
    buf.write(f"--{boundary}\r\n".encode())
    buf.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    buf.write(b"Content-Type: application/pdf\r\n\r\n")
    buf.write(content_bytes)
    buf.write(b"\r\n")
    
    # doc_type field
    buf.write(f"--{boundary}\r\n".encode())
    buf.write(b'Content-Disposition: form-data; name="doc_type"\r\n\r\n')
    buf.write(doc_type.encode())
    buf.write(b"\r\n")
    
    if linked_domains:
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(b'Content-Disposition: form-data; name="linked_domains_json"\r\n\r\n')
        buf.write(json.dumps(linked_domains).encode())
        buf.write(b"\r\n")
        
    buf.write(f"--{boundary}--\r\n".encode())
    
    body = buf.getvalue()
    req = urllib.request.Request(f"{BASE}/api/documents/upload", body, headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def run_tests():
    print("=" * 70)
    print("🚀 RUNNING COMPREHENSIVE DOCUAGENT TEST SUITE")
    print("=" * 70)

    # 1. Health check
    print("\n[1] Testing Health Endpoint...")
    h = api("GET", "/api/health")
    print(f"  Status: {h['status']} | Service: {h['service']} | Version: {h['version']}")
    assert h["status"] == "ok"

    # 2. Login
    print("\n[2] Testing Authentication...")
    login_res = api("POST", "/api/users/login", {"email": "demo@example.com", "password": "demo123"})
    token = login_res["session_token"]
    user = login_res["user"]
    print(f"  Logged in as: {user['name']} ({user['email_masked']})")
    assert token is not None

    # 3. User Profile
    me = api("GET", "/api/users/me", token=token)
    print(f"  Profile verified: ID={me['id']}, Role={me['role']}")

    # 4. Cross-Domain Chat 1: Schengen Visa
    print("\n[3] Testing Chat Agent — Schengen Visa Domain...")
    chat1 = api("POST", "/api/chat", {
        "message": "I am traveling to France and Italy for 3 weeks in December. What documents are needed?"
    }, token)
    print(f"  Domain: {chat1['domain']} | State: {chat1['workflow_state']}")
    reqs1 = chat1["requirements"]
    print(f"  Total required: {reqs1['total_required']} | Met: {len(reqs1['documents_met'])} | Missing: {len(reqs1['documents_missing'])}")
    print(f"  Completion: {reqs1['completion_percentage']}%")
    print(f"  Reused documents from vault: {[d['doc_type'] for d in reqs1['documents_met']]}")
    assert len(reqs1['documents_met']) >= 2  # Passport and Bank Statement reused!

    # 5. Cross-Domain Chat 2: Home Loan (Testing intelligent requirement aliasing!)
    print("\n[4] Testing Chat Agent — Home Loan Domain (Cross-Domain Vault Check)...")
    chat2 = api("POST", "/api/chat", {
        "message": "I want to apply for a home loan of 50 lakhs. I earn 1.5 lakh per month."
    }, token)
    print(f"  Domain: {chat2['domain']} | State: {chat2['workflow_state']}")
    reqs2 = chat2["requirements"]
    print(f"  Total required: {reqs2['total_required']} | Met: {len(reqs2['documents_met'])} | Missing: {len(reqs2['documents_missing'])}")
    print(f"  Completion: {reqs2['completion_percentage']}%")
    print(f"  Reused: {[d['doc_type'] for d in reqs2['documents_met']]}")
    assert "passport" in [d.get("reused_from", d["doc_type"]) for d in reqs2["documents_met"]] or "bank_statement" in [d["doc_type"] for d in reqs2["documents_met"]]

    # 6. Cross-Domain Chat 3: GST Registration
    print("\n[5] Testing Chat Agent — GST Registration Domain...")
    chat3 = api("POST", "/api/chat", {
        "message": "I want to register for GST as a freelancer."
    }, token)
    print(f"  Domain: {chat3['domain']}")
    reqs3 = chat3["requirements"]
    print(f"  Reused in GST: {[d['doc_type'] for d in reqs3['documents_met']]}")
    assert len(reqs3["documents_met"]) >= 2

    # 7. Document Vault Inspection
    print("\n[6] Testing Document Vault...")
    docs_res = api("GET", "/api/documents", token=token)
    print(f"  Total documents in vault: {docs_res['total']}")
    for d in docs_res["documents"]:
        masked = d.get("pii_fields_masked") or {}
        print(f"  • {d['doc_type']:20s} | Status: {d['status']:10s} | PII: {masked} | Linked: {d.get('linked_domains', [])}")

    # 8. Document Upload with Auto-linking
    print("\n[7] Testing Document Upload with Encryption & Auto-domain Linking...")
    up_res = upload_file("travel_insurance", "axa_travel_insurance.pdf", b"SIMULATED_ENCRYPTED_INSURANCE_DATA", token=token)
    print(f"  Uploaded document ID: {up_res['id']} | Type: {up_res['doc_type']}")
    print(f"  Auto-linked domains: {up_res['linked_domains']}")
    assert up_res["doc_type"] == "travel_insurance"
    assert "schengen_visa" in up_res["linked_domains"]

    # 9. Reminders API (List & Proactive Scan)
    print("\n[8] Testing Reminders System...")
    scan_res = api("POST", "/api/reminders/scan", token=token)
    print(f"  Proactive scan result: {scan_res['message']}")
    
    rem_list = api("GET", "/api/reminders", token=token)
    print(f"  Total reminders: {rem_list['total']}")
    for r in rem_list["reminders"][:3]:
        print(f"  • [{r['reminder_type'].upper()}] {r['message'][:55]}... (Sent/Done: {r['is_sent']})")
    
    if rem_list["reminders"]:
        first_id = rem_list["reminders"][0]["id"]
        dismiss_res = api("POST", f"/api/reminders/{first_id}/dismiss", token=token)
        print(f"  Dismissed reminder {first_id}: {dismiss_res['message']}")

    # 10. Submissions Tracking & Status Advance
    print("\n[9] Testing Submissions Tracker & Progression...")
    subs_res = api("GET", "/api/submissions", token=token)
    print(f"  Total submissions: {len(subs_res['submissions'])}")
    for s in subs_res["submissions"]:
        print(f"  • {s['domain']:18s} | Ref: {s['external_ref_id']} | Status: {s['status']}")
        
    if subs_res["submissions"]:
        first_sub_id = subs_res["submissions"][0]["id"]
        stat_res = api("GET", f"/api/submissions/{first_sub_id}/status", token=token)
        print(f"  Checked status for {first_sub_id}: Status={stat_res['status']}")

    # 11. Security Audit Log
    print("\n[10] Testing Security Audit Log...")
    audit_res = api("GET", "/api/audit/log?per_page=10", token=token)
    print(f"  Audit log entries: {len(audit_res['entries'])} (Total: {audit_res['total']})")
    for e in audit_res["entries"][:5]:
        ts = e["timestamp"][:19] if e["timestamp"] else "N/A"
        actor = e.get("actor", "?")
        act = e.get("action", "?")
        res = e.get("result", "?")
        details = (e.get("details") or "")[:50]
        print(f"  [{ts}] {actor:6s} | {act:18s} | {res:7s} | {details}")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
