"""
EVIDRA — CDR Analyzer (Tier 2 / M-05).

Implements Core Agent Specs §M-05 and ML Spec §3:
- Baseline behavior modeling (daily stats)
- Z-Score silence window detection
- Contact classification (FREQUENT/INFREQUENT/RARE/DORMANT/UNKNOWN)
- TOD behavioral delta computation
- Tower sequence analysis with haversine speed anomaly
- IMEI anomaly detection
- Forensic flags output
"""
import pandas as pd
import numpy as np
from datetime import timedelta
from math import radians, sin, cos, sqrt, atan2
from collections import defaultdict
from uuid import UUID
import logging
from agents.base import BaseAgent
from core.database import db

logger = logging.getLogger("evidra.cdr")


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    if None in [lat1, lon1, lat2, lon2]:
        return float("inf")
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ═══════════════════════════════════════════════════════════
# CONTACT CLASSIFICATION (spec §M-05)
# ═══════════════════════════════════════════════════════════

def classify_contacts(df: pd.DataFrame, tod_estimate: pd.Timestamp = None) -> list[dict]:
    """Classify contacts: FREQUENT/INFREQUENT/RARE/DORMANT/UNKNOWN."""
    contact_stats = {}
    for _, row in df.iterrows():
        cp = row.get("counterparty_msisdn", "")
        if not cp:
            continue
        if cp not in contact_stats:
            contact_stats[cp] = {"count": 0, "first": row["ts"], "last": row["ts"]}
        contact_stats[cp]["count"] += 1
        if row["ts"] < contact_stats[cp]["first"]:
            contact_stats[cp]["first"] = row["ts"]
        if row["ts"] > contact_stats[cp]["last"]:
            contact_stats[cp]["last"] = row["ts"]

    tod_ref = tod_estimate or df["ts"].max()
    results = []
    for cp, stats in contact_stats.items():
        count = stats["count"]
        days_since_last = (tod_ref - stats["last"]).total_seconds() / 86400
        days_since_first = (tod_ref - stats["first"]).total_seconds() / 86400

        if days_since_first <= 7 and count <= 2:
            classification = "UNKNOWN"
        elif days_since_last > 30:
            classification = "DORMANT"
        elif count >= 10:
            classification = "FREQUENT"
        elif count >= 3:
            classification = "INFREQUENT"
        else:
            classification = "RARE"

        results.append({
            "msisdn": cp,
            "classification": classification,
            "total_events": count,
            "first_contact": stats["first"].isoformat(),
            "last_contact": stats["last"].isoformat(),
        })

    return results


# ═══════════════════════════════════════════════════════════
# TOWER SEQUENCE ANALYSIS (spec §M-05)
# ═══════════════════════════════════════════════════════════

def build_tower_sequence(df: pd.DataFrame) -> dict:
    """Analyze tower transitions for speed anomalies."""
    tower_df = df[df["cell_tower_id"].notna() & (df["cell_tower_id"] != "")].sort_values("ts")

    transitions = []
    anomalous_jumps = []

    for i in range(1, len(tower_df)):
        prev = tower_df.iloc[i - 1]
        curr = tower_df.iloc[i]

        if prev["cell_tower_id"] != curr["cell_tower_id"]:
            time_min = (curr["ts"] - prev["ts"]).total_seconds() / 60
            speed = None

            if prev.get("lat") and curr.get("lat") and time_min > 0:
                dist_km = haversine_km(
                    float(prev["lat"]), float(prev["lon"]),
                    float(curr["lat"]), float(curr["lon"]),
                )
                speed = (dist_km / time_min * 60) if time_min > 0 else None

            transition = {
                "from_tower": prev["cell_tower_id"],
                "to_tower": curr["cell_tower_id"],
                "time_diff_min": round(time_min, 1),
                "speed_kmh": round(speed, 1) if speed else None,
                "anomalous": speed is not None and speed > 200,
            }
            transitions.append(transition)
            if transition["anomalous"]:
                anomalous_jumps.append(transition)

    return {
        "total_transitions": len(transitions),
        "anomalous_jumps": anomalous_jumps,
        "unique_towers": int(tower_df["cell_tower_id"].nunique()),
    }


# ═══════════════════════════════════════════════════════════
# IMEI ANOMALY DETECTION (spec §M-05)
# ═══════════════════════════════════════════════════════════

def detect_imei_anomalies(df: pd.DataFrame) -> list[dict]:
    """Detect multiple IMEIs per MSISDN (SIM swapping indicator)."""
    imei_per_msisdn = defaultdict(set)
    for _, row in df.iterrows():
        imei = row.get("imei")
        msisdn = row.get("source_msisdn", "")
        if imei and str(imei).strip():
            imei_per_msisdn[msisdn].add(str(imei).strip())

    anomalies = []
    for msisdn, imei_set in imei_per_msisdn.items():
        if len(imei_set) > 1:
            anomalies.append({
                "type": "MULTIPLE_IMEI",
                "msisdn": msisdn,
                "imei_set": list(imei_set),
                "severity": "MEDIUM",
            })
    return anomalies


class CdrAnalyzer(BaseAgent):
    agent_id = "cdr_analyzer"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        events = await db.fetch(
            "SELECT * FROM canonical_cdr_events WHERE case_id=$1 ORDER BY event_timestamp ASC",
            case_id,
        )
        if not events:
            return {"status": "SKIPPED", "reason": "No CDR events"}

        df = pd.DataFrame([dict(e) for e in events])
        df["ts"] = pd.to_datetime(df["event_timestamp"])

        # ─── 1. Baseline Model ───
        total_days = max((df["ts"].max() - df["ts"].min()).total_seconds() / 86400, 1)
        daily_call_count = len(df) / total_days
        hourly_dist = df["ts"].dt.hour.value_counts().to_dict()
        active_hours = set(df["ts"].dt.hour.unique())
        typical_max_silence = max(24 - len(active_hours), 4)

        baseline = {
            "total_events": len(df),
            "total_days": round(total_days, 1),
            "daily_avg_events": round(daily_call_count, 1),
            "active_hours": sorted(list(active_hours)),
        }

        # ─── 2. Z-Score Silence Detection ───
        silences = []
        gaps = []
        last_ts = None
        for ts in df["ts"]:
            if last_ts:
                gap_h = (ts - last_ts).total_seconds() / 3600
                gaps.append(gap_h)
                if gap_h > 4:
                    gap_mean = np.mean(gaps) if gaps else gap_h
                    gap_std = np.std(gaps) if len(gaps) > 1 else 2.0
                    z_score = (gap_h - gap_mean) / max(gap_std, 1.0)
                    if z_score > 1.0:
                        silences.append({
                            "start": last_ts.isoformat(),
                            "end": ts.isoformat(),
                            "duration_hours": round(gap_h, 2),
                            "z_score": round(z_score, 2),
                            "severity": "HIGH" if z_score > 2.5 else "MEDIUM",
                        })
            last_ts = ts

        # ─── 3. Contact Classification ───
        contacts = classify_contacts(df)
        unknown_near_tod = [c for c in contacts if c["classification"] == "UNKNOWN"]

        # ─── 4. Contact Escalation ───
        most_recent = df["ts"].max()
        alert_start = most_recent - timedelta(hours=72)
        top_contacts = df["counterparty_msisdn"].value_counts().head(10).index

        escalations = []
        for contact in top_contacts:
            if not contact:
                continue
            baseline_ct = len(df[(df["counterparty_msisdn"] == contact) & (df["ts"] < alert_start)])
            alert_ct = len(df[(df["counterparty_msisdn"] == contact) & (df["ts"] >= alert_start)])
            baseline_rate = max(0.1, baseline_ct / max(total_days - 3, 1))
            alert_rate = alert_ct / 3
            ratio = alert_rate / baseline_rate
            if ratio > 2.0 and alert_ct >= 3:
                escalations.append({
                    "contact": contact,
                    "baseline_rate": round(baseline_rate, 2),
                    "alert_rate": round(alert_rate, 2),
                    "ratio": round(ratio, 2),
                })

        # ─── 5. TOD Behavioral Delta ───
        tod_res = await self.get_prior_result("tod_agent")
        tod_delta = {"interpretation": "NOT_COMPUTED"}
        if tod_res and tod_res.get("posterior"):
            try:
                tod_start = pd.Timestamp(tod_res["posterior"].get("tod_window_95_start", tod_res.get("window_start")))
                tod_end = pd.Timestamp(tod_res["posterior"].get("tod_window_95_end", tod_res.get("window_end")))
                tod_events = df[(df["ts"] >= tod_start) & (df["ts"] <= tod_end)]
                baseline_same_hours = df[
                    (df["ts"] < tod_start) &
                    (df["ts"].dt.hour.isin(tod_events["ts"].dt.hour.unique() if not tod_events.empty else []))
                ]
                baseline_daily = len(baseline_same_hours) / max(total_days - 1, 1)

                interpretation = (
                    "SILENCE_DURING_TOD" if tod_events.empty and baseline_daily > 1
                    else "ELEVATED_ACTIVITY_DURING_TOD" if len(tod_events) > baseline_daily * 2
                    else "NORMAL"
                )
                tod_delta = {
                    "tod_event_count": len(tod_events),
                    "baseline_daily_avg": round(baseline_daily, 2),
                    "interpretation": interpretation,
                }
            except Exception as e:
                logger.warning(f"TOD delta computation failed: {e}")

        # ─── 6. Tower Sequence ───
        tower_result = build_tower_sequence(df)

        # ─── 7. IMEI Anomalies ───
        imei_anomalies = detect_imei_anomalies(df)

        # ─── 8. Forensic Flags ───
        forensic_flags = []
        if any(s["severity"] == "HIGH" for s in silences):
            forensic_flags.append("SILENCE_WINDOW_DURING_TOD")
        if unknown_near_tod:
            forensic_flags.append(f"UNKNOWN_CONTACTS_NEAR_TOD:{len(unknown_near_tod)}")
        if imei_anomalies:
            forensic_flags.append("IMEI_ANOMALY_DETECTED")
        if tower_result["anomalous_jumps"]:
            forensic_flags.append("SUSPICIOUS_TOWER_JUMP")
        if escalations:
            forensic_flags.append(f"CONTACT_ESCALATION:{len(escalations)}")

        await self.log_step(
            "STATISTICAL_ANALYSIS",
            "CDR Full Analysis Complete",
            f"Silences: {len(silences)}, Contacts: {len(contacts)} ({len(unknown_near_tod)} unknown), "
            f"Escalations: {len(escalations)}, Tower anomalies: {len(tower_result['anomalous_jumps'])}, "
            f"IMEI anomalies: {len(imei_anomalies)}. TOD delta: {tod_delta['interpretation']}",
            confidence=0.92,
        )

        return {
            "baseline": baseline,
            "silence_windows": sorted(silences, key=lambda x: x["z_score"], reverse=True),
            "contacts": contacts,
            "unknown_contacts_near_tod": unknown_near_tod,
            "escalations": escalations,
            "tod_behavior_delta": tod_delta,
            "tower_sequence": tower_result,
            "imei_anomalies": imei_anomalies,
            "forensic_flags": forensic_flags,
            "_confidence": 0.92,
        }
