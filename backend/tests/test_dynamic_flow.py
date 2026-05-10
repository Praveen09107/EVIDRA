"""
ForensIQ — Full Dynamic End-to-End Flow Test.
Tests: Case Creation → Evidence Upload → Pipeline Trigger → ML Results → API Verification
"""
import sys, json, asyncio, hashlib, urllib.request, urllib.parse
from uuid import uuid4

API = "http://localhost:8000/api/v1"
PASS = "✅"
FAIL = "❌"
results = []

def log(name, ok, detail=""):
    results.append((name, ok))
    print(f"  {PASS if ok else FAIL} {name}" + (f" — {detail}" if detail else ""))

async def main():
    print("\n" + "=" * 60)
    print("  ForensIQ — Full Dynamic E2E Flow Test")
    print("=" * 60)

    from core.database import db
    from core.storage import storage
    pool = await db.get_pool()
    storage.get_minio()

    # ── 1. Login ──
    print("\n── Login ──")
    data = urllib.parse.urlencode({"username": "admin@evidra.gov", "password": "admin123"}).encode()
    req = urllib.request.Request(f"{API}/auth/login", data, {"Content-Type": "application/x-www-form-urlencoded"})
    resp = urllib.request.urlopen(req, timeout=5)
    body = json.loads(resp.read())
    token = body.get("access_token")
    log("Login successful", token is not None, f"token={token[:20]}...")

    def auth_request(method, path, body_data=None):
        url = f"{API}{path}"
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        if body_data:
            return urllib.request.urlopen(req, json.dumps(body_data).encode(), timeout=30)
        return urllib.request.urlopen(req, timeout=30)

    # ── 2. Create Case ──
    print("\n── Create Case ──")
    resp = auth_request("POST", "/cases", {"title": "E2E Dynamic Test: Sharma Murder", "description": "Body found with defensive wounds", "risk_level": "HIGH"})
    case = json.loads(resp.read())
    case_id = case["case_id"]
    log("Case created via API", case_id is not None, f"id={case_id[:12]}...")

    # ── 3. Upload Evidence ──
    print("\n── Upload Evidence ──")

    autopsy = b"""OFFICE OF THE MEDICAL EXAMINER
Name: Vikram Sharma | Age: 38 | Sex: Male | Weight: 75kg
Rectal Temperature: 29.5 C | Ambient Temperature: 20.0 C
Rigor Mortis: Fully established | Livor Mortis: Fixed
External: Defensive wounds on forearms. Blunt force trauma to skull.
Toxicology: Positive for elevated potassium chloride.
COD: Blunt force trauma + toxic injection | Manner: HOMICIDE
"""
    cdr = b"""timestamp,event_type,source_msisdn,counterparty,duration
2026-05-08T22:15:00Z,MOC,919876543210,919111222333,240
2026-05-08T22:20:00Z,SMS_MO,919876543210,919111222333,0
2026-05-09T06:00:00Z,MTC,919876543210,919444555666,0
"""
    fin = b"""timestamp,txn_type,amount,narration
2026-05-08T21:00:00Z,DEBIT,500000,Wire Transfer Offshore
2026-05-08T21:30:00Z,DEBIT,250000,Cash Withdrawal ATM
"""

    for fname, dtype, content in [("Autopsy_Sharma.txt", "AUTOPSY_REPORT", autopsy), ("CDR_Victim.csv", "CDR", cdr), ("HDFC_Stmt.csv", "FINANCIAL_RECORDS", fin)]:
        fid = str(uuid4())
        sha = hashlib.sha256(content).hexdigest()
        await db.execute(
            "INSERT INTO case_files (file_id, case_id, original_name, s3_key, doc_type, sha256_hash, uploaded_by) VALUES ($1, $2, $3, 'pending', $4, $5, (SELECT user_id FROM users WHERE email='admin@evidra.gov'))",
            fid, case_id, fname, dtype, sha
        )
        s3k = storage.upload_file(case_id, fid, fname, content, "text/plain")
        await db.execute("UPDATE case_files SET s3_key=$1 WHERE file_id=$2", s3k, fid)
        log(f"Uploaded {fname}", True)

    files = await db.fetchval("SELECT COUNT(*) FROM case_files WHERE case_id=$1", case_id)
    log("3 files in DB", files == 3)

    # ── 4. Trigger Pipeline (THIS IS THE BIG TEST) ──
    print("\n── Pipeline Trigger (runs ML agents) ──")
    try:
        resp = auth_request("POST", f"/cases/{case_id}/pipeline/trigger")
        pipe = json.loads(resp.read())
        log("Pipeline executed", pipe.get("status") == "complete", f"status={pipe.get('status')}")
    except Exception as e:
        log("Pipeline executed", False, str(e))

    # ── 5. Verify ALL Results are DYNAMIC ──
    print("\n── Verify Dynamic Results ──")

    # Pipeline status
    try:
        resp = auth_request("GET", f"/cases/{case_id}/pipeline/status")
        status = json.loads(resp.read())
        log("Pipeline status = COMPLETE", status.get("status") == "COMPLETE")
    except Exception as e:
        log("Pipeline status", False, str(e))

    # TOD Result
    try:
        resp = auth_request("GET", f"/cases/{case_id}/analysis/tod")
        tod = json.loads(resp.read())
        has_pmi = "pmiMeanHours" in tod
        log("TOD result is DYNAMIC", has_pmi, f"PMI={tod.get('pmiMeanHours')}h" if has_pmi else f"got: {list(tod.keys())}")
        if has_pmi:
            log("  → Has window95", "window95" in tod)
            log("  → Has componentContributions", len(tod.get("componentContributions", [])) >= 3)
            log("  → Has signLikelihoods", "signLikelihoods" in tod)
    except Exception as e:
        log("TOD result", False, str(e))

    # Hypothesis
    try:
        resp = auth_request("GET", f"/cases/{case_id}/analysis/hypothesis")
        hypo = json.loads(resp.read())
        posteriors = hypo.get("posteriors", {})
        log("Hypothesis posteriors populated", len(posteriors) >= 4, f"top={hypo.get('topHypothesis')}, conf={hypo.get('topConfidence', 0):.2f}")
        log("  → Has signals", len(hypo.get("signals", [])) > 0, f"{len(hypo.get('signals', []))} signals")
    except Exception as e:
        log("Hypothesis", False, str(e))

    # Replay
    try:
        resp = auth_request("GET", f"/cases/{case_id}/replay")
        replay = json.loads(resp.read())
        log("Replay steps populated", len(replay) >= 3, f"{len(replay)} steps")
    except Exception as e:
        log("Replay steps", False, str(e))

    # Report
    try:
        resp = auth_request("GET", f"/cases/{case_id}/report")
        report = json.loads(resp.read())
        narrative = report.get("narrative", "")
        log("Report generated dynamically", len(narrative) > 100, f"{len(narrative)} chars")
        log("  → Contains case data", "Sharma" in narrative or "HOMICIDE" in narrative or "ForensIQ" in narrative)
    except Exception as e:
        log("Report", False, str(e))

    # Agents (should be from registry, not static)
    try:
        resp = urllib.request.urlopen(f"{API}/agents", timeout=5)
        agents = json.loads(resp.read())
        log("Agent registry returns 17", len(agents) == 17)
    except Exception as e:
        log("Agent registry", False, str(e))

    # ── Summary ──
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"  RESULTS: {passed}/{len(results)} passed, {failed} failed")
    print("=" * 60)
    if failed:
        print("\n  FAILURES:")
        for name, ok in results:
            if not ok:
                print(f"    {FAIL} {name}")
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
