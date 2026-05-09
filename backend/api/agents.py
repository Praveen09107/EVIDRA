"""
EVIDRA — Agents Registry API.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}/agents", tags=["Agents"])

@router.get("/results")
async def get_agent_results(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get raw JSON results from every completed agent for this case."""
    rows = await db.fetch("SELECT agent_id, result_data, confidence, warnings, created_at FROM agent_results WHERE case_id=$1 ORDER BY created_at DESC", case_id)
    return {"results": [dict(r) for r in rows]}
