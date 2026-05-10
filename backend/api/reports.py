"""
EVIDRA — Reports API.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}", tags=["Reports"])


@router.get("/report")
async def get_report(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the compiled reasoning narrative report (frontend path)."""
    row = await db.fetchrow("SELECT narrative, created_at FROM report_snapshots WHERE case_id=$1 ORDER BY created_at DESC LIMIT 1", case_id)
    if not row:
        return {"narrative": "No report compiled yet. Run the pipeline to completion."}
    return {"narrative": row["narrative"], "created_at": str(row["created_at"])}


@router.get("/reports/final")
async def get_final_report(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the compiled reasoning narrative report (legacy path)."""
    return await get_report(case_id, current_user)
