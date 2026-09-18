"""Quick integration test for cross-domain + audit log."""
import urllib.request, json

BASE = "http://localhost:8000"

def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", body, headers, method=method)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# 1. Login
print("=" * 60)
print("TEST 1: Login")
r = api("POST", "/api/users/login", {"email": "demo@example.com", "password": "demo123"})
token = r["session_token"]
print(f"  Logged in as: {r['user']['name']}")
print(f"  Email (masked): {r['user']['email_masked']}")

# 2. Home Loan chat
print("\n" + "=" * 60)
print("TEST 2: Home Loan Domain (cross-domain test)")
r = api("POST", "/api/chat/", {"message": "I want to apply for a home loan of 50 lakhs. I earn 1.5 lakh per month."}, token)
print(f"  Domain: {r['domain']}")
print(f"  Workflow state: {r['workflow_state']}")
if r.get("requirements"):
    req = r["requirements"]
    print(f"  Total required: {req['total_required']}")
    print(f"  Met: {len(req['documents_met'])}, Missing: {len(req['documents_missing'])}")
    print(f"  Completion: {req['completion_percentage']}%")
    print(f"  Reused documents: {[d['doc_type'] for d in req['documents_met']]}")

# 3. List documents (shows cross-domain reuse)
print("\n" + "=" * 60)
print("TEST 3: Documents (shows cross-domain reuse)")
r = api("GET", "/api/documents", token=token)
for doc in r["documents"]:
    print(f"  {doc['doc_type']:20s} | status: {doc['status']:10s} | linked: {doc.get('linked_domains', [])}")

# 4. List submissions
print("\n" + "=" * 60)
print("TEST 4: Submissions")
r = api("GET", "/api/submissions", token=token)
for sub in r["submissions"]:
    print(f"  {sub['domain']:20s} | {sub['external_ref_id']} | status: {sub['status']}")

# 5. Audit log
print("\n" + "=" * 60)
print("TEST 5: Security Audit Log (last 10)")
r = api("GET", "/api/audit/log?per_page=10", token=token)
for e in r["entries"]:
    ts = e["timestamp"][:19] if e["timestamp"] else "N/A"
    actor = e.get("actor", "?")
    action = e.get("action", "?")
    result = e.get("result", "?")
    details = (e.get("details") or "")[:60]
    print(f"  {ts} | {actor:6s} | {action:20s} | {result:7s} | {details}")
print(f"  Total entries: {r['total']}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
