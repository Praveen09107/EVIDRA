"""
EVIDRA — Cases & Evidence API.

Handles case creation, listing, and evidence file uploads to MinIO.
"""
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from core.database import db
from core.storage import storage
from api.auth import get_current_user

router = APIRouter(prefix="/cases", tags=["Cases"])

# ═══════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════

class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    risk_level: str = "MEDIUM"

class CaseResponse(BaseModel):
    case_id: str
    case_number: str
    title: str
    status: str
    risk_level: str
    created_at: str

class FileResponse(BaseModel):
    file_id: str
    original_name: str
    doc_type: str
    status: str
    file_size_bytes: int

# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.post("", response_model=CaseResponse)
async def create_case(case: CaseCreate, current_user: dict = Depends(get_current_user)):
    """Create a new forensic case."""
    row = await db.fetchrow(
        """
        INSERT INTO cases (org_id, title, description, risk_level, created_by)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING case_id::text, case_number, title, status, risk_level, created_at::text
        """,
        current_user["org_id"], case.title, case.description, case.risk_level, current_user["user_id"]
    )
    return dict(row)

@router.get("", response_model=List[CaseResponse])
async def list_cases(current_user: dict = Depends(get_current_user)):
    """List all cases for the user's organization."""
    rows = await db.fetch(
        """
        SELECT case_id::text, case_number, title, status, risk_level, created_at::text
        FROM cases
        WHERE org_id = $1
        ORDER BY created_at DESC
        """,
        current_user["org_id"]
    )
    return [dict(r) for r in rows]

@router.get("/{case_id}", response_model=dict)
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get full case details including uploaded files."""
    case = await db.fetchrow("SELECT * FROM cases WHERE case_id = $1 AND org_id = $2", case_id, current_user["org_id"])
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    files = await db.fetch("SELECT * FROM case_files WHERE case_id = $1 ORDER BY uploaded_at DESC", case_id)
    
    result = dict(case)
    result["created_at"] = str(result["created_at"])
    result["updated_at"] = str(result["updated_at"])
    result["files"] = [{**dict(f), "uploaded_at": str(f["uploaded_at"])} for f in files]
    return result

@router.post("/{case_id}/files", response_model=FileResponse)
async def upload_file(
    case_id: str,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload evidence to a case (saves to MinIO + Postgres)."""
    # Verify case exists
    case = await db.fetchrow("SELECT case_id FROM cases WHERE case_id = $1 AND org_id = $2", case_id, current_user["org_id"])
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    valid_types = ['AUTOPSY_REPORT','CDR','FINANCIAL_RECORDS','DEVICE_DATA','CCTV','WITNESS_STATEMENT','POLICE_REPORT','OTHER']
    if doc_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Must be one of {valid_types}")

    file_bytes = await file.read()
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Reserve DB row to get file_id
    row = await db.fetchrow(
        """
        INSERT INTO case_files (case_id, original_name, s3_key, mime_type, file_size_bytes, doc_type, sha256_hash, uploaded_by)
        VALUES ($1, $2, 'pending', $3, $4, $5, $6, $7)
        RETURNING file_id
        """,
        case_id, file.filename, file.content_type, len(file_bytes), doc_type, sha256_hash, current_user["user_id"]
    )
    file_id = str(row["file_id"])

    # Upload to MinIO
    s3_key = storage.upload_file(case_id, file_id, file.filename, file_bytes, file.content_type)

    # Update DB with final S3 key
    updated = await db.fetchrow(
        "UPDATE case_files SET s3_key = $1 WHERE file_id = $2 RETURNING *",
        s3_key, file_id
    )

    return dict(updated)


@router.get("/{case_id}/files")
async def list_files(case_id: str, current_user: dict = Depends(get_current_user)):
    """List all evidence files uploaded to a case."""
    case = await db.fetchrow("SELECT case_id FROM cases WHERE case_id = $1 AND org_id = $2", case_id, current_user["org_id"])
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    rows = await db.fetch(
        "SELECT file_id, original_name, doc_type, mime_type, file_size_bytes, sha256_hash, uploaded_at "
        "FROM case_files WHERE case_id=$1 ORDER BY uploaded_at DESC",
        case_id
    )
    return [{
        "file_id": str(r["file_id"]),
        "original_name": r["original_name"],
        "doc_type": r["doc_type"],
        "size_bytes": r["file_size_bytes"],
        "status": "PROCESSED",
        "checksum": r["sha256_hash"][:12] + "..." if r["sha256_hash"] else "",
        "uploaded_at": str(r["uploaded_at"]),
    } for r in rows]
