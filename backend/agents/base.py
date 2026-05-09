"""
EVIDRA — BaseAgent Abstract Class.

Every agent in the 8-tier DAG inherits from this class.
Enforces the lifecycle contract:
  1. receive task from Redis Stream
  2. update agent_tasks status to RUNNING
  3. call execute() (implemented by each agent)
  4. log every reasoning step to replay_steps (audit trail)
  5. save result to agent_results
  6. update agent_tasks status to COMPLETE
  7. signal orchestrator via Redis Stream

Usage:
    class AutopsyAgent(BaseAgent):
        agent_id = "autopsy_agent"

        async def execute(self, case_id, pipeline_run_id, task_data):
            # ... your logic ...
            await self.log_step("LLM_EXTRACTION", "Extracted 40 fields", "High confidence", 0.92)
            return {"fields": {...}}
"""
import time
import json
import logging
import traceback
from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any, Optional

from core.database import db
from core.redis_client import publish_task, publish_ws_event

logger = logging.getLogger("evidra.agent")


class BaseAgent(ABC):
    """
    Abstract base class for all EVIDRA agents.
    Handles the full lifecycle: status tracking, audit logging, error handling, and orchestrator signaling.
    """

    agent_id: str = ""  # Override in subclass (e.g. "autopsy_agent")

    def __init__(self):
        if not self.agent_id:
            raise ValueError("Subclass must define agent_id")
        self._pipeline_run_id: Optional[UUID] = None
        self._case_id: Optional[UUID] = None
        self._task_id: Optional[UUID] = None
        self._start_time: float = 0

    async def run(self, task_data: dict):
        """
        Full agent lifecycle. Called by the worker daemon.
        DO NOT override this method.
        """
        self._task_id = UUID(task_data["task_id"])
        self._pipeline_run_id = UUID(task_data["pipeline_run_id"])
        self._case_id = UUID(task_data["case_id"])
        attempt = task_data.get("attempt", 1)

        logger.info(f"[{self.agent_id}] Starting (attempt {attempt}, run={str(self._pipeline_run_id)[:8]})")
        self._start_time = time.monotonic()

        try:
            # Mark as RUNNING
            await db.execute(
                "UPDATE agent_tasks SET status='RUNNING', started_at=NOW(), attempt_count=$1 "
                "WHERE task_id=$2",
                attempt, self._task_id
            )

            # Notify frontend
            await publish_ws_event(str(self._case_id), "AGENT_STARTED", {
                "agent_id": self.agent_id,
                "pipeline_run_id": str(self._pipeline_run_id),
            })

            # Execute the agent's logic
            result = await self.execute(self._case_id, self._pipeline_run_id, task_data)

            # Calculate duration
            duration_ms = int((time.monotonic() - self._start_time) * 1000)

            # Save result to agent_results
            confidence = result.pop("_confidence", None) if isinstance(result, dict) else None
            warnings = result.pop("_warnings", []) if isinstance(result, dict) else []

            await db.execute(
                "INSERT INTO agent_results (pipeline_run_id, case_id, agent_id, result_data, confidence, warnings) "
                "VALUES ($1, $2, $3, $4, $5, $6) "
                "ON CONFLICT (pipeline_run_id, agent_id) DO UPDATE SET result_data=$4, confidence=$5, warnings=$6",
                self._pipeline_run_id, self._case_id, self.agent_id,
                json.dumps(result, default=str), confidence, warnings
            )

            # Mark as COMPLETE
            await db.execute(
                "UPDATE agent_tasks SET status='COMPLETE', completed_at=NOW(), duration_ms=$1 WHERE task_id=$2",
                duration_ms, self._task_id
            )

            logger.info(f"[{self.agent_id}] COMPLETE in {duration_ms}ms")

            # Signal orchestrator
            await publish_task("orchestrator:completions", {
                "agent_id": self.agent_id,
                "pipeline_run_id": str(self._pipeline_run_id),
                "case_id": str(self._case_id),
                "status": "COMPLETE",
            })

            # Notify frontend
            await publish_ws_event(str(self._case_id), "AGENT_COMPLETED", {
                "agent_id": self.agent_id,
                "duration_ms": duration_ms,
                "pipeline_run_id": str(self._pipeline_run_id),
            })

        except Exception as e:
            duration_ms = int((time.monotonic() - self._start_time) * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            tb = traceback.format_exc()

            logger.error(f"[{self.agent_id}] FAILED: {error_msg}\n{tb}")

            # Log error step for audit trail
            await self.log_step("ERROR", f"Agent failed: {error_msg}", tb[:500], 0.0)

            # Mark as FAILED
            await db.execute(
                "UPDATE agent_tasks SET status='FAILED', completed_at=NOW(), duration_ms=$1, error_message=$2 WHERE task_id=$3",
                duration_ms, error_msg[:500], self._task_id
            )

            # Signal orchestrator (with FAILED status)
            await publish_task("orchestrator:completions", {
                "agent_id": self.agent_id,
                "pipeline_run_id": str(self._pipeline_run_id),
                "case_id": str(self._case_id),
                "status": "FAILED",
                "error": error_msg[:200],
            })

            # Notify frontend
            await publish_ws_event(str(self._case_id), "AGENT_FAILED", {
                "agent_id": self.agent_id,
                "error": error_msg[:200],
                "pipeline_run_id": str(self._pipeline_run_id),
            })

    @abstractmethod
    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """
        Implement agent logic here. Must return a dict that will be stored as JSONB in agent_results.

        Special keys in the returned dict:
          - "_confidence": float (0-1) → stored in agent_results.confidence
          - "_warnings": list[str] → stored in agent_results.warnings

        Args:
            case_id: The case being analyzed
            pipeline_run_id: Current pipeline run
            task_data: Raw task data from Redis (contains attempt, etc.)

        Returns:
            dict: Result data (stored as JSONB)
        """
        raise NotImplementedError

    # ═══════════════════════════════════════════════════════════
    # HELPER METHODS — Available to all agents
    # ═══════════════════════════════════════════════════════════

    async def log_step(
        self,
        step_type: str,
        action: str,
        interpretation: str,
        confidence: float = 0.5,
        evidence_ids: list[UUID] | None = None,
        warnings: list[str] | None = None
    ):
        """
        Log a reasoning step to replay_steps for audit trail.
        Every significant decision should be logged.

        Args:
            step_type: One of DATA_NORMALIZATION, LLM_EXTRACTION, MODEL_OUTPUT,
                      ML_INFERENCE, PHYSICS_MODEL, BAYESIAN_FUSION, ANOMALY_DETECTION,
                      CONSISTENCY_CHECK, HYPOTHESIS_SCORE, RULE, LLM_NARRATIVE, ERROR
            action: What the agent did (e.g. "Extracted 40 fields from autopsy report")
            interpretation: What the result means (e.g. "High confidence in cause of death")
            confidence: 0.0 - 1.0
            evidence_ids: Optional list of evidence UUIDs this step references
            warnings: Optional list of warning messages
        """
        await db.execute(
            "INSERT INTO replay_steps "
            "(pipeline_run_id, case_id, agent_id, step_type, action, interpretation, confidence, evidence_ids, warnings) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            self._pipeline_run_id, self._case_id, self.agent_id,
            step_type, action, interpretation, confidence,
            evidence_ids or [], warnings or []
        )

    async def get_prior_result(self, agent_id: str) -> Optional[dict]:
        """
        Fetch the result of a previously completed agent in this pipeline run.
        Used by downstream agents to access upstream outputs.

        Args:
            agent_id: e.g. "format_normalizer", "autopsy_agent"

        Returns:
            dict (the result_data JSONB) or None if not found
        """
        row = await db.fetchrow(
            "SELECT result_data FROM agent_results "
            "WHERE pipeline_run_id=$1 AND agent_id=$2",
            self._pipeline_run_id, agent_id
        )
        if row and row["result_data"]:
            return json.loads(row["result_data"]) if isinstance(row["result_data"], str) else row["result_data"]
        return None

    async def get_case_files(self, doc_type: Optional[str] = None) -> list[dict]:
        """
        Get all files for the current case, optionally filtered by doc_type.

        Returns:
            List of file records as dicts.
        """
        if doc_type:
            rows = await db.fetch(
                "SELECT * FROM case_files WHERE case_id=$1 AND doc_type=$2",
                self._case_id, doc_type
            )
        else:
            rows = await db.fetch(
                "SELECT * FROM case_files WHERE case_id=$1", self._case_id
            )
        return [dict(r) for r in rows]
