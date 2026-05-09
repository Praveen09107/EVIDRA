"""
EVIDRA — Hotspot Engine (Tier 4).

Fuses the ML Anomaly Windows with the Physics TOD window to highlight
the most critical temporal regions in the investigation.
"""
from uuid import UUID
from agents.base import BaseAgent
from core.database import db
from datetime import datetime

class HotspotEngine(BaseAgent):
    agent_id = "hotspot_engine"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Calculate hotspot scores by fusing TOD and Anomaly windows."""
        
        # 1. Fetch outputs
        tod_res = await self.get_prior_result("tod_agent")
        
        tod_start = None
        tod_end = None
        if tod_res and tod_res.get("status") != "SKIPPED":
            tod_start = datetime.fromisoformat(tod_res["window_start"])
            tod_end = datetime.fromisoformat(tod_res["window_end"])
            
        anomalies = await db.fetch("SELECT * FROM anomaly_windows WHERE case_id=$1", case_id)
        
        if not anomalies:
            return {"status": "SKIPPED", "reason": "No anomalies to form hotspots"}

        hotspots = []
        for a in anomalies:
            score = float(a["fused_score"])
            
            # Boost score if the anomaly overlaps with the TOD window
            within_tod = False
            if tod_start and tod_end:
                if (a["time_start"] <= tod_end) and (a["time_end"] >= tod_start):
                    score += 0.3 # TOD overlap boost
                    within_tod = True
                    
            hotspots.append({
                "time_start": a["time_start"],
                "time_end": a["time_end"],
                "score": min(1.0, score),
                "within_tod": within_tod,
                "label": a["label"]
            })
            
        # Sort by score descending
        hotspots.sort(key=lambda x: x["score"], reverse=True)
        
        # Save to DB
        rank = 1
        for h in hotspots:
            await db.execute(
                """
                INSERT INTO hotspots (case_id, pipeline_run_id, rank, score, time_start, time_end, within_tod_band)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                case_id, pipeline_run_id, rank, h["score"], h["time_start"], h["time_end"], h["within_tod"]
            )
            rank += 1

        await self.log_step(
            "BAYESIAN_FUSION",
            "Hotspot Engine execution",
            f"Fused {len(anomalies)} anomalies with TOD window. Top hotspot score: {hotspots[0]['score']:.2f}",
            confidence=0.9
        )

        return {
            "total_hotspots": len(hotspots),
            "top_hotspot_score": hotspots[0]["score"],
            "_confidence": 0.9
        }
