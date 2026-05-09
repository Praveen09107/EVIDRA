"""
EVIDRA — Replay & Audit API.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}/replay", tags=["Replay"])

@router.get("/steps")
async def get_replay_steps(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the immutable reasoning audit trail."""
    rows = await db.fetch("SELECT * FROM replay_steps WHERE case_id=$1 ORDER BY timestamp ASC", case_id)
    return {"steps": [{**dict(r), "timestamp": str(r["timestamp"])} for r in rows]}
