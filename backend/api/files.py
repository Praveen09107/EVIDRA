"""
EVIDRA — File Upload API with forensic integrity.

Handles evidence file uploads with:
- SHA-256 hash computation on upload
- Chain-of-custody logging
- MinIO storage
- Audit trail entry
"""
import logging
from uuid import UUID, uuid4
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from core.database import db
from core.storage import storage
from core.integrity import compute_file_hash, log_custody_event, append_audit_entry

logger = logging.getLogger("evidra.api.files")
router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload/{case_id}")
async def upload_evidence(
    case_id: UUID,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
):
    """
    Upload a piece of evidence to a case.
    Computes SHA-256 hash, stores in MinIO, logs custody chain.
    """
    file_bytes = await file.read()
    file_id = uuid4()

    # 1. Compute SHA-256 hash
    file_hash = compute_file_hash(file_bytes)

    # 2. Upload to MinIO
    s3_key = f"cases/{case_id}/{file_id}/{file.filename}"
    try:
        storage.upload_file(s3_key, file_bytes, file.content_type or "application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    # 3. Insert file record with hash
    await db.execute(
        """
        INSERT INTO case_files (file_id, case_id, original_name, s3_key, doc_type, mime_type, size_bytes, file_hash, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'UPLOADED')
        """,
        file_id, case_id, file.filename, s3_key, doc_type,
        file.content_type or "application/octet-stream",
        len(file_bytes), file_hash,
    )

    # 4. Log custody event
    await log_custody_event(
        db, case_id, file_id,
        action="UPLOAD",
        actor="system",
        details=f"Uploaded {file.filename} ({doc_type}, {len(file_bytes)} bytes)",
        file_hash=file_hash,
    )

    # 5. Append audit log entry
    await append_audit_entry(
        db, case_id,
        action="EVIDENCE_UPLOADED",
        actor="system",
        details={
            "file_id": str(file_id),
            "filename": file.filename,
            "doc_type": doc_type,
            "size_bytes": len(file_bytes),
            "sha256": file_hash,
        },
    )

    logger.info(f"Evidence uploaded: {file.filename} -> {file_id} (SHA256: {file_hash[:16]}...)")

    return {
        "file_id": str(file_id),
        "case_id": str(case_id),
        "filename": file.filename,
        "doc_type": doc_type,
        "size_bytes": len(file_bytes),
        "sha256": file_hash,
        "s3_key": s3_key,
        "status": "UPLOADED",
    }


@router.get("/{case_id}")
async def list_case_files(case_id: UUID):
    """List all files for a case."""
    files = await db.fetch("SELECT * FROM case_files WHERE case_id=$1 ORDER BY uploaded_at DESC", case_id)
    return [dict(f) for f in files] if files else []


@router.get("/verify/{file_id}")
async def verify_file_integrity(file_id: UUID):
    """Verify the integrity of an uploaded file by recomputing its hash."""
    from core.integrity import verify_file_integrity as _verify
    result = await _verify(db, storage, file_id)
    return result
