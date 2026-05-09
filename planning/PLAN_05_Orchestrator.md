# PLAN 05 — Orchestrator & DAG Execution Engine
**Owner:** Dev A | **Hour:** 3:00–4:00 | **Priority:** CRITICAL
**Audit Status:** ✅ GAP-7 FIXED — PAUSED_FOR_REVIEW state added (2026-05-10)

---

## 1. Objective
Build the python-based Orchestrator that controls the 8-tier agent DAG. It takes a list of available document types, builds the execution plan according to `CANONICAL_01`, stores it in the database, dispatches Tier 0 agents via Redis Streams, and listens on `orchestrator:completions` to trigger subsequent tiers.

---

## 2. DAG Builder Logic

**File: `backend/orchestrator/dag.py`**

```python
from typing import Dict, Set

def build_agent_plan(doc_types: Set[str], has_scanned: bool = True) -> Dict[str, dict]:
    """
    Build the execution plan based on uploaded evidence types.
    Matches CANONICAL_01_Agent_DAG_and_Orchestration.
    """
    plan = {}

    # TIER 0
    plan["evidence_parser"] = {"tier": 0, "depends_on": [], "required": True}
    if has_scanned:
        plan["ocr"] = {"tier": 0, "depends_on": [], "required": False}

    # TIER 1
    plan["format_normalizer"] = {
        "tier": 1,
        "depends_on": ["evidence_parser"] + (["ocr"] if has_scanned else []),
        "required": True
    }

    # TIER 2 — conditional on doc types
    tier2_agents = []
    if "AUTOPSY_REPORT" in doc_types:
        plan["autopsy_agent"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("autopsy_agent")
    if "CDR" in doc_types:
        plan["cdr_analyzer"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("cdr_analyzer")
    if "FINANCIAL_RECORDS" in doc_types:
        plan["financial_analyzer"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("financial_analyzer")
    if "DEVICE_DATA" in doc_types or "CCTV" in doc_types:
        plan["image_agent"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("image_agent")

    # TIER 3 — temporal intelligence
    if "autopsy_agent" in plan:
        plan["tod_agent"] = {"tier": 3, "depends_on": ["autopsy_agent"]}
    
    digital_agents = [a for a in ["cdr_analyzer", "financial_analyzer", "image_agent"] if a in plan]
    if digital_agents:
        plan["timeline_anomaly"] = {"tier": 3, "depends_on": digital_agents}
    if len(digital_agents) >= 1 and "image_agent" in plan:
        plan["collision_agent"] = {"tier": 3, "depends_on": digital_agents}

    # TIER 4 — fusion
    hotspot_deps = [a for a in ["tod_agent", "timeline_anomaly", "collision_agent"] if a in plan]
    if len(hotspot_deps) >= 2:
        plan["hotspot_engine"] = {"tier": 4, "depends_on": hotspot_deps}
    
    text_sources = [a for a in ["autopsy_agent", "cdr_analyzer", "financial_analyzer"] if a in plan]
    if text_sources:
        plan["claim_extractor"] = {"tier": 4, "depends_on": text_sources}

    # TIER 5 — reasoning
    tier5_deps = [a for a in plan if plan[a].get("tier", 0) <= 4]
    if "claim_extractor" in plan:
        plan["evidence_claim_mapper"] = {"tier": 5, "depends_on": ["claim_extractor"] + tier2_agents}
    
    plan["hypothesis_manager"] = {"tier": 5, "depends_on": tier5_deps, "required": True}
    plan["bias_uncertainty"] = {"tier": 5, "depends_on": tier5_deps, "required": True}

    # TIER 6 — guidance
    plan["nbe_agent"] = {
        "tier": 6,
        "depends_on": ["hypothesis_manager", "bias_uncertainty"],
        "required": True
    }

    # TIER 7 — audit
    plan["reasoning_replay"] = {"tier": 7, "depends_on": list(plan.keys()), "required": True}

    return plan
```

---

## 3. Dispatcher Logic

**File: `backend/orchestrator/dispatcher.py`**

```python
import json
import logging
from uuid import UUID
from core.database import db
from core.redis_client import publish_task, publish_ws_event

logger = logging.getLogger("orchestrator")

async def create_pipeline_run(case_id: UUID, user_id: UUID, plan: dict) -> UUID:
    """Create a new pipeline run and agent_tasks records."""
    run_id = await db.fetchval(
        "INSERT INTO pipeline_runs (case_id, triggered_by, agent_plan, started_at, status) "
        "VALUES ($1, $2, $3, NOW(), 'RUNNING') RETURNING pipeline_run_id",
        case_id, user_id, json.dumps(plan)
    )
    
    # Insert all tasks
    tasks = []
    for agent_id, config in plan.items():
        tasks.append((
            run_id, agent_id, config["tier"], config.get("depends_on", [])
        ))
    
    await db.executemany(
        "INSERT INTO agent_tasks (pipeline_run_id, agent_id, tier, depends_on) "
        "VALUES ($1, $2, $3, $4)",
        tasks
    )
    return run_id

async def dispatch_ready_agents(pipeline_run_id: UUID, case_id: UUID):
    """
    Find agents whose dependencies are all COMPLETE or SKIPPED, 
    and whose status is currently PENDING.
    
    GAP-7 FIX: After Tier 1 (format_normalizer) completes,
    PAUSE the pipeline for human evidence review before running ML agents.
    """
    # Check if pipeline is paused
    run_record = await db.fetchrow(
        "SELECT agent_plan, status FROM pipeline_runs WHERE pipeline_run_id=$1", pipeline_run_id
    )
    if run_record and run_record["status"] == "PAUSED_FOR_REVIEW":
        logger.info(f"Pipeline {pipeline_run_id} is PAUSED_FOR_REVIEW. Skipping dispatch.")
        return 0
    
    plan = json.loads(run_record["agent_plan"]) if run_record else {}
    
    tasks = await db.fetch(
        "SELECT * FROM agent_tasks WHERE pipeline_run_id=$1", pipeline_run_id
    )
    
    tasks_by_id = {t["agent_id"]: dict(t) for t in tasks}
    dispatched_count = 0
    all_done = True
    any_failed_required = False
    
    # GAP-7: Check if Tier 1 just completed → pause for human review
    tier1_agents = [aid for aid, cfg in plan.items() if cfg.get("tier") == 1]
    tier1_all_done = all(
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
            
            if deps_ready and task["status"] == "PENDING":
                # Dispatch it!
                await db.execute("UPDATE agent_tasks SET status='DISPATCHED' WHERE task_id=$1", task["task_id"])
                
                await publish_task(agent_id, {
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
```

---

## 4. Main Orchestrator Loop

**File: `backend/orchestrator/main.py`**

```python
"""
The Orchestrator Daemon.
Runs independently. Listens to 'orchestrator:completions' Redis stream.
When an agent finishes, it triggers the dispatcher to check for next steps.
"""
import asyncio
import logging
from uuid import UUID
from core.database import db
from core.redis_client import get_redis
from orchestrator.dispatcher import dispatch_ready_agents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

async def orchestrator_loop():
    await db.get_pool()
    r = await get_redis()
    
    stream_key = "orchestrator:completions"
    last_id = "0-0"
    
    logger.info("Orchestrator started, listening for completions...")
    
    while True:
        try:
            results = await r.xread({stream_key: last_id}, count=10, block=5000)
            if not results:
                continue
                
            for stream, messages in results:
                for msg_id, data in messages:
                    last_id = msg_id
                    agent_id = data["agent_id"]
                    pipeline_run_id = UUID(data["pipeline_run_id"])
                    status = data["status"]
                    
                    logger.info(f"Received {status} from {agent_id} for run {str(pipeline_run_id)[:8]}")
                    
                    # Fetch case_id
                    run = await db.fetchrow("SELECT case_id FROM pipeline_runs WHERE pipeline_run_id=$1", pipeline_run_id)
                    if run:
                        await dispatch_ready_agents(pipeline_run_id, run["case_id"])
                        
        except Exception as e:
            logger.error(f"Orchestrator loop error: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(orchestrator_loop())
```

---

## 5. Connecting Gateway to Orchestrator

**File: `backend/api/pipeline.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from core.database import db
from api.auth import get_current_user
from orchestrator.dag import build_agent_plan
from orchestrator.dispatcher import create_pipeline_run, dispatch_ready_agents
import json

router = APIRouter()

@router.post("/{case_id}/pipeline/trigger")
async def trigger_pipeline(case_id: str, user_id: str = Depends(get_current_user)):
    files = await db.fetch("SELECT doc_type FROM case_files WHERE case_id=$1", case_id)
    doc_types = {f["doc_type"] for f in files}
    
    if not doc_types:
        raise HTTPException(400, "Cannot run pipeline: no files uploaded.")
        
    await db.execute("UPDATE cases SET status='IN_ANALYSIS' WHERE case_id=$1", case_id)
    
    plan = build_agent_plan(doc_types, has_scanned=True)
    run_id = await create_pipeline_run(case_id, user_id, plan)
    
    # Dispatch Tier 0
    await dispatch_ready_agents(run_id, case_id)
    
    return {"message": "Pipeline triggered", "pipeline_run_id": run_id}

@router.get("/{case_id}/pipeline/status")
async def get_pipeline_status(case_id: str):
    run = await db.fetchrow(
        "SELECT * FROM pipeline_runs WHERE case_id=$1 ORDER BY created_at DESC LIMIT 1", case_id
    )
    if not run:
        return {"status": "NOT_STARTED"}
        
    tasks = await db.fetch("SELECT agent_id, status, duration_ms FROM agent_tasks WHERE pipeline_run_id=$1", run["pipeline_run_id"])
    
    return {
        "pipeline_run_id": run["pipeline_run_id"],
        "status": run["status"],
        "agents": [dict(t) for t in tasks]
    }
```

## 6. Acceptance Criteria
- [ ] `build_agent_plan` accurately includes only agents whose dependencies (doc types) are present
- [ ] `trigger_pipeline` successfully writes to `pipeline_runs` and `agent_tasks` and dispatches Tier 0
- [ ] Orchestrator loop receives "COMPLETE" events and dispatches exactly the agents in the next tier
- [ ] Pipeline halts if a "required" agent fails (e.g., `format_normalizer`)
