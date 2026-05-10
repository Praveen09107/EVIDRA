"""
EVIDRA — Replay & Audit API.

Serves the immutable reasoning chain and audit trail.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}", tags=["Replay & Audit"])


@router.get("/replay")
async def get_replay(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the immutable reasoning audit trail (flat path for frontend)."""
    rows = await db.fetch("SELECT * FROM replay_steps WHERE case_id=$1 ORDER BY timestamp ASC", case_id)
    return [{**dict(r), "timestamp": str(r["timestamp"])} for r in rows]


@router.get("/replay/steps")
async def get_replay_steps(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the immutable reasoning audit trail (legacy sub-path)."""
    rows = await db.fetch("SELECT * FROM replay_steps WHERE case_id=$1 ORDER BY timestamp ASC", case_id)
    return {"steps": [{**dict(r), "timestamp": str(r["timestamp"])} for r in rows]}


@router.get("/audit")
async def get_audit_log(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the audit log for a case (or system-wide if case_id='system')."""
    if case_id == "system":
        rows = await db.fetch("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 200")
    else:
        rows = await db.fetch("SELECT * FROM audit_log WHERE case_id=$1 ORDER BY created_at DESC LIMIT 200", case_id)

    return [{
        "id": str(r.get("log_id", r.get("id", ""))),
        "timestamp": str(r.get("created_at", "")),
        "user": r.get("performed_by", "SYSTEM"),
        "role": r.get("role", "-"),
        "action": r.get("action", ""),
        "resource": r.get("resource_type", ""),
        "result": r.get("result", "SUCCESS"),
        "ip": r.get("ip_address", "internal"),
    } for r in rows]
