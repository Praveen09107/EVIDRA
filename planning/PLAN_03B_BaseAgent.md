# PLAN 03B — BaseAgent Abstract Class & Agent Lifecycle
**Owner:** Dev A | **Hour:** 1:30–2:00 | **Priority:** CRITICAL

---

## 1. Objective
Build the `BaseAgent` abstract base class that every one of the 17 agents inherits from. This class defines the canonical lifecycle: receive task → load prior results → execute → store results → log replay steps → notify completion. No agent can bypass this contract.

---

## 2. Why a Base Class?
Without a common base:
- Each agent would independently handle DB writes, error handling, and replay logging.
- Any change to the lifecycle (e.g., adding a new audit field) would require editing 17 files.
- The orchestrator couldn't treat all agents uniformly.

With `BaseAgent`:
- `run()` is the public method — handles the full lifecycle.
- `execute()` is the abstract method — agents only implement their unique logic.
- Error handling, timing, status updates, and replay logging are automatic.

---

## 3. Full Implementation

**File: `services/base_agent.py`**

```python
"""
BaseAgent — Abstract base class for all AIVENTRA forensic agents.

Every agent inherits from BaseAgent and implements execute().
The run() method handles the complete lifecycle automatically:
    1. Mark task as RUNNING in DB
    2. Load prior agent results (dependencies)
    3. Call execute() — the agent's custom logic
    4. Store result in agent_results table
    5. Mark task as COMPLETE (or FAILED on error)
    6. Notify orchestrator via Redis

Usage:
    class AutopsyAgent(BaseAgent):
        agent_id = "autopsy_agent"
        
        async def execute(self, task: AgentTask) -> AgentResult:
            # Your logic here
            return AgentResult(data={"findings": ...})
"""
import asyncio
import json
import time
import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from uuid import UUID, uuid4

from services.database import db
from services.redis_client import notify_completion, publish_ws_event
from services.llm_gateway import llm

logger = logging.getLogger("agents")


@dataclass
class AgentTask:
    """Input to every agent. Created by the orchestrator when dispatching."""
    task_id: UUID
    pipeline_run_id: UUID
    case_id: UUID
    agent_id: str
    attempt: int = 1
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentTask':
        return cls(
            task_id=UUID(data["task_id"]),
            pipeline_run_id=UUID(data["pipeline_run_id"]),
            case_id=UUID(data["case_id"]),
            agent_id=data["agent_id"],
            attempt=int(data.get("attempt", 1)),
        )


@dataclass
class AgentResult:
    """Output from every agent's execute() method."""
    data: dict = field(default_factory=dict)
    confidence: float = 0.5
    warnings: list = field(default_factory=list)
    
    def to_json(self) -> str:
        return json.dumps(self.data, default=str)


class BaseAgent(ABC):
    """
    Abstract base class for all forensic agents.
    
    Subclasses MUST:
        1. Set `agent_id` class attribute (e.g., "autopsy_agent")
        2. Implement `async execute(self, task: AgentTask) -> AgentResult`
    
    The base class provides:
        - run() — full lifecycle management
        - get_prior_result() — fetch output from a dependency agent
        - log_step() — record a replay step for the reasoning chain
    """
    
    agent_id: str = "base"  # Override in subclass
    
    # ═══════════════════════════════════════════════════════
    # PUBLIC: run() — the full lifecycle, called by workers
    # ═══════════════════════════════════════════════════════
    
    async def run(self, task: AgentTask) -> Optional[AgentResult]:
        """
        Execute the full agent lifecycle.
        This is called by the worker process — agents never call this directly.
        
        Lifecycle:
            1. Update agent_tasks status to RUNNING
            2. Call self.execute(task) — the agent's custom logic
            3. Store result in agent_results table
            4. Update agent_tasks status to COMPLETE
            5. Notify orchestrator via Redis
            6. Push WebSocket event for UI
        
        On failure:
            - Stores error in agent_tasks
            - Notifies orchestrator with FAILED status
            - Does NOT raise — the worker loop continues
        
        Returns:
            AgentResult on success, None on failure
        """
        start_time = time.time()
        
        try:
            # Step 1: Mark RUNNING
            await db.execute(
                "UPDATE agent_tasks SET status='RUNNING', started_at=NOW(), "
                "attempt_count=$1 WHERE task_id=$2",
                task.attempt, task.task_id
            )
            
            # Push UI event
            await self._push_event(task, "AGENT_STARTED", {
                "agent_id": self.agent_id, "attempt": task.attempt
            })
            
            logger.info(f"[{self.agent_id}] Starting task {str(task.task_id)[:8]} "
                       f"(attempt {task.attempt})")
            
            # Step 2: Execute agent logic
            result = await self.execute(task)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Step 3: Store result
            await db.execute(
                "INSERT INTO agent_results (result_id, pipeline_run_id, agent_id, "
                "result_data, confidence, warnings) "
                "VALUES ($1, $2, $3, $4, $5, $6) "
                "ON CONFLICT (pipeline_run_id, agent_id) DO UPDATE SET "
                "result_data=$4, confidence=$5, warnings=$6",
                uuid4(), task.pipeline_run_id, self.agent_id,
                json.dumps(result.data, default=str),
                result.confidence,
                result.warnings or []
            )
            
            # Step 4: Mark COMPLETE
            await db.execute(
                "UPDATE agent_tasks SET status='COMPLETE', completed_at=NOW(), "
                "duration_ms=$1 WHERE task_id=$2",
                elapsed_ms, task.task_id
            )
            
            # Step 5: Notify orchestrator
            await notify_completion(
                self.agent_id, str(task.pipeline_run_id), "COMPLETE"
            )
            
            # Step 6: Push UI event
            await self._push_event(task, "AGENT_COMPLETED", {
                "agent_id": self.agent_id,
                "duration_ms": elapsed_ms,
                "confidence": result.confidence,
            })
            
            logger.info(f"[{self.agent_id}] ✓ Complete in {elapsed_ms}ms "
                       f"(confidence={result.confidence:.2f})")
            
            return result
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            tb = traceback.format_exc()
            
            logger.error(f"[{self.agent_id}] ✗ Failed after {elapsed_ms}ms: {error_msg}")
            logger.debug(f"[{self.agent_id}] Traceback:\n{tb}")
            
            # Mark FAILED
            await db.execute(
                "UPDATE agent_tasks SET status='FAILED', completed_at=NOW(), "
                "duration_ms=$1, error_message=$2 WHERE task_id=$3",
                elapsed_ms, error_msg[:2000], task.task_id
            )
            
            # Notify orchestrator
            await notify_completion(
                self.agent_id, str(task.pipeline_run_id), "FAILED", error=error_msg
            )
            
            # Log a replay step for the failure
            await self._log_replay_step(
                task, "ERROR",
                f"Agent {self.agent_id} failed",
                f"Error: {error_msg[:500]}",
                confidence=0.0
            )
            
            # Push UI event
            await self._push_event(task, "AGENT_FAILED", {
                "agent_id": self.agent_id, "error": error_msg[:200]
            })
            
            return None
    
    # ═══════════════════════════════════════════════════════
    # ABSTRACT: execute() — agents implement this
    # ═══════════════════════════════════════════════════════
    
    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Agent-specific logic. Override in every subclass.
        
        Args:
            task: Contains case_id, pipeline_run_id, and task metadata
        
        Returns:
            AgentResult with data dict, confidence, and optional warnings
        
        Inside execute(), agents should:
            1. Use self.get_prior_result() to fetch dependency outputs
            2. Process data (LLM, ML, rules, etc.)
            3. Use self.log_step() to record reasoning for the replay chain
            4. Return AgentResult with structured output
        """
        raise NotImplementedError
    
    # ═══════════════════════════════════════════════════════
    # HELPER: get_prior_result() — read output from dependency
    # ═══════════════════════════════════════════════════════
    
    async def get_prior_result(self, task: AgentTask, agent_id: str) -> Optional[dict]:
        """
        Fetch the result data from a previously completed agent.
        
        Args:
            task: Current agent's task (provides pipeline_run_id)
            agent_id: The dependency agent's ID (e.g., "autopsy_agent")
        
        Returns:
            The agent's result_data dict, or None if not found/failed
        
        Example:
            autopsy = await self.get_prior_result(task, "autopsy_agent")
            if autopsy:
                injuries = autopsy.get("extractions", [{}])[0].get("injuries", [])
        """
        row = await db.fetchrow(
            "SELECT result_data FROM agent_results "
            "WHERE pipeline_run_id=$1 AND agent_id=$2",
            task.pipeline_run_id, agent_id
        )
        if row and row["result_data"]:
            data = row["result_data"]
            # asyncpg returns JSONB as dict already, but handle string case
            if isinstance(data, str):
                return json.loads(data)
            return data
        return None
    
    # ═══════════════════════════════════════════════════════
    # HELPER: log_step() — record reasoning for replay chain
    # ═══════════════════════════════════════════════════════
    
    def log_step(self, task: AgentTask, step_type: str,
                 action: str, interpretation: str,
                 confidence: float = 0.5,
                 evidence_ids: list = None,
                 warnings: list = None):
        """
        Record a reasoning step for the Reasoning Replay audit trail.
        This is fire-and-forget — it doesn't block the agent.
        
        Args:
            task: Current task context
            step_type: One of DATA_NORMALIZATION, LLM_EXTRACTION, MODEL_OUTPUT,
                      ML_INFERENCE, PHYSICS_MODEL, BAYESIAN_FUSION,
                      ANOMALY_DETECTION, CONSISTENCY_CHECK, HYPOTHESIS_SCORE,
                      RULE, LLM_NARRATIVE, ERROR
            action: What the agent did (e.g., "Sending autopsy text to Gemini")
            interpretation: What the result means (e.g., "Manner: HOMICIDE, 3 injuries")
            confidence: 0.0–1.0 confidence in this step
            evidence_ids: List of file_ids or entity_ids referenced
            warnings: Optional list of warning strings
        """
        # Fire-and-forget async task
        asyncio.create_task(
            self._log_replay_step(
                task, step_type, action, interpretation,
                confidence, evidence_ids, warnings
            )
        )
    
    async def _log_replay_step(self, task, step_type, action, interpretation,
                                confidence=0.5, evidence_ids=None, warnings=None):
        """Internal: actually write the replay step to the database."""
        try:
            # Convert evidence_ids to UUID array
            ev_ids = None
            if evidence_ids:
                ev_ids = [UUID(str(eid)) if not isinstance(eid, UUID) else eid 
                         for eid in evidence_ids]
            
            await db.execute(
                "INSERT INTO replay_steps "
                "(step_id, pipeline_run_id, agent_id, step_type, action, "
                "interpretation, confidence, evidence_ids, warnings) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                uuid4(), task.pipeline_run_id, self.agent_id,
                step_type, action[:1000], interpretation[:2000],
                confidence, ev_ids, warnings or []
            )
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Failed to log replay step: {e}")
    
    async def _push_event(self, task, event_type, data):
        """Push a WebSocket event for real-time UI updates."""
        try:
            await publish_ws_event(str(task.case_id), event_type, data)
        except Exception:
            pass  # Non-critical — don't break agent on WS failure
```

---

## 4. Agent Contract Summary

| Method | Who Calls | Purpose |
|--------|-----------|---------|
| `run(task)` | Worker process | Full lifecycle — never override |
| `execute(task)` | `run()` internally | Agent logic — always override |
| `get_prior_result(task, agent_id)` | `execute()` | Read dependency output |
| `log_step(task, ...)` | `execute()` | Record reasoning for replay |

### Lifecycle Diagram
```
Worker receives Redis message
    │
    ▼
BaseAgent.run(task)
    ├── UPDATE agent_tasks SET status='RUNNING'
    ├── Publish WS event: AGENT_STARTED
    ├── Call self.execute(task) ◄── Agent-specific logic
    │   ├── get_prior_result() — reads from agent_results
    │   ├── [Agent does its work: LLM, ML, rules, etc.]
    │   ├── log_step() × N — records reasoning steps
    │   └── return AgentResult(data={...})
    ├── INSERT INTO agent_results
    ├── UPDATE agent_tasks SET status='COMPLETE'
    ├── Notify orchestrator via Redis
    └── Publish WS event: AGENT_COMPLETED
```

---

## 5. Acceptance Criteria
- [ ] `BaseAgent` is abstract — cannot be instantiated directly
- [ ] `run()` catches all exceptions and marks task FAILED (never crashes worker)
- [ ] `get_prior_result()` returns `None` gracefully when dependency missing
- [ ] `log_step()` is fire-and-forget — doesn't block the agent
- [ ] `agent_results` has ON CONFLICT upsert for re-runs
- [ ] Duration measured accurately in milliseconds
- [ ] WebSocket events published for STARTED/COMPLETED/FAILED
