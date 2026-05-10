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
    cdr_events = await db.fetch(
        "SELECT event_id as id, event_timestamp as timestamp, 'CDR' as source, event_type, duration_seconds as duration "
        "FROM canonical_cdr_events WHERE case_id=$1", case_id
    )
    fin_events = await db.fetch(
        "SELECT event_id as id, timestamp, 'FINANCIAL' as source, txn_type as event_type, amount "
        "FROM canonical_financial_events WHERE case_id=$1", case_id
    )

    events = [dict(e) for e in cdr_events] + [dict(e) for e in fin_events]
    for e in events:
        e["timestamp"] = str(e["timestamp"])
    events.sort(key=lambda x: x["timestamp"])

    return {"events": events}


@router.get("/events")
async def get_timeline_events(case_id: str, current_user: dict = Depends(get_current_user)):
    """Alias: Get all timeline events (frontend expects /timeline/events)."""
    result = await get_timeline(case_id, current_user)
    return result.get("events", [])


@router.get("/summary")
async def get_timeline_summary(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get a timeline summary with hourly buckets and TOD window overlay."""
    # Get the TOD result for the window overlay
    tod_result = await db.fetchrow(
        "SELECT result_data FROM agent_results WHERE case_id=$1 AND agent_id='tod_agent' ORDER BY created_at DESC LIMIT 1",
        case_id
    )

    tod_window = None
    if tod_result and tod_result["result_data"]:
        data = tod_result["result_data"]
        tod_window = {
            "start": data.get("window_start"),
            "end": data.get("window_end"),
            "mode": data.get("mode", "UNKNOWN")
        }

    # Get event counts
    cdr_count = await db.fetchval("SELECT COUNT(*) FROM canonical_cdr_events WHERE case_id=$1", case_id)
    fin_count = await db.fetchval("SELECT COUNT(*) FROM canonical_financial_events WHERE case_id=$1", case_id)

    return {
        "total_cdr_events": cdr_count or 0,
        "total_financial_events": fin_count or 0,
        "todWindow": tod_window,
    }
