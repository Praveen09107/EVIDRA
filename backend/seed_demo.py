"""
EVIDRA — Synthetic Demo Case Generator.

Run this script to inject a fully prepared "Suspicious Death" case
into the database and MinIO, ready to trigger the pipeline.
"""
import asyncio
import io
import os
from uuid import uuid4
from datetime import datetime, timedelta

from core.database import db
from core.storage import storage
from core.config import settings

async def seed_demo_case():
    await db.get_pool()
    storage.get_minio()

    # Get admin user
    admin = await db.fetchrow("SELECT user_id, org_id FROM users WHERE email='admin@evidra.gov'")
    if not admin:
        print("Admin user not found. Did you run init.sql?")
        return

    # 1. Create Case
    case_id = str(uuid4())
    await db.execute(
        """
        INSERT INTO cases (case_id, org_id, title, description, risk_level, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        case_id, admin["org_id"], "Demo Case: The Midnight Ledger",
        "A suspicious death of a CFO found in his home office. Ruled natural, but family suspects foul play.",
        "HIGH", admin["user_id"]
    )
    print(f"Created Case: {case_id}")

    # 2. Synthetic Autopsy Report (Text)
    autopsy_text = """
    OFFICE OF THE MEDICAL EXAMINER - AUTOPSY REPORT
    Name: John Doe
    Age: 45 | Sex: Male | Weight: 85kg | Height: 180cm
    
    Measurements:
    Rectal Temperature: 31.0 C
    Ambient Temperature: 22.0 C
    Measurement Time: 2026-05-09T08:00:00Z
    
    Rigor Mortis: Fully complete
    Livor Mortis: Fixed, cherry-red color
    Stomach Contents: Empty
    
    External Exam:
    No blunt force trauma. Faint 2mm puncture wound on left deltoid.
    
    Toxicology:
    Blood Alcohol: 0.02%
    Potassium Chloride: Highly elevated (lethal levels)
    
    Opinion:
    Cause of Death: Cardiac arrest secondary to potassium chloride toxicity.
    Manner of Death: UNDETERMINED
    """
    await upload_demo_file(case_id, admin["user_id"], "Autopsy_Report.txt", "AUTOPSY_REPORT", autopsy_text.encode())

    # 3. Synthetic CDR (CSV)
    # Shows silence window before death
    cdr_csv = "timestamp,event_type,source_msisdn,counterparty,duration,tower_id,lat,lon\n"
    base_time = datetime.fromisoformat("2026-05-08T12:00:00+00:00")
    
    cdr_csv += f"{(base_time).isoformat()},MOC,555-0100,555-0999,120,TWR-A,40.71,-74.00\n"
    cdr_csv += f"{(base_time + timedelta(hours=2)).isoformat()},MOC,555-0100,555-0999,45,TWR-A,40.71,-74.00\n"
    # Silence gap of 14 hours!
    cdr_csv += f"{(base_time + timedelta(hours=16)).isoformat()},MTC,555-0100,555-0000,0,TWR-A,40.71,-74.00\n"
    
    await upload_demo_file(case_id, admin["user_id"], "Phone_Logs.csv", "CDR", cdr_csv.encode())

    # 4. Synthetic Financials (CSV)
    # Shows sudden liquidation
    fin_csv = "timestamp,txn_type,amount,narration,counterparty\n"
    fin_csv += f"{(base_time - timedelta(days=2)).isoformat()},CREDIT,5000,Payroll,TechCorp\n"
    fin_csv += f"{(base_time - timedelta(days=1)).isoformat()},DEBIT,2000000,Wire Transfer - Urgent Liquidation,OffshoreAcc123\n"
    fin_csv += f"{(base_time).isoformat()},DEBIT,1500000,Wire Transfer - Urgent Liquidation,OffshoreAcc123\n"
    
    await upload_demo_file(case_id, admin["user_id"], "Bank_Statements.csv", "FINANCIAL_RECORDS", fin_csv.encode())

    print("\n✅ Demo Case Seeded Successfully!")
    print(f"Case ID: {case_id}")
    print("Trigger pipeline using: POST /api/v1/pipeline/trigger")

async def upload_demo_file(case_id: str, user_id: str, filename: str, doc_type: str, data: bytes):
    file_id = str(uuid4())
    import hashlib
    sha256 = hashlib.sha256(data).hexdigest()
    
    # DB entry
    await db.execute(
        """
        INSERT INTO case_files (file_id, case_id, original_name, s3_key, doc_type, sha256_hash, uploaded_by)
        VALUES ($1, $2, $3, 'pending', $4, $5, $6)
        """,
        file_id, case_id, filename, doc_type, sha256, user_id
    )
    
    # MinIO
    s3_key = storage.upload_file(case_id, file_id, filename, data, "text/plain")
    
    # Update DB
    await db.execute("UPDATE case_files SET s3_key=$1 WHERE file_id=$2", s3_key, file_id)
    print(f"  - Uploaded {filename}")

if __name__ == "__main__":
    asyncio.run(seed_demo_case())
