"""
EVIDRA — Pipeline Control API.

Handles triggering the DAG orchestrator, resuming from PAUSED_FOR_REVIEW,
and fetching pipeline status.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.database import db
from core.redis_client import publish_task
from api.auth import get_current_user

router = APIRouter(tags=["Pipeline"])

class PipelineTriggerRequest(BaseModel):
    case_id: str

class PipelineActionRequest(BaseModel):
    action: str  # "RESUME" or "CANCEL"


# ═══════════════════════════════════════════════════════════
# Case-scoped pipeline endpoints (what frontend expects)
# ═══════════════════════════════════════════════════════════

@router.post("/cases/{case_id}/pipeline/trigger")
async def trigger_pipeline_by_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """Trigger the DAG Orchestrator for a specific case (case-scoped path)."""
    case = await db.fetchrow("SELECT status FROM cases WHERE case_id = $1 AND org_id = $2", case_id, current_user["org_id"])
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    run = await db.fetchrow(
        """
        INSERT INTO pipeline_runs (case_id, triggered_by, status)
        VALUES ($1, $2, 'PENDING')
        RETURNING pipeline_run_id
        """,
        case_id, current_user["user_id"]
    )
    run_id = str(run["pipeline_run_id"])

    await db.execute("UPDATE cases SET status = 'IN_ANALYSIS' WHERE case_id = $1", case_id)

    await publish_task("orchestrator:trigger", {
        "case_id": case_id,
        "pipeline_run_id": run_id
    })

    return {"status": "triggered", "pipeline_run_id": run_id, "message": "Pipeline orchestration started"}


@router.get("/cases/{case_id}/pipeline/status")
async def get_pipeline_status_by_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get status of the latest pipeline run for a case."""
    run = await db.fetchrow(
        "SELECT * FROM pipeline_runs WHERE case_id=$1 ORDER BY created_at DESC LIMIT 1",
        case_id
    )
    if not run:
        return {"pipeline_run_id": None, "status": "NO_RUNS", "agents": []}

    run_id = run["pipeline_run_id"]
    tasks = await db.fetch(
        "SELECT agent_id, status, tier, duration_ms FROM agent_tasks WHERE pipeline_run_id = $1 ORDER BY tier ASC",
        run_id
    )

    return {
        "pipeline_run_id": str(run_id),
        "status": run["status"],
        "error_message": run.get("error_message"),
        "agents": [dict(t) for t in tasks]
    }


# ═══════════════════════════════════════════════════════════
# Legacy flat pipeline endpoints (still supported)
# ═══════════════════════════════════════════════════════════

@router.post("/pipeline/trigger")
async def trigger_pipeline(req: PipelineTriggerRequest, current_user: dict = Depends(get_current_user)):
    """Trigger the DAG Orchestrator for a specific case (flat path)."""
    return await trigger_pipeline_by_case(req.case_id, current_user)


@router.post("/pipeline/{run_id}/action")
async def pipeline_action(run_id: str, req: PipelineActionRequest, current_user: dict = Depends(get_current_user)):
    """Resume a PAUSED_FOR_REVIEW pipeline or cancel it."""
    run = await db.fetchrow(
        "SELECT case_id, status FROM pipeline_runs WHERE pipeline_run_id = $1", run_id
    )
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    if req.action == "RESUME":
        if run["status"] != "PAUSED_FOR_REVIEW":
            raise HTTPException(status_code=400, detail="Pipeline is not paused")
            
        await db.execute("UPDATE pipeline_runs SET status = 'RUNNING' WHERE pipeline_run_id = $1", run_id)
        
        await publish_task("orchestrator:trigger", {
            "case_id": str(run["case_id"]),
            "pipeline_run_id": run_id
        })
        return {"status": "resumed"}

    elif req.action == "CANCEL":
        await db.execute("UPDATE pipeline_runs SET status = 'CANCELLED' WHERE pipeline_run_id = $1", run_id)
        return {"status": "cancelled"}

    raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/pipeline/{run_id}/status")
async def get_pipeline_status(run_id: str, current_user: dict = Depends(get_current_user)):
    """Get status of pipeline and all its agents by run_id."""
    run = await db.fetchrow("SELECT * FROM pipeline_runs WHERE pipeline_run_id = $1", run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    tasks = await db.fetch(
        "SELECT agent_id, status, tier, duration_ms FROM agent_tasks WHERE pipeline_run_id = $1 ORDER BY tier ASC",
        run_id
    )

    return {
        "pipeline_run_id": str(run["pipeline_run_id"]),
        "status": run["status"],
        "error_message": run.get("error_message"),
        "agents": [dict(t) for t in tasks]
    }
