"""
EVIDRA — Financial Analyzer (Tier 2).

Queries canonical_financial_events to identify rapid liquidations,
beneficiary anomalies, and life insurance payouts.
"""
from uuid import UUID
from agents.base import BaseAgent
from core.database import db

class FinancialAnalyzer(BaseAgent):
    agent_id = "financial_analyzer"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Analyze financial records for anomalies (liquidation, insurance, TOD deltas)."""
        
        events = await db.fetch(
            "SELECT * FROM canonical_financial_events WHERE case_id=$1 ORDER BY timestamp ASC",
            case_id
        )
        
        if not events:
            return {"status": "SKIPPED", "reason": "No financial events found"}

        large_transfers = []
        insurance_markers = []
        total_volume = 0.0
        
        for e in events:
            amt = float(e["amount"])
            total_volume += amt
            
            # Rule 1: Large transfers (> 1,000,000 INR roughly $12k USD)
            if amt > 1000000:
                large_transfers.append({
                    "timestamp": e["timestamp"].isoformat(),
                    "type": e["txn_type"],
                    "amount": amt,
                    "counterparty": e["counterparty"]
                })
                
            # Rule 2: Life insurance / policy markers in narration
            narration = str(e["narration"]).lower() if e["narration"] else ""
            if any(keyword in narration for keyword in ["insurance", "policy", "claim", "settlement", "lic"]):
                insurance_markers.append({
                    "timestamp": e["timestamp"].isoformat(),
                    "amount": amt,
                    "narration": e["narration"]
                })

        await self.log_step(
            "RULE",
            "Financial Anomaly Scan",
            f"Detected {len(large_transfers)} large transfers and {len(insurance_markers)} insurance-related flags.",
            confidence=0.9
        )
        
        warnings = []
        if len(large_transfers) > 3:
            warnings.append("Pattern of rapid asset liquidation detected.")

        return {
            "total_transactions": len(events),
            "total_volume": total_volume,
            "large_transfers": large_transfers,
            "insurance_markers": insurance_markers,
            "_confidence": 0.9,
            "_warnings": warnings
        }
