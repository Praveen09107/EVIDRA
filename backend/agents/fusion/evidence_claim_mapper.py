"""
EVIDRA — Evidence-Claim Mapper (Tier 5).

Uses an LLM (simulating Natural Language Inference - NLI) to map claims against
each other to find SUPPORTS or CONTRADICTS relationships.
"""
import json
from uuid import UUID
from agents.base import BaseAgent
from core.database import db
from core.llm_gateway import llm

class EvidenceClaimMapper(BaseAgent):
    agent_id = "evidence_claim_mapper"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Find contradictions and support between extracted claims."""
        
        claims = await db.fetch("SELECT claim_id, text, source_agent FROM claims WHERE case_id=$1", case_id)
        if len(claims) < 2:
            return {"status": "SKIPPED", "reason": "Not enough claims to find relations"}
            
        claims_list = [{"id": str(c["claim_id"]), "text": c["text"], "source": c["source_agent"]} for c in claims]
        
        prompt = f"""
        Analyze these claims and identify relationships between them.
        Find pairs that either SUPPORT or CONTRADICT each other.
        Return ONLY valid JSON:
        [
            {{
                "from_claim_id": "uuid",
                "to_claim_id": "uuid",
                "relation": "SUPPORTS|CONTRADICTS",
                "confidence": 0.9,
                "reason": "Brief explanation"
            }}
        ]
        
        Claims:
        {json.dumps(claims_list)}
        """
        
        resp = await llm.complete(
            task="nli_classify",
            prompt=prompt,
            system_prompt="You are an NLI relationship mapper."
        )
        
        try:
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            relations = json.loads(clean_json)
            
            contradictions = 0
            supports = 0
            
            for r in relations:
                await db.execute(
                    """
                    INSERT INTO claim_relations (case_id, from_claim_id, to_claim_id, relation, confidence)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    case_id, UUID(r["from_claim_id"]), UUID(r["to_claim_id"]), 
                    r["relation"], float(r.get("confidence", 0.8))
                )
                if r["relation"] == "CONTRADICTS": contradictions += 1
                if r["relation"] == "SUPPORTS": supports += 1
                
            await self.log_step(
                "CONSISTENCY_CHECK",
                "Claim Relationship Mapping",
                f"Found {contradictions} contradictions and {supports} supporting relationships.",
                confidence=0.8
            )
            
            return {
                "relations_found": len(relations),
                "contradictions": contradictions,
                "supports": supports,
                "_confidence": 0.8
            }
            
        except (json.JSONDecodeError, KeyError, ValueError):
            await self.log_step("ERROR", "NLI Mapping failed", resp.text[:100], 0.0)
            return {"status": "FAILED", "reason": "JSON decode error"}
