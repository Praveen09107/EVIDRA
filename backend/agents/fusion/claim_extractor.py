"""
EVIDRA — Claim Extractor (Tier 4).

Uses the LLM to read the outputs of all Tier 2 domain agents and convert
them into discrete, testable "Claims".
"""
import json
from uuid import UUID
from agents.base import BaseAgent
from core.database import db
from core.llm_gateway import llm

class ClaimExtractor(BaseAgent):
    agent_id = "claim_extractor"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Extract atomic factual claims from all domain agent outputs."""
        
        # 1. Gather all upstream reports
        reports = {}
        for aid in ["autopsy_agent", "cdr_analyzer", "financial_analyzer"]:
            res = await self.get_prior_result(aid)
            if res and res.get("status") != "SKIPPED":
                reports[aid] = res
                
        if not reports:
            return {"status": "SKIPPED", "reason": "No domain reports available to extract claims"}

        prompt = f"""
        Analyze the following domain agent outputs and extract 3-5 distinct, atomic factual CLAIMS.
        A claim is a single testable statement (e.g. "The victim died of blunt force trauma").
        
        Return ONLY valid JSON:
        [
            {{
                "text": "The victim had a >24h silence window on their phone",
                "claim_type": "EVENT|STATE|ALIBI",
                "source_agent": "cdr_analyzer",
                "certainty": 0.9
            }}
        ]
        
        Agent Outputs:
        {json.dumps(reports)[:8000]}
        """
        
        resp = await llm.complete(
            task="claim_extract",
            prompt=prompt,
            system_prompt="You are an expert investigative analyst."
        )
        
        try:
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            claims = json.loads(clean_json)
            
            for c in claims:
                await db.execute(
                    """
                    INSERT INTO claims (case_id, pipeline_run_id, text, claim_type, certainty, source_agent)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    case_id, pipeline_run_id, c["text"], c.get("claim_type", "EVENT"),
                    c.get("certainty", 0.8), c.get("source_agent")
                )
                
            await self.log_step(
                "LLM_EXTRACTION",
                "Claim Extraction",
                f"Extracted {len(claims)} distinct factual claims from domain reports.",
                confidence=0.85
            )
            
            return {"claims_extracted": len(claims), "_confidence": 0.85}
            
        except json.JSONDecodeError:
             await self.log_step("ERROR", "Claim extraction failed", resp.text[:100], 0.0)
             raise ValueError("LLM returned invalid JSON for claims")
