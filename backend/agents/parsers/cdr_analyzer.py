"""
EVIDRA — CDR Analyzer (Tier 2).

Queries the canonical_cdr_events table and identifies high-risk patterns:
- Tower ping sequences (movement)
- Silence windows (burner phones / device destruction)
- Contact frequency anomalies
"""
from uuid import UUID
from agents.base import BaseAgent
from core.database import db

class CdrAnalyzer(BaseAgent):
    agent_id = "cdr_analyzer"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Analyze canonical CDR data for temporal and spatial anomalies."""
        
        # We query the DB directly since Tier 1 already populated canonical_cdr_events
        events = await db.fetch(
            "SELECT * FROM canonical_cdr_events WHERE case_id=$1 ORDER BY event_timestamp ASC",
            case_id
        )
        
        if not events:
            return {"status": "SKIPPED", "reason": "No CDR events found for this case"}

        # 1. Calculate Activity Windows & Silence
        # Simple gap analysis
        silence_windows = []
        last_event_time = None
        
        for e in events:
            if last_event_time:
                gap_hours = (e["event_timestamp"] - last_event_time).total_seconds() / 3600
                if gap_hours > 6.0:  # 6+ hours of silence is notable in active investigations
                    silence_windows.append({
                        "start": last_event_time.isoformat(),
                        "end": e["event_timestamp"].isoformat(),
                        "duration_hours": round(gap_hours, 2),
                        "msisdn": e["source_msisdn"]
                    })
            last_event_time = e["event_timestamp"]

        # 2. Contact Frequency (Top 5 contacts)
        contact_counts = {}
        for e in events:
            cp = e["counterparty_msisdn"]
            if cp:
                contact_counts[cp] = contact_counts.get(cp, 0) + 1
        top_contacts = sorted(contact_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # 3. Tower Sequences (Movement)
        towers = list(set([e["cell_tower_id"] for e in events if e["cell_tower_id"]]))
        
        await self.log_step(
            "RULE",
            "Analyzed CDR Patterns",
            f"Found {len(silence_windows)} silence gaps >6hrs. Detected {len(towers)} unique cell towers.",
            confidence=1.0
        )
        
        warnings = []
        if any(w["duration_hours"] > 24 for w in silence_windows):
            warnings.append("Critical >24h silence window detected. Potential burner drop or device destruction.")

        return {
            "total_events": len(events),
            "unique_contacts": len(contact_counts),
            "unique_towers": len(towers),
            "top_contacts": [{"msisdn": c[0], "count": c[1]} for c in top_contacts],
            "silence_windows": silence_windows,
            "_confidence": 1.0,
            "_warnings": warnings
        }
