"""
EVIDRA — Timeline API.

Fetches unified timeline events for the frontend visualization.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}/timeline", tags=["Timeline"])

@router.get("")
async def get_timeline(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get all timeline events, ordered chronologically."""
    # Note: in a real system we'd use the unified `timeline_events` table
    # For now, we aggregate CDR and Fin events directly to guarantee data
    cdr_events = await db.fetch(
        "SELECT event_id as id, event_timestamp as timestamp, 'CDR' as source, event_type, duration_seconds as duration "
        "FROM canonical_cdr_events WHERE case_id=$1", case_id
    )
    fin_events = await db.fetch(
        "SELECT event_id as id, timestamp, 'FINANCIAL' as source, txn_type as event_type, amount "
        "FROM canonical_financial_events WHERE case_id=$1", case_id
    )
    
    events = [dict(e) for e in cdr_events] + [dict(e) for e in fin_events]
    # Sort and stringify dates
    for e in events:
        e["timestamp"] = str(e["timestamp"])
    events.sort(key=lambda x: x["timestamp"])
    
    return {"events": events}
