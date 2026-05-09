"""
EVIDRA — Hypothesis Manager (Tier 6).

Evaluates the 5 MANNERS OF DEATH (Natural, Accident, Suicide, Homicide, Undetermined)
using an LLM-driven Bayesian-style posterior update based on all accumulated claims and relations.
"""
import json
from uuid import UUID
from agents.base import BaseAgent
from core.database import db
from core.llm_gateway import llm

class HypothesisManager(BaseAgent):
    agent_id = "hypothesis_manager"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Evaluate the 5 core hypotheses."""
        
        # 1. Fetch all claims and relations
        claims = await db.fetch("SELECT * FROM claims WHERE case_id=$1", case_id)
        relations = await db.fetch("SELECT * FROM claim_relations WHERE case_id=$1", case_id)
        
        if not claims:
            return {"status": "SKIPPED", "reason": "No claims available for hypothesis testing"}
            
        context = {
            "claims": [{"id": str(c["claim_id"]), "text": c["text"]} for c in claims],
            "contradictions": [
                {"from": str(r["from_claim_id"]), "to": str(r["to_claim_id"])} 
                for r in relations if r["relation"] == "CONTRADICTS"
            ]
        }
        
        prompt = f"""
        Based on the following extracted claims and contradictions, evaluate the probability of the 5 manners of death.
        Return ONLY valid JSON. Probabilities MUST sum to 1.0 exactly.
        
        Schema:
        {{
            "NATURAL": {{"probability": float, "summary": "string"}},
            "ACCIDENT": {{"probability": float, "summary": "string"}},
            "SUICIDE": {{"probability": float, "summary": "string"}},
            "HOMICIDE": {{"probability": float, "summary": "string"}},
            "UNDETERMINED": {{"probability": float, "summary": "string"}}
        }}
        
        Context:
        {json.dumps(context)}
        """
        
        resp = await llm.complete(
            task="hypothesis_reason",
            prompt=prompt,
            system_prompt="You are a Bayesian hypothesis evaluator for forensic investigations."
        )
        
        try:
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            hypotheses = json.loads(clean_json)
            
            # Save to DB
            for key, data in hypotheses.items():
                await db.execute(
                    """
                    INSERT INTO hypothesis_history (case_id, pipeline_run_id, hypothesis_key, probability, evidence_summary)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    case_id, pipeline_run_id, key, float(data["probability"]), data["summary"]
                )
                
            # Find most likely
            top_hyp = max(hypotheses.items(), key=lambda x: x[1]["probability"])
            
            await self.log_step(
                "HYPOTHESIS_SCORE",
                "Calculated Posterior Probabilities",
                f"Most likely manner: {top_hyp[0]} ({top_hyp[1]['probability']:.2f})",
                confidence=0.85
            )
            
            return {
                "hypotheses": hypotheses,
                "leading_hypothesis": top_hyp[0],
                "_confidence": 0.85
            }
            
        except Exception as e:
            await self.log_step("ERROR", "Hypothesis evaluation failed", str(e), 0.0)
            return {"status": "FAILED", "reason": "JSON decode error"}
