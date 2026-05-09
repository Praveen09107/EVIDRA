"""
EVIDRA — Bias & Uncertainty Assessor (Tier 6).

Scans the audit trail and claim graph to flag confirmation bias,
missing evidence, or overconfidence in the hypothesis.
"""
import json
from uuid import UUID
from agents.base import BaseAgent
from core.database import db
from core.llm_gateway import llm

class BiasUncertaintyAgent(BaseAgent):
    agent_id = "bias_uncertainty"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Assess systemic bias and missing data."""
        
        # 1. Fetch data
        claims = await db.fetch("SELECT * FROM claims WHERE case_id=$1", case_id)
        relations = await db.fetch("SELECT * FROM claim_relations WHERE case_id=$1", case_id)
        
        prompt = f"""
        Analyze this case graph for cognitive bias (e.g. tunnel vision, missing data, over-reliance on one source).
        Return ONLY valid JSON:
        {{
            "bias_flags": [
                {{"type": "MISSING_EVIDENCE|OVERCONFIDENCE|SOURCE_BIAS", "description": "string", "severity": "HIGH|MEDIUM|LOW"}}
            ],
            "overall_uncertainty_score": float (0-1, higher means more uncertain)
        }}
        
        Claims: {len(claims)} total.
        Contradictions: {len([r for r in relations if r["relation"] == 'CONTRADICTS'])}
        """
        
        resp = await llm.complete(
            task="bias_assess",
            prompt=prompt,
            system_prompt="You are an algorithmic bias auditor."
        )
        
        try:
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            assessment = json.loads(clean_json)
            
            await db.execute(
                """
                INSERT INTO uncertainty_reports (case_id, pipeline_run_id, bias_flags, overall_score)
                VALUES ($1, $2, $3, $4)
                """,
                case_id, pipeline_run_id, json.dumps(assessment.get("bias_flags", [])), 
                float(assessment.get("overall_uncertainty_score", 0.5))
            )
            
            await self.log_step(
                "CONSISTENCY_CHECK",
                "Bias Assessment",
                f"Generated {len(assessment.get('bias_flags', []))} bias flags.",
                confidence=0.9
            )
            
            return assessment
            
        except Exception as e:
            return {"status": "FAILED", "reason": str(e)}
