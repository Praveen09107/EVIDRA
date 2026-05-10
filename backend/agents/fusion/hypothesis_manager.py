"""
EVIDRA — Hypothesis Manager (Tier 6).

Implements ML Spec §6: Bayesian Scoring Engine.
Uses deterministic EVIDENCE_WEIGHTS for reproducible, court-admissible scoring.
Never delegates probability computation to an LLM.
"""
import json
import numpy as np
from uuid import UUID
from agents.base import BaseAgent
from core.database import db
from core.llm_gateway import llm

# ═══════════════════════════════════════════════════════════
# EVIDENCE → HYPOTHESIS weight table (from spec §6.1)
# Additive in log-space. Positive = supports, Negative = weakens.
# ═══════════════════════════════════════════════════════════

HYPOTHESES = ["HOMICIDE", "SUICIDE", "ACCIDENT", "NATURAL", "UNDETERMINED"]

EVIDENCE_WEIGHTS = {
    "defensive_wounds_present": {
        "HOMICIDE": +0.40, "SUICIDE": -0.30, "ACCIDENT": -0.20, "NATURAL": -0.30
    },
    "manner_of_death_homicide": {
        "HOMICIDE": +0.40, "SUICIDE": -0.30, "ACCIDENT": -0.10, "NATURAL": -0.20
    },
    "manner_of_death_suicide": {
        "HOMICIDE": -0.20, "SUICIDE": +0.40, "ACCIDENT": -0.10, "NATURAL": -0.10
    },
    "manner_of_death_natural": {
        "HOMICIDE": -0.25, "SUICIDE": -0.15, "ACCIDENT": -0.15, "NATURAL": +0.35
    },
    "lethal_toxicology": {
        "HOMICIDE": +0.10, "SUICIDE": +0.20, "ACCIDENT": +0.05, "NATURAL": +0.05
    },
    "silence_during_tod": {
        "HOMICIDE": +0.20, "SUICIDE": +0.10, "ACCIDENT": +0.02, "NATURAL": -0.05
    },
    "unknown_contact_near_tod": {
        "HOMICIDE": +0.25, "SUICIDE": -0.10, "ACCIDENT": +0.02, "NATURAL": -0.05
    },
    "large_financial_txn_near_tod": {
        "HOMICIDE": +0.15, "SUICIDE": +0.10, "ACCIDENT": +0.02, "NATURAL": -0.05
    },
    "critical_hotspot": {
        "HOMICIDE": +0.20, "SUICIDE": +0.05, "ACCIDENT": +0.05, "NATURAL": 0.0
    },
    "no_injuries": {
        "HOMICIDE": -0.20, "SUICIDE": -0.05, "ACCIDENT": -0.10, "NATURAL": +0.15
    },
    "blunt_force_trauma": {
        "HOMICIDE": +0.35, "ACCIDENT": +0.10, "SUICIDE": -0.20, "NATURAL": -0.30
    },
    "sharp_force_trauma": {
        "HOMICIDE": +0.25, "SUICIDE": +0.20, "ACCIDENT": +0.05, "NATURAL": -0.30
    },
    "hesitation_wounds": {
        "SUICIDE": +0.45, "HOMICIDE": -0.20, "ACCIDENT": -0.15, "NATURAL": -0.20
    },
    "phone_silence_coincides_tod": {
        "HOMICIDE": +0.20, "SUICIDE": +0.10, "ACCIDENT": +0.02, "NATURAL": -0.05
    },
    "contact_proximity_tod": {
        "HOMICIDE": +0.25, "SUICIDE": -0.10, "ACCIDENT": +0.02, "NATURAL": -0.05
    },
    "large_cash_withdrawal": {
        "HOMICIDE": +0.15, "SUICIDE": +0.10, "ACCIDENT": +0.02, "NATURAL": -0.05
    },
    "natural_disease_history": {
        "NATURAL": +0.45, "HOMICIDE": -0.15, "SUICIDE": -0.05, "ACCIDENT": -0.10
    },
    "no_suicide_note": {
        "HOMICIDE": +0.05, "SUICIDE": -0.10, "ACCIDENT": +0.02, "NATURAL": +0.02
    },
    "strangulation_signs": {
        "HOMICIDE": +0.40, "SUICIDE": +0.10, "ACCIDENT": -0.15, "NATURAL": -0.30
    },
    "firearm_injuries": {
        "HOMICIDE": +0.30, "SUICIDE": +0.25, "ACCIDENT": +0.05, "NATURAL": -0.30
    },
    "financial_motive_detected": {
        "HOMICIDE": +0.25, "SUICIDE": +0.05, "ACCIDENT": 0.0, "NATURAL": -0.10
    },
    "anomalous_tower_jump": {
        "HOMICIDE": +0.15, "SUICIDE": 0.0, "ACCIDENT": +0.05, "NATURAL": 0.0
    },
    "imei_anomaly": {
        "HOMICIDE": +0.20, "SUICIDE": 0.0, "ACCIDENT": 0.0, "NATURAL": 0.0
    },
}


def compute_hypothesis_scores(
    evidence_flags: list[str],
    prior_scores: dict | None = None
) -> dict:
    """
    Bayesian-style evidence accumulation over hypotheses.
    Starts from uniform prior and updates additively in log-space
    for each evidence item. Fully deterministic and reproducible.
    """
    # Uniform prior (or given)
    if prior_scores:
        log_scores = {
            h: np.log(max(prior_scores.get(h, 0.2), 1e-10))
            for h in HYPOTHESES
        }
    else:
        log_scores = {h: np.log(0.2) for h in HYPOTHESES}

    # Track which evidence was applied
    applied_evidence = []

    for evidence in evidence_flags:
        weights = EVIDENCE_WEIGHTS.get(evidence)
        if weights:
            applied_evidence.append(evidence)
            for h in HYPOTHESES:
                delta = weights.get(h, 0.0)
                log_scores[h] += delta

    # Softmax normalization to probabilities
    max_log = max(log_scores.values())
    raw_scores = {h: np.exp(log_scores[h] - max_log) for h in HYPOTHESES}
    total = sum(raw_scores.values())
    scores = {h: round(raw_scores[h] / total, 4) for h in HYPOTHESES}

    primary = max(scores, key=scores.get)
    return {
        "scores": scores,
        "primary_hypothesis": primary,
        "primary_confidence": scores[primary],
        "evidence_applied": applied_evidence,
    }


def detect_contradictions(autopsy: dict, cdr: dict, financial: dict) -> list[str]:
    """Detect logical contradictions between evidence sources."""
    contradictions = []

    manner = autopsy.get("manner_of_death")
    defensive = autopsy.get("defensive_wounds")
    hesitation = autopsy.get("hesitation_wounds")

    if manner == "SUICIDE" and defensive:
        contradictions.append("PATHOLOGIST_MANNER_VS_DEFENSIVE_WOUNDS")
    if manner == "HOMICIDE" and hesitation:
        contradictions.append("HOMICIDE_MANNER_VS_HESITATION_WOUNDS")
    if manner == "NATURAL" and autopsy.get("injuries_present"):
        contradictions.append("NATURAL_MANNER_VS_INJURIES_PRESENT")

    # CDR silence + financial activity = suspicious
    cdr_flags = cdr.get("forensic_flags", [])
    fin_flags = financial.get("forensic_flags", [])
    if "SILENCE_WINDOW_DURING_TOD" in cdr_flags and "LARGE_TRANSACTION_NEAR_TOD" in fin_flags:
        contradictions.append("CDR_SILENCE_BUT_FINANCIAL_ACTIVITY_NEAR_TOD")

    return contradictions


def extract_evidence_signals(autopsy: dict, cdr: dict, financial: dict, hotspots: dict) -> list[str]:
    """Map raw agent outputs to canonical evidence signal keys."""
    signals = []

    # Autopsy signals
    if autopsy.get("defensive_wounds"):
        signals.append("defensive_wounds_present")
    if autopsy.get("manner_of_death") == "HOMICIDE":
        signals.append("manner_of_death_homicide")
    if autopsy.get("manner_of_death") == "SUICIDE":
        signals.append("manner_of_death_suicide")
    if autopsy.get("manner_of_death") == "NATURAL":
        signals.append("manner_of_death_natural")
    if not autopsy.get("injuries_present", True):
        signals.append("no_injuries")
    if autopsy.get("sharp_force_injuries"):
        signals.append("sharp_force_trauma")
    if autopsy.get("blunt_force_injuries"):
        signals.append("blunt_force_trauma")
    if autopsy.get("hesitation_wounds"):
        signals.append("hesitation_wounds")
    if autopsy.get("strangulation_signs"):
        signals.append("strangulation_signs")
    if autopsy.get("firearm_injuries"):
        signals.append("firearm_injuries")

    # Toxicology
    tox = autopsy.get("toxicology", {})
    if isinstance(tox, dict):
        drugs = tox.get("drug_details", [])
        if any(d.get("significance") == "LETHAL" for d in drugs if isinstance(d, dict)):
            signals.append("lethal_toxicology")

    # CDR signals
    cdr_flags = cdr.get("forensic_flags", [])
    if "SILENCE_WINDOW_DURING_TOD" in cdr_flags:
        signals.append("silence_during_tod")
    if any("UNKNOWN_CONTACTS" in f for f in cdr_flags):
        signals.append("unknown_contact_near_tod")
    if "SUSPICIOUS_TOWER_JUMP" in cdr_flags:
        signals.append("anomalous_tower_jump")
    if "IMEI_ANOMALY_DETECTED" in cdr_flags:
        signals.append("imei_anomaly")

    # Financial signals
    fin_flags = financial.get("forensic_flags", [])
    if "LARGE_TRANSACTION_NEAR_TOD" in fin_flags:
        signals.append("large_financial_txn_near_tod")
    if financial.get("motive_score", 0) > 0.3:
        signals.append("financial_motive_detected")

    # Hotspot signals
    hs_list = hotspots.get("hotspots", [])
    if any(h.get("severity") in ("HIGH", "CRITICAL") for h in hs_list if isinstance(h, dict)):
        signals.append("critical_hotspot")

    return signals


# ═══════════════════════════════════════════════════════════
# RECOMMENDED INVESTIGATIVE ACTIONS (per hypothesis)
# ═══════════════════════════════════════════════════════════

RECOMMENDED_ACTIONS = {
    "HOMICIDE": [
        "Verify alibi of unknown contacts near TOD",
        "Request full CDR of unknown contact MSISDNs",
        "Analyze financial transfers to unknown counterparties",
        "Re-examine scene for additional physical evidence",
        "Request CCTV footage near last known tower location",
    ],
    "SUICIDE": [
        "Obtain mental health records if any",
        "Interview close contacts for behavioral changes",
        "Review all communications in 48h before TOD",
        "Check for suicide note or digital drafts",
    ],
    "ACCIDENT": [
        "Review scene photographs for environmental hazards",
        "Check toxicology for intoxicants",
        "Verify circumstances with witnesses",
    ],
    "NATURAL": [
        "Confirm pre-existing medical conditions",
        "Verify prescription medication compliance",
        "Rule out foul play via secondary autopsy opinion",
    ],
    "UNDETERMINED": [
        "Expedite toxicology report",
        "Request additional autopsy opinion",
        "Expand CDR analysis to 30-day window",
        "Map all towers near death location",
    ],
}

# ═══════════════════════════════════════════════════════════
# LLM NARRATIVE (only for human-readable summary — NOT scoring)
# ═══════════════════════════════════════════════════════════

NARRATIVE_PROMPT = """You are a senior forensic investigator.
Based on the following evidence summary, write a structured analytical narrative covering:
1. Recommended primary hypothesis (most probable cause/manner of death)
2. Supporting evidence for the primary hypothesis
3. Evidence that contradicts or weakens the primary hypothesis
4. Alternative hypotheses that cannot be ruled out
5. Recommended next investigative steps

Rules:
- Be analytical, not speculative
- Cite specific evidence (e.g. "defensive wounds present", "unknown contact 2h before TOD")
- Express uncertainty clearly
- Do not use victim/suspect names — refer to "the deceased" / "the subject"
- Limit to 300 words

EVIDENCE SUMMARY:
{evidence_json}"""


class HypothesisManager(BaseAgent):
    agent_id = "hypothesis_manager"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """
        Deterministic Bayesian hypothesis scoring.
        LLM is only used for the narrative summary — never for probability computation.
        """

        # 1. Fetch all upstream agent results
        autopsy_res = await self.get_prior_result("autopsy_agent") or {}
        cdr_res = await self.get_prior_result("cdr_analyzer") or {}
        fin_res = await self.get_prior_result("financial_analyzer") or {}
        hotspot_res = await self.get_prior_result("hotspot_engine") or {}

        autopsy_data = autopsy_res.get("pathology", autopsy_res)
        cdr_data = cdr_res
        fin_data = fin_res
        hotspot_data = hotspot_res

        # 2. Extract evidence signals from structured outputs
        signals = extract_evidence_signals(autopsy_data, cdr_data, fin_data, hotspot_data)

        await self.log_step(
            "RULE",
            "Evidence Signal Extraction",
            f"Extracted {len(signals)} evidence signals: {signals}",
            confidence=0.95,
        )

        # 3. Compute Bayesian scores (deterministic, reproducible)
        result = compute_hypothesis_scores(signals)
        scores = result["scores"]
        primary = result["primary_hypothesis"]

        await self.log_step(
            "HYPOTHESIS_SCORE",
            "Bayesian Evidence Accumulation",
            f"Scores: {json.dumps(scores)}. Primary: {primary} ({scores[primary]:.2%})",
            confidence=0.92,
        )

        # 4. Detect contradictions
        contradictions = detect_contradictions(autopsy_data, cdr_data, fin_data)

        if contradictions:
            await self.log_step(
                "CONSISTENCY_CHECK",
                "Contradiction Detection",
                f"Found {len(contradictions)} contradictions: {contradictions}",
                confidence=0.85,
            )

        # 5. Classify supporting vs weakening evidence
        supporting = [s for s in signals if EVIDENCE_WEIGHTS.get(s, {}).get(primary, 0) > 0]
        weakening = [s for s in signals if EVIDENCE_WEIGHTS.get(s, {}).get(primary, 0) < 0]

        # 6. Generate LLM narrative (for human readability only)
        evidence_summary = {
            "scores": scores,
            "primary_hypothesis": primary,
            "supporting_evidence": supporting,
            "weakening_evidence": weakening,
            "contradictions": contradictions,
        }

        narrative = ""
        try:
            resp = await llm.complete(
                task="hypothesis_reason",
                prompt=NARRATIVE_PROMPT.format(evidence_json=json.dumps(evidence_summary)),
                system_prompt="You are an analytical forensic intelligence writer.",
            )
            narrative = resp.text
        except Exception:
            narrative = f"Primary hypothesis: {primary} ({scores[primary]:.0%}). Based on {len(signals)} evidence signals."

        # 7. Save to DB
        for key, prob in scores.items():
            await db.execute(
                """
                INSERT INTO hypothesis_history (case_id, pipeline_run_id, hypothesis_key, probability, evidence_summary)
                VALUES ($1, $2, $3, $4, $5)
                """,
                case_id, pipeline_run_id, key, prob,
                json.dumps([s for s in signals if EVIDENCE_WEIGHTS.get(s, {}).get(key, 0) > 0]),
            )

        # 8. Get recommended actions
        actions = RECOMMENDED_ACTIONS.get(primary, RECOMMENDED_ACTIONS["UNDETERMINED"])

        await self.log_step(
            "HYPOTHESIS_SCORE",
            "Final Hypothesis Output",
            f"Leading: {primary} at {scores[primary]:.2%}. {len(contradictions)} contradictions.",
            confidence=0.92,
        )

        return {
            "scores": scores,
            "primary_hypothesis": primary,
            "primary_confidence": scores[primary],
            "evidence_applied": signals,
            "supporting_evidence": supporting,
            "weakening_evidence": weakening,
            "contradictions": contradictions,
            "recommended_actions": actions,
            "narrative": narrative,
            "_confidence": 0.92,
        }
