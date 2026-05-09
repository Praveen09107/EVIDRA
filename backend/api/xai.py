"""
EVIDRA — Explainable AI (XAI) API.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}/xai", tags=["XAI"])

@router.get("/nbe")
async def get_next_best_evidence(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get Next Best Evidence suggestions (Tier 7)."""
    rows = await db.fetch("SELECT * FROM nbe_suggestions WHERE case_id=$1 ORDER BY priority_score DESC", case_id)
    return {"suggestions": [dict(r) for r in rows]}
