"""
EVIDRA — Forensic Integrity Module.

Implements spec §6.1:
- SHA-256 evidence file hashing on upload
- Chain-of-custody logging
- Audit log entry chaining (prev_entry_hash)
- Evidence integrity verification
"""
import hashlib
import json
import logging
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional

logger = logging.getLogger("evidra.integrity")


# ═══════════════════════════════════════════════════════════
# SHA-256 EVIDENCE HASHING
# ═══════════════════════════════════════════════════════════

def compute_file_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(file_bytes).hexdigest()


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════
# CHAIN-OF-CUSTODY LOGGING
# ═══════════════════════════════════════════════════════════

async def log_custody_event(
    db,
    case_id: UUID,
    file_id: UUID,
    action: str,
    actor: str,
    details: str = "",
    file_hash: str = "",
):
    """
    Record a chain-of-custody event for a piece of evidence.
    Actions: UPLOAD, ACCESS, MODIFY, EXPORT, DELETE, TRANSFER
    """
    await db.execute(
        """
        INSERT INTO chain_of_custody (case_id, file_id, action, actor, details, file_hash, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """,
        case_id, file_id, action, actor, details, file_hash,
    )
    logger.info(f"Custody: [{action}] file={str(file_id)[:8]} by {actor}")


# ═══════════════════════════════════════════════════════════
# AUDIT LOG CHAINING
# ═══════════════════════════════════════════════════════════

async def append_audit_entry(
    db,
    case_id: UUID,
    action: str,
    actor: str,
    details: dict,
) -> str:
    """
    Append an audit log entry with hash chaining.
    Each entry's hash includes the previous entry's hash for tamper detection.
    """
    # Get the last entry hash
    last_entry = await db.fetchrow(
        "SELECT entry_hash FROM audit_log WHERE case_id=$1 ORDER BY created_at DESC LIMIT 1",
        case_id,
    )
    prev_hash = last_entry["entry_hash"] if last_entry else "GENESIS"

    # Compute current entry hash
    entry_data = {
        "case_id": str(case_id),
        "action": action,
        "actor": actor,
        "details": details,
        "prev_hash": prev_hash,
        "timestamp": datetime.utcnow().isoformat(),
    }
    entry_hash = hashlib.sha256(
        json.dumps(entry_data, sort_keys=True).encode("utf-8")
    ).hexdigest()

    await db.execute(
        """
        INSERT INTO audit_log (case_id, action, actor, details, prev_entry_hash, entry_hash)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        case_id, action, actor,
        json.dumps(details, default=str),
        prev_hash, entry_hash,
    )

    return entry_hash


# ═══════════════════════════════════════════════════════════
# INTEGRITY VERIFICATION
# ═══════════════════════════════════════════════════════════

async def verify_audit_chain(db, case_id: UUID) -> dict:
    """Verify the integrity of the audit log chain for a case."""
    entries = await db.fetch(
        "SELECT * FROM audit_log WHERE case_id=$1 ORDER BY created_at ASC",
        case_id,
    )

    if not entries:
        return {"valid": True, "entries_checked": 0, "message": "No audit entries"}

    valid = True
    broken_at = None
    prev_hash = "GENESIS"

    for i, entry in enumerate(entries):
        stored_prev = entry.get("prev_entry_hash", "")
        if stored_prev != prev_hash:
            valid = False
            broken_at = i
            break
        prev_hash = entry.get("entry_hash", "")

    return {
        "valid": valid,
        "entries_checked": len(entries),
        "broken_at_index": broken_at,
        "message": "Chain intact" if valid else f"Chain broken at entry {broken_at}",
    }


async def verify_file_integrity(db, storage, file_id: UUID) -> dict:
    """Verify a file's current hash matches its stored hash."""
    file_record = await db.fetchrow(
        "SELECT * FROM case_files WHERE file_id=$1", file_id,
    )
    if not file_record:
        return {"valid": False, "message": "File not found"}

    stored_hash = file_record.get("file_hash", "")
    if not stored_hash:
        return {"valid": False, "message": "No hash stored for file"}

    # Download and recompute
    try:
        file_bytes = storage.download_file(file_record["s3_key"])
        current_hash = compute_file_hash(file_bytes)
        match = current_hash == stored_hash
        return {
            "valid": match,
            "stored_hash": stored_hash,
            "current_hash": current_hash,
            "message": "Integrity verified" if match else "HASH MISMATCH — possible tampering",
        }
    except Exception as e:
        return {"valid": False, "message": f"Verification failed: {e}"}
