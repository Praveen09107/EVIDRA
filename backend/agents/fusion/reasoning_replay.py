"""
EVIDRA — Reasoning Replay Compiler (Tier 7).

Implements spec §5.10 and ML Spec §10:
- Step-level confidence model (per-agent reliability × input quality)
- Case-level harmonic confidence aggregation
- SHA-256 step hashing for integrity
- LLM narrative synthesis
- Court-ready structured audit log
"""
import json
import hashlib
import logging
import numpy as np
from uuid import UUID
from datetime import datetime
from agents.base import BaseAgent
from core.database import db
from core.llm_gateway import llm

logger = logging.getLogger("evidra.replay")

# ═══════════════════════════════════════════════════════════
# ML-10: STEP-LEVEL CONFIDENCE MODEL (spec §10.1)
# ═══════════════════════════════════════════════════════════

BASE_RELIABILITY = {
    "evidence_parser":       0.95,
    "ocr":                   0.80,
    "format_normalizer":     0.90,
    "autopsy_agent":         0.88,
    "cdr_analyzer":          0.93,
    "financial_analyzer":    0.85,
    "tod_agent":             0.82,
    "anomaly_detector":      0.87,
    "hotspot_engine":        0.79,
    "claim_extractor":       0.84,
    "evidence_claim_mapper": 0.82,
    "hypothesis_manager":    0.84,
    "bias_uncertainty":      0.80,
    "graph_builder":         0.88,
    "gap_auditor":           0.90,
    "nbe_agent":             0.78,
    "reasoning_replay":      0.95,
}

WARNING_PENALTIES = {
    "MISSING_DATA":          0.08,
    "LOW_OCR_CONFIDENCE":    0.10,
    "INCONSISTENT_SIGNAL":   0.15,
    "SINGLE_SOURCE":         0.05,
    "MODEL_EXTRAPOLATION":   0.07,
    "COD_INJURY_MISMATCH":   0.10,
    "MANNER_DEFENSIVE":      0.12,
    "RIGOR_LIVOR":           0.06,
    "DECOMP_RIGOR":          0.10,
}


def compute_step_confidence(
    agent_id: str,
    raw_confidence: float,
    source_count: int,
    warnings: list[str],
) -> float:
    """Rule-based confidence scoring for each Replay step."""
    base = BASE_RELIABILITY.get(agent_id, 0.75)
    score = base * max(raw_confidence, 0.1)

    # Boost for multiple corroborating sources
    source_boost = min(0.10, (source_count - 1) * 0.03)
    score += source_boost

    # Warning penalties
    for warning in (warnings or []):
        warning_upper = warning.upper()
        for key, penalty in WARNING_PENALTIES.items():
            if key in warning_upper:
                score -= penalty
                break

    return round(max(0.10, min(0.99, score)), 3)


def compute_overall_case_confidence(
    step_confidences: list[float],
    contradiction_count: int,
    gap_count: int,
) -> float:
    """
    Aggregates all step confidences into a single case-level score.
    Uses harmonic mean to penalize weak links.
    """
    if not step_confidences:
        return 0.0

    weights = np.array(step_confidences)
    # Harmonic mean penalizes weak links heavily
    harmonic = len(weights) / np.sum(1.0 / np.maximum(weights, 0.01))

    # Contradiction and gap penalties
    contradiction_penalty = contradiction_count * 0.05
    gap_penalty = gap_count * 0.03

    final = max(0.0, min(1.0, harmonic - contradiction_penalty - gap_penalty))
    return round(float(final), 3)


# ═══════════════════════════════════════════════════════════
# SHA-256 STEP HASHING (spec §5.10)
# ═══════════════════════════════════════════════════════════

def hash_step(step_data: dict, prev_hash: str = "") -> str:
    """Compute SHA-256 hash of a step for integrity chain."""
    canonical = json.dumps(step_data, sort_keys=True, default=str)
    payload = f"{prev_hash}:{canonical}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════
# NARRATIVE PROMPT
# ═══════════════════════════════════════════════════════════

REPLAY_NARRATIVE_PROMPT = """You are a forensic case report writer.
Synthesize the following pipeline execution steps into a clear, professional forensic triage narrative.

Requirements:
1. Summarize what evidence was analyzed and key findings from each agent
2. Highlight contradictions or anomalies discovered
3. State the leading hypothesis with confidence level
4. Note any gaps or missing evidence
5. Keep under 500 words. Use passive voice. No names.

PIPELINE STEPS:
{steps_json}"""


class ReasoningReplay(BaseAgent):
    agent_id = "reasoning_replay"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Compile the final pipeline narrative with crypto integrity and confidence scoring."""

        # 1. Fetch all replay steps
        steps = await db.fetch(
            "SELECT agent_id, step_type, action, interpretation, confidence, warnings, timestamp "
            "FROM replay_steps WHERE pipeline_run_id=$1 ORDER BY timestamp ASC",
            pipeline_run_id,
        )

        if not steps:
            return {"status": "SKIPPED", "reason": "No replay steps found"}

        steps_list = [dict(s) for s in steps]

        # 2. Compute step-level adjusted confidences (ML-10)
        adjusted_steps = []
        prev_hash = ""
        step_confidences = []

        for s in steps_list:
            raw_conf = float(s.get("confidence", 0.5))
            warnings = s.get("warnings", []) or []

            # Count how many other agents reference this agent's output
            source_count = sum(
                1 for other in steps_list
                if other["agent_id"] != s["agent_id"]
            )

            adj_conf = compute_step_confidence(
                agent_id=s["agent_id"],
                raw_confidence=raw_conf,
                source_count=min(source_count, 5),
                warnings=warnings if isinstance(warnings, list) else [],
            )
            step_confidences.append(adj_conf)

            # Hash chain
            step_data = {
                "agent_id": s["agent_id"],
                "step_type": s["step_type"],
                "action": s["action"],
                "interpretation": s["interpretation"],
                "confidence": raw_conf,
                "adjusted_confidence": adj_conf,
                "timestamp": str(s.get("timestamp", "")),
            }
            step_hash = hash_step(step_data, prev_hash)
            prev_hash = step_hash

            adjusted_steps.append({
                **step_data,
                "step_hash": step_hash,
            })

        # 3. Get contradiction and gap counts
        hyp_res = await self.get_prior_result("hypothesis_manager")
        gap_res = await self.get_prior_result("gap_auditor")

        contradiction_count = len(hyp_res.get("contradictions", [])) if hyp_res else 0
        gap_count = gap_res.get("coverage_stats", {}).get("total_findings", 0) if gap_res else 0

        # 4. Compute overall case confidence (harmonic mean)
        overall_confidence = compute_overall_case_confidence(
            step_confidences, contradiction_count, gap_count,
        )

        # 5. Build structured audit log
        audit_log = {
            "pipeline_run_id": str(pipeline_run_id),
            "case_id": str(case_id),
            "compiled_at": datetime.utcnow().isoformat(),
            "total_steps": len(adjusted_steps),
            "overall_case_confidence": overall_confidence,
            "contradiction_count": contradiction_count,
            "gap_count": gap_count,
            "final_hash": prev_hash,
            "steps": adjusted_steps,
        }

        # 6. LLM Narrative synthesis
        narrative = ""
        try:
            steps_summary = json.dumps(
                [{
                    "agent": s["agent_id"],
                    "action": s["action"],
                    "result": s["interpretation"],
                    "confidence": s["adjusted_confidence"],
                } for s in adjusted_steps],
                default=str,
            )

            resp = await llm.complete(
                task="replay_narrative",
                prompt=REPLAY_NARRATIVE_PROMPT.format(steps_json=steps_summary[:6000]),
                system_prompt="You are a forensic report writer.",
            )
            narrative = resp.text
        except Exception as e:
            logger.warning(f"Narrative generation failed: {e}")
            narrative = f"Pipeline completed with {len(adjusted_steps)} steps. "
            narrative += f"Overall confidence: {overall_confidence:.0%}. "
            if hyp_res:
                narrative += f"Leading hypothesis: {hyp_res.get('primary_hypothesis', 'UNDETERMINED')}."

        # 7. Save report snapshot
        await db.execute(
            """
            INSERT INTO report_snapshots (case_id, pipeline_run_id, report_type, narrative)
            VALUES ($1, $2, 'FULL', $3)
            """,
            case_id, pipeline_run_id, narrative,
        )

        # 8. Save audit log
        await db.execute(
            """
            INSERT INTO report_snapshots (case_id, pipeline_run_id, report_type, narrative)
            VALUES ($1, $2, 'AUDIT_LOG', $3)
            """,
            case_id, pipeline_run_id, json.dumps(audit_log, default=str),
        )

        await self.log_step(
            "LLM_NARRATIVE",
            "Final Report Compiled",
            f"Aggregated {len(adjusted_steps)} steps. Overall confidence: {overall_confidence:.0%}. "
            f"Hash chain: {prev_hash[:16]}...",
            confidence=overall_confidence,
        )

        return {
            "total_steps": len(adjusted_steps),
            "overall_case_confidence": overall_confidence,
            "contradiction_count": contradiction_count,
            "gap_count": gap_count,
            "final_hash": prev_hash,
            "narrative_length": len(narrative),
            "_confidence": overall_confidence,
        }
