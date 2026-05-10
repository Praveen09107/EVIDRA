"""
EVIDRA — Hotspot Engine (Tier 4).

Implements Core Agent Specs §M-09:
- Fuses anomaly windows from Timeline Agent with TOD window
- Fuses suspicious contacts, financial anomalies, and geographic clusters
- Classifies hotspot types (TEMPORAL/CONTACT/FINANCIAL/GEOGRAPHIC/COMPOUND)
- Ranks hotspots by composite score
"""
import logging
from uuid import UUID
from datetime import datetime
from agents.base import BaseAgent
from core.database import db

logger = logging.getLogger("evidra.hotspot")


class HotspotEngine(BaseAgent):
    agent_id = "hotspot_engine"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Calculate hotspot scores by fusing multiple signal sources."""

        # 1. Fetch upstream results
        tod_res = await self.get_prior_result("tod_agent")
        anomaly_res = await self.get_prior_result("anomaly_detector")
        cdr_res = await self.get_prior_result("cdr_analyzer")
        fin_res = await self.get_prior_result("financial_analyzer")

        # Parse TOD window
        tod_start = None
        tod_end = None
        if tod_res and tod_res.get("posterior"):
            try:
                tod_start = datetime.fromisoformat(tod_res["posterior"]["tod_window_95_start"])
                tod_end = datetime.fromisoformat(tod_res["posterior"]["tod_window_95_end"])
            except (KeyError, ValueError, TypeError):
                pass

        hotspots = []
        hotspot_id = 0

        # ─── 2. Temporal Hotspots (from anomaly windows) ───
        anomaly_windows = []
        if anomaly_res and anomaly_res.get("anomaly_windows"):
            anomaly_windows = anomaly_res["anomaly_windows"]
        else:
            # Fallback: read from DB
            db_windows = await db.fetch(
                "SELECT * FROM anomaly_windows WHERE case_id=$1", case_id,
            )
            anomaly_windows = [dict(w) for w in db_windows] if db_windows else []

        for w in anomaly_windows:
            try:
                w_start = datetime.fromisoformat(str(w.get("window_start", w.get("time_start", ""))))
                w_end = datetime.fromisoformat(str(w.get("window_end", w.get("time_end", ""))))
            except (ValueError, TypeError):
                continue

            score = float(w.get("avg_anomaly_score", w.get("fused_score", 0.5)))
            within_tod = False

            # Boost if overlaps with TOD window
            if tod_start and tod_end:
                if w_start <= tod_end and w_end >= tod_start:
                    score = min(1.0, score + 0.25)
                    within_tod = True

            hotspot_id += 1
            hotspots.append({
                "id": hotspot_id,
                "type": "TEMPORAL",
                "time_start": w_start.isoformat(),
                "time_end": w_end.isoformat(),
                "score": round(score, 3),
                "within_tod": within_tod,
                "severity": w.get("severity", "MEDIUM"),
                "label": f"Temporal anomaly window ({w.get('severity', 'MEDIUM')})",
            })

        # ─── 3. Contact Hotspots (unknown contacts near TOD) ───
        if cdr_res and cdr_res.get("unknown_contacts_near_tod"):
            for contact in cdr_res["unknown_contacts_near_tod"]:
                hotspot_id += 1
                hotspots.append({
                    "id": hotspot_id,
                    "type": "CONTACT",
                    "time_start": contact.get("first_contact", ""),
                    "time_end": contact.get("last_contact", ""),
                    "score": 0.65,
                    "within_tod": True,
                    "severity": "HIGH",
                    "label": f"Unknown contact: {contact.get('msisdn', 'N/A')} ({contact.get('total_events', 0)} events)",
                })

        # ─── 4. Financial Hotspots ───
        if fin_res and fin_res.get("point_anomalies"):
            for anomaly in fin_res["point_anomalies"]:
                if anomaly.get("severity") in ("HIGH", "CRITICAL"):
                    hotspot_id += 1
                    hotspots.append({
                        "id": hotspot_id,
                        "type": "FINANCIAL",
                        "time_start": anomaly.get("timestamp", ""),
                        "time_end": anomaly.get("timestamp", ""),
                        "score": round(anomaly.get("anomaly_score", 0.6), 3),
                        "within_tod": False,
                        "severity": anomaly.get("severity", "MEDIUM"),
                        "label": f"Financial anomaly: ₹{anomaly.get('amount', 0):,.0f} ({anomaly.get('category', 'UNKNOWN')})",
                    })

        # ─── 5. Tower/Geographic Hotspots ───
        if cdr_res and cdr_res.get("tower_sequence", {}).get("anomalous_jumps"):
            for jump in cdr_res["tower_sequence"]["anomalous_jumps"]:
                hotspot_id += 1
                hotspots.append({
                    "id": hotspot_id,
                    "type": "GEOGRAPHIC",
                    "time_start": "",
                    "time_end": "",
                    "score": 0.60,
                    "within_tod": False,
                    "severity": "MEDIUM",
                    "label": f"Suspicious tower jump: {jump.get('from_tower')} → {jump.get('to_tower')} at {jump.get('speed_kmh', '?')} km/h",
                })

        # ─── 6. Compound Hotspots ───
        # If both temporal AND contact hotspots overlap → compound
        temporal_hotspots = [h for h in hotspots if h["type"] == "TEMPORAL" and h["within_tod"]]
        contact_hotspots = [h for h in hotspots if h["type"] == "CONTACT"]
        if temporal_hotspots and contact_hotspots:
            hotspot_id += 1
            compound_score = min(1.0, max(h["score"] for h in temporal_hotspots) + 0.15)
            hotspots.append({
                "id": hotspot_id,
                "type": "COMPOUND",
                "time_start": temporal_hotspots[0]["time_start"],
                "time_end": temporal_hotspots[0]["time_end"],
                "score": round(compound_score, 3),
                "within_tod": True,
                "severity": "CRITICAL",
                "label": f"Compound: temporal anomaly + unknown contact near TOD",
            })

        # Sort by score descending
        hotspots.sort(key=lambda x: x["score"], reverse=True)

        # ─── 7. Save to DB ───
        for rank, h in enumerate(hotspots, 1):
            try:
                ts = datetime.fromisoformat(h["time_start"]) if h["time_start"] else None
                te = datetime.fromisoformat(h["time_end"]) if h["time_end"] else None
                await db.execute(
                    """
                    INSERT INTO hotspots (case_id, pipeline_run_id, rank, score, time_start, time_end, within_tod_band)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    case_id, pipeline_run_id, rank, h["score"], ts, te, h["within_tod"],
                )
            except Exception as e:
                logger.warning(f"Failed to save hotspot: {e}")

        if not hotspots:
            return {"status": "SKIPPED", "reason": "No signal sources produced hotspots"}

        await self.log_step(
            "BAYESIAN_FUSION",
            "Hotspot Engine Complete",
            f"Built {len(hotspots)} hotspots: "
            f"{sum(1 for h in hotspots if h['type'] == 'TEMPORAL')} temporal, "
            f"{sum(1 for h in hotspots if h['type'] == 'CONTACT')} contact, "
            f"{sum(1 for h in hotspots if h['type'] == 'FINANCIAL')} financial, "
            f"{sum(1 for h in hotspots if h['type'] == 'GEOGRAPHIC')} geographic, "
            f"{sum(1 for h in hotspots if h['type'] == 'COMPOUND')} compound. "
            f"Top score: {hotspots[0]['score']:.2f}",
            confidence=0.88,
        )

        return {
            "total_hotspots": len(hotspots),
            "hotspots": hotspots,
            "top_hotspot_score": hotspots[0]["score"],
            "hotspot_types": list({h["type"] for h in hotspots}),
            "_confidence": 0.88,
        }
