"""
EVIDRA — Orchestrator Dispatcher.

Handles creating the pipeline run in the database, inserting tasks,
and dispatching agents via Redis when dependencies are met.
Implements the GAP-7 PAUSED_FOR_REVIEW logic.
"""
import json
import logging
from uuid import UUID

from core.database import db
from core.redis_client import publish_task, publish_ws_event
from orchestrator.dag import build_agent_plan

logger = logging.getLogger("evidra.orchestrator")

async def create_pipeline_run(case_id: UUID, pipeline_run_id: UUID) -> dict:
    """
    Look up available files for the case, build the DAG, and populate agent_tasks.
    """
    # 1. Identify available evidence types
    files = await db.fetch("SELECT doc_type FROM case_files WHERE case_id=$1 AND status='PENDING'", case_id)
    available_types = set([f["doc_type"] for f in files])
    
    # 2. Build execution plan
    plan = build_agent_plan(available_types)
    
    # 3. Save plan to pipeline_runs
    await db.execute(
        "UPDATE pipeline_runs SET agent_plan=$1, status='RUNNING', started_at=NOW() WHERE pipeline_run_id=$2",
        json.dumps(plan), pipeline_run_id
    )
    
    # 4. Insert tasks into agent_tasks
    for agent_id, config in plan.items():
        await db.execute(
            """
            INSERT INTO agent_tasks (pipeline_run_id, agent_id, tier, depends_on)
            VALUES ($1, $2, $3, $4)
            """,
            pipeline_run_id, agent_id, config["tier"], config["depends_on"]
        )
        
    logger.info(f"Created pipeline run {pipeline_run_id} with {len(plan)} agents.")
    return plan


async def dispatch_ready_agents(pipeline_run_id: UUID, case_id: UUID) -> int:
    """
    Find agents whose dependencies are COMPLETE or SKIPPED, and dispatch them.
    Implements the PAUSED_FOR_REVIEW gap fix.
    """
    # 1. Check if pipeline is paused
    run_record = await db.fetchrow(
        "SELECT agent_plan, status FROM pipeline_runs WHERE pipeline_run_id=$1", pipeline_run_id
    )
    if run_record and run_record["status"] == "PAUSED_FOR_REVIEW":
        logger.info(f"Pipeline {pipeline_run_id} is PAUSED_FOR_REVIEW. Skipping dispatch.")
        return 0
    
    plan = json.loads(run_record["agent_plan"]) if run_record else {}
    
    tasks = await db.fetch("SELECT * FROM agent_tasks WHERE pipeline_run_id=$1", pipeline_run_id)
    tasks_by_id = {t["agent_id"]: dict(t) for t in tasks}
    
    dispatched_count = 0
    all_done = True
    any_failed_required = False
    
    # GAP-7: Check if Tier 1 just completed → pause for human review
    tier1_agents = [aid for aid, cfg in plan.items() if cfg.get("tier") == 1]
    tier1_all_done = bool(tier1_agents) and all(
        tasks_by_id.get(a, {}).get("status") in ["COMPLETE", "SKIPPED"]
        for a in tier1_agents
    )
    tier2_not_started = all(
        tasks_by_id.get(a, {}).get("status") == "PENDING"
        for a in tasks_by_id if plan.get(a, {}).get("tier", 0) >= 2
    )
    
    if tier1_agents and tier1_all_done and tier2_not_started:
        logger.info(f"Tier 1 complete. Pausing pipeline for human review.")
        await db.execute(
            "UPDATE pipeline_runs SET status='PAUSED_FOR_REVIEW' WHERE pipeline_run_id=$1",
            pipeline_run_id
        )
        await db.execute(
            "UPDATE cases SET status='PAUSED_FOR_REVIEW' WHERE case_id=$1", case_id
        )
        await publish_ws_event(str(case_id), "PIPELINE_PAUSED_FOR_REVIEW", {
            "run_id": str(pipeline_run_id),
            "message": "Evidence parsed. Please review extracted data before proceeding."
        })
        return 0
    
    # Normal dispatch logic
    for agent_id, task in tasks_by_id.items():
        if task["status"] in ["PENDING", "FAILED"]:
            all_done = False
            
            # Check dependencies
            deps_ready = True
            for dep in task["depends_on"]:
                dep_status = tasks_by_id.get(dep, {}).get("status")
                if dep_status not in ["COMPLETE", "SKIPPED"]:
                    deps_ready = False
                    # If a required dependency failed, mark this as skipped
                    if dep_status == "FAILED" and plan.get(dep, {}).get("required", False):
                        await db.execute("UPDATE agent_tasks SET status='SKIPPED' WHERE task_id=$1", task["task_id"])
                        deps_ready = False
                    break
            
            # Dispatch
            if deps_ready and task["status"] == "PENDING":
                await db.execute("UPDATE agent_tasks SET status='DISPATCHED' WHERE task_id=$1", task["task_id"])
                
                # Publish to worker stream
                await publish_task(f"agent:{agent_id}", {
                    "task_id": str(task["task_id"]),
                    "pipeline_run_id": str(pipeline_run_id),
                    "case_id": str(case_id),
                    "agent_id": agent_id,
                    "attempt": task["attempt_count"] + 1
                })
                dispatched_count += 1
                logger.info(f"Dispatched {agent_id} (Tier {task['tier']})")
                
        elif task["status"] == "FAILED" and plan.get(agent_id, {}).get("required", False):
            any_failed_required = True
            
    # Terminal states
    if all_done:
        logger.info(f"Pipeline {pipeline_run_id} COMPLETE.")
        await db.execute("UPDATE pipeline_runs SET status='COMPLETE', completed_at=NOW() WHERE pipeline_run_id=$1", pipeline_run_id)
        await publish_ws_event(str(case_id), "PIPELINE_COMPLETED", {"run_id": str(pipeline_run_id)})
        await db.execute("UPDATE cases SET status='REVIEW' WHERE case_id=$1", case_id)
        
    elif any_failed_required:
        logger.error(f"Pipeline {pipeline_run_id} FAILED (required agent failed).")
        await db.execute("UPDATE pipeline_runs SET status='FAILED', completed_at=NOW() WHERE pipeline_run_id=$1", pipeline_run_id)
        await publish_ws_event(str(case_id), "PIPELINE_FAILED", {"run_id": str(pipeline_run_id)})
        
    return dispatched_count
