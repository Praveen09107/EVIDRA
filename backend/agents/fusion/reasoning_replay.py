"""
EVIDRA — Reasoning Replay Compiler (Tier 7).

Runs last. Aggregates all replay_steps from the DB into a final, 
readable Narrative Report and Court-Ready Audit Log.
"""
from uuid import UUID
from agents.base import BaseAgent
from core.database import db

class ReasoningReplay(BaseAgent):
    agent_id = "reasoning_replay"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Compile the final pipeline narrative."""
        
        # We don't need the LLM here, just aggregate the DB
        steps = await db.fetch(
            "SELECT agent_id, step_type, action, interpretation, confidence "
            "FROM replay_steps WHERE pipeline_run_id=$1 ORDER BY timestamp ASC",
            pipeline_run_id
        )
        
        narrative = "Pipeline Execution Summary:\n\n"
        for s in steps:
            narrative += f"[{s['agent_id']}] {s['step_type']}: {s['action']} -> {s['interpretation']} (Conf: {s['confidence']:.2f})\n"
            
        # Save snapshot
        await db.execute(
            """
            INSERT INTO report_snapshots (case_id, pipeline_run_id, report_type, narrative)
            VALUES ($1, $2, 'FULL', $3)
            """,
            case_id, pipeline_run_id, narrative
        )
        
        await self.log_step(
            "LLM_NARRATIVE",
            "Compiled Final Report",
            f"Aggregated {len(steps)} reasoning steps.",
            confidence=1.0
        )
        
        return {
            "total_steps": len(steps),
            "report_length": len(narrative),
            "_confidence": 1.0
        }
