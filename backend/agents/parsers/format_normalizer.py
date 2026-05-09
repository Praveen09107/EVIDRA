"""
EVIDRA — Format Normalizer (Tier 1).

Takes raw text from the Evidence Parser and uses the LLM to structure it into 
standardized JSON arrays. (e.g. converting a raw CDR CSV into canonical_cdr_events).
"""
import json
from uuid import UUID
from agents.base import BaseAgent
from core.llm_gateway import llm
from core.database import db

class FormatNormalizer(BaseAgent):
    agent_id = "format_normalizer"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Normalize raw text into Canonical tables."""
        
        # 1. Fetch Tier 0 output
        prior = await self.get_prior_result("evidence_parser")
        if not prior or "files" not in prior:
            raise ValueError("Missing upstream data from evidence_parser")
            
        warnings = []
        normalized_stats = {"cdr_events": 0, "financial_events": 0}
        
        for file_id, file_data in prior["files"].items():
            doc_type = file_data["doc_type"]
            content = file_data["content"]
            
            if doc_type == "CDR":
                await self._normalize_cdr(case_id, file_id, content)
                normalized_stats["cdr_events"] += 1
                
            elif doc_type == "FINANCIAL_RECORDS":
                await self._normalize_financial(case_id, file_id, content)
                normalized_stats["financial_events"] += 1
                
            else:
                # Other files (Autopsy, CCTV) don't need canonical rows yet,
                # they are processed directly by Tier 2 domain agents.
                pass

        await self.log_step(
            "DATA_NORMALIZATION",
            "Normalized tabular evidence",
            f"Processed CDRs and Financial records into canonical tables. {normalized_stats}",
            confidence=0.9
        )
        
        # Mark files as processed
        await db.execute("UPDATE case_files SET status='PROCESSED', processed_at=NOW() WHERE case_id=$1", case_id)

        return {"stats": normalized_stats, "_warnings": warnings, "_confidence": 0.9}


    async def _normalize_cdr(self, case_id: UUID, file_id: str, raw_csv: str):
        """Use LLM to map raw CSV to canonical CDR events."""
        prompt = f"""
        Extract the first 5 call data records (CDR) from this raw text.
        Return ONLY valid JSON matching this schema:
        [
            {{ "timestamp": "ISO8601", "event_type": "MOC|MTC|SMS_MO|SMS_MT", "source_msisdn": "string", "counterparty": "string", "duration": int, "tower_id": "string", "lat": float, "lon": float }}
        ]
        
        Raw Data:
        {raw_csv[:2000]}
        """
        
        resp = await llm.complete(
            task="evidence_parse",
            prompt=prompt,
            system_prompt="You are a data normalizer. Output raw JSON arrays only. No markdown."
        )
        
        try:
            # Strip markdown if present
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            events = json.loads(clean_json)
            
            # Insert into Canonical Table
            for e in events:
                await db.execute(
                    """
                    INSERT INTO canonical_cdr_events 
                    (case_id, file_id, source_msisdn, event_timestamp, event_type, duration_seconds, counterparty_msisdn, cell_tower_id, lat, lon)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    case_id, UUID(file_id), e.get("source_msisdn"), e.get("timestamp"), 
                    e.get("event_type", "MOC"), e.get("duration", 0), e.get("counterparty"),
                    e.get("tower_id"), e.get("lat"), e.get("lon")
                )
                
        except json.JSONDecodeError:
            await self.log_step("ERROR", "CDR Parse Failed", resp.text[:100], 0.0)


    async def _normalize_financial(self, case_id: UUID, file_id: str, raw_csv: str):
        """Use LLM to map raw CSV to canonical Financial events."""
        prompt = f"""
        Extract financial transactions from this raw text.
        Return ONLY valid JSON matching this schema:
        [
            {{ "timestamp": "ISO8601", "txn_type": "DEBIT|CREDIT", "amount": float, "narration": "string", "counterparty": "string" }}
        ]
        
        Raw Data:
        {raw_csv[:2000]}
        """
        
        resp = await llm.complete(
            task="evidence_parse",
            prompt=prompt,
            system_prompt="You are a data normalizer. Output raw JSON arrays only."
        )
        
        try:
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            events = json.loads(clean_json)
            
            for e in events:
                await db.execute(
                    """
                    INSERT INTO canonical_financial_events 
                    (case_id, file_id, timestamp, txn_type, amount, narration, counterparty)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    case_id, UUID(file_id), e.get("timestamp"), e.get("txn_type", "DEBIT"), 
                    float(e.get("amount", 0)), e.get("narration"), e.get("counterparty")
                )
                
        except json.JSONDecodeError:
            await self.log_step("ERROR", "Financial Parse Failed", resp.text[:100], 0.0)
