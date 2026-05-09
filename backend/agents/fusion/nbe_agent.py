"""
EVIDRA — Next Best Evidence (NBE) Agent (Tier 7).

Recommends the specific missing files or actions that would maximize
Information Gain (IG) and resolve contradictions.
"""
import json
from uuid import UUID
from agents.base import BaseAgent
from core.database import db
from core.llm_gateway import llm

class NbeAgent(BaseAgent):
    agent_id = "nbe_agent"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Suggest actions to resolve uncertainty."""
        
        bias_res = await self.get_prior_result("bias_uncertainty")
        hyp_res = await self.get_prior_result("hypothesis_manager")
        
        prompt = f"""
        Based on the current uncertainty and hypotheses, suggest 2-3 specific "Next Best Evidence" actions to take.
        Return ONLY valid JSON:
        [
            {{
                "label": "string (e.g. Subpoena victim's smartwatch data)",
                "description": "string",
                "action_type": "COLLECT_EVIDENCE|MANUAL_REVIEW|EXTERNAL_CONSULT",
                "expected_ig": float (0-1)
            }}
        ]
        
        Leading Hypothesis: {hyp_res.get('leading_hypothesis') if hyp_res else 'Unknown'}
        Bias Flags: {json.dumps(bias_res.get('bias_flags', [])) if bias_res else 'None'}
        """
        
        resp = await llm.complete(
            task="nbe_suggest",
            prompt=prompt,
            system_prompt="You are an investigative strategy advisor."
        )
        
        try:
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            suggestions = json.loads(clean_json)
            
            for s in suggestions:
                await db.execute(
                    """
                    INSERT INTO nbe_suggestions (case_id, pipeline_run_id, label, description, action_type, expected_ig)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    case_id, pipeline_run_id, s["label"], s["description"], 
                    s["action_type"], float(s.get("expected_ig", 0.5))
                )
                
            await self.log_step(
                "RULE",
                "NBE Generation",
                f"Suggested {len(suggestions)} next steps.",
                confidence=0.9
            )
            
            return {"suggestions": len(suggestions), "_confidence": 0.9}
            
        except Exception as e:
            return {"status": "FAILED", "reason": str(e)}
