"""
EVIDRA — Bias & Uncertainty Assessor (Tier 6).

Implements Bias & Uncertainty Monitor spec:
- Rule-based bias detection (not LLM-delegated)
- Confirmation bias detection (single-source dominance)
- Missing evidence detection
- Overconfidence detection
- Contradiction-based uncertainty scoring
"""
import json
import logging
from uuid import UUID
from agents.base import BaseAgent
from core.database import db

logger = logging.getLogger("evidra.bias")


def detect_biases(
    claims: list[dict],
    relations: list[dict],
    hypotheses: list[dict],
    agent_results: list[dict],
) -> list[dict]:
    """Rule-based bias detection engine."""
    flags = []

    # ─── 1. Single-Source Dominance ───
    source_counts = {}
    for claim in claims:
        src = claim.get("source_agent", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    total_claims = len(claims) or 1
    for src, count in source_counts.items():
        pct = count / total_claims
        if pct > 0.60 and total_claims >= 3:
            flags.append({
                "type": "SOURCE_BIAS",
                "description": f"Agent '{src}' accounts for {pct:.0%} of all claims — risk of single-source dominance",
                "severity": "MEDIUM",
                "remediation": f"Collect additional evidence types to reduce dependency on {src}",
            })

    # ─── 2. Confirmation Bias (all claims support one hypothesis) ───
    if hypotheses:
        top_hyp = max(hypotheses, key=lambda h: float(h.get("probability", 0)))
        top_prob = float(top_hyp.get("probability", 0))

        if top_prob > 0.75:
            contradictions = [r for r in relations if r.get("relation") == "CONTRADICTS"]
            if len(contradictions) == 0:
                flags.append({
                    "type": "CONFIRMATION_BIAS",
                    "description": f"Leading hypothesis '{top_hyp.get('hypothesis_key')}' at {top_prob:.0%} with ZERO contradictions — possible tunnel vision",
                    "severity": "HIGH",
                    "remediation": "Actively seek disconfirming evidence for the leading hypothesis",
                })

    # ─── 3. Overconfidence ───
    if hypotheses:
        top_prob = max(float(h.get("probability", 0)) for h in hypotheses)
        if top_prob > 0.85 and total_claims < 5:
            flags.append({
                "type": "OVERCONFIDENCE",
                "description": f"Primary hypothesis confidence ({top_prob:.0%}) is very high relative to limited evidence ({total_claims} claims)",
                "severity": "HIGH",
                "remediation": "Consider whether additional evidence would significantly alter the probability distribution",
            })

    # ─── 4. Missing Evidence Types ───
    completed_agents = {r.get("agent_id", "") for r in agent_results}
    expected_domain = {"autopsy_agent", "cdr_analyzer", "financial_analyzer"}
    missing = expected_domain - completed_agents

    for agent in missing:
        flags.append({
            "type": "MISSING_EVIDENCE",
            "description": f"Domain agent '{agent}' did not produce results — evidence may be incomplete",
            "severity": "MEDIUM",
            "remediation": f"Upload {agent.replace('_', ' ')} data to enable analysis",
        })

    # ─── 5. Unaddressed Contradictions ───
    contradictions = [r for r in relations if r.get("relation") == "CONTRADICTS"]
    if len(contradictions) >= 3:
        flags.append({
            "type": "HIGH_CONTRADICTION_COUNT",
            "description": f"{len(contradictions)} contradictions detected between claims — high internal inconsistency",
            "severity": "HIGH",
            "remediation": "Prioritize resolving contradictions before finalizing hypothesis",
        })

    # ─── 6. Low claim count ───
    if total_claims < 3:
        flags.append({
            "type": "INSUFFICIENT_EVIDENCE",
            "description": f"Only {total_claims} claims extracted — analysis may be premature",
            "severity": "MEDIUM",
            "remediation": "Upload additional evidence or re-run extraction with more detail",
        })

    return flags


def compute_uncertainty_score(
    flags: list[dict],
    contradiction_count: int,
    claim_count: int,
) -> float:
    """Compute overall uncertainty score (0=certain, 1=totally uncertain)."""
    base = 0.20  # Minimum uncertainty for any forensic case

    # Bias flag severity contributions
    severity_weights = {"CRITICAL": 0.15, "HIGH": 0.10, "MEDIUM": 0.05, "LOW": 0.02}
    for flag in flags:
        base += severity_weights.get(flag["severity"], 0.03)

    # Contradiction contribution
    base += min(0.20, contradiction_count * 0.05)

    # Low evidence contribution
    if claim_count < 3:
        base += 0.15
    elif claim_count < 5:
        base += 0.05

    return round(min(1.0, base), 3)


class BiasUncertaintyAgent(BaseAgent):
    agent_id = "bias_uncertainty"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Assess systemic bias and missing data using rule-based checks."""

        # Fetch data
        claims = await db.fetch("SELECT * FROM claims WHERE case_id=$1", case_id)
        relations = await db.fetch("SELECT * FROM claim_relations WHERE case_id=$1", case_id)
        hypotheses = await db.fetch(
            "SELECT * FROM hypothesis_history WHERE pipeline_run_id=$1",
            pipeline_run_id,
        )
        agent_results = await db.fetch(
            "SELECT agent_id FROM agent_results WHERE pipeline_run_id=$1",
            pipeline_run_id,
        )

        claims_list = [dict(c) for c in claims] if claims else []
        relations_list = [dict(r) for r in relations] if relations else []
        hyp_list = [dict(h) for h in hypotheses] if hypotheses else []
        agent_list = [dict(a) for a in agent_results] if agent_results else []

        # Detect biases (rule-based)
        bias_flags = detect_biases(claims_list, relations_list, hyp_list, agent_list)

        # Compute overall uncertainty
        contradiction_count = sum(1 for r in relations_list if r.get("relation") == "CONTRADICTS")
        uncertainty_score = compute_uncertainty_score(bias_flags, contradiction_count, len(claims_list))

        # Save to DB
        await db.execute(
            """
            INSERT INTO uncertainty_reports (case_id, pipeline_run_id, bias_flags, overall_score)
            VALUES ($1, $2, $3, $4)
            """,
            case_id, pipeline_run_id,
            json.dumps(bias_flags, default=str),
            uncertainty_score,
        )

        await self.log_step(
            "CONSISTENCY_CHECK",
            "Bias & Uncertainty Assessment",
            f"Detected {len(bias_flags)} bias flags. "
            f"Overall uncertainty: {uncertainty_score:.0%}. "
            f"Types: {[f['type'] for f in bias_flags]}",
            confidence=0.90,
        )

        return {
            "bias_flags": bias_flags,
            "overall_uncertainty_score": uncertainty_score,
            "contradiction_count": contradiction_count,
            "claim_count": len(claims_list),
            "_confidence": 0.90,
        }
