"""
EVIDRA — Gap & Logic Auditor (Tier 6).

Implements CANONICAL_04 spec:
- Orphan claim detection (claims with no evidence links)
- Weakly supported hypothesis detection
- Unresolved contradiction detection
- Unused evidence detection
- Coverage statistics
"""
import json
import logging
from uuid import UUID
from agents.base import BaseAgent
from core.database import db

logger = logging.getLogger("evidra.gap_auditor")


class GapAuditor(BaseAgent):
    agent_id = "gap_auditor"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Scan the argument graph for structural weaknesses and gaps."""

        findings = []

        # 1. Fetch all data
        claims = await db.fetch("SELECT * FROM claims WHERE case_id=$1", case_id)
        relations = await db.fetch("SELECT * FROM claim_relations WHERE case_id=$1", case_id)
        hypotheses = await db.fetch(
            "SELECT * FROM hypothesis_history WHERE pipeline_run_id=$1",
            pipeline_run_id,
        )
        case_files = await db.fetch("SELECT * FROM case_files WHERE case_id=$1", case_id)
        agent_results = await db.fetch(
            "SELECT agent_id FROM agent_results WHERE pipeline_run_id=$1",
            pipeline_run_id,
        )

        claims_list = [dict(c) for c in claims] if claims else []
        relations_list = [dict(r) for r in relations] if relations else []
        hyp_list = [dict(h) for h in hypotheses] if hypotheses else []
        files_list = [dict(f) for f in case_files] if case_files else []
        processed_agents = {r["agent_id"] for r in agent_results} if agent_results else set()

        # ─── 1. Orphan Claims (no evidence linking to or from them) ───
        linked_claims = set()
        for r in relations_list:
            linked_claims.add(str(r.get("from_claim_id", "")))
            linked_claims.add(str(r.get("to_claim_id", "")))

        for claim in claims_list:
            cid = str(claim["claim_id"])
            if cid not in linked_claims:
                findings.append({
                    "type": "ORPHAN_CLAIM",
                    "description": f"Claim '{claim['text'][:80]}' has no supporting or refuting evidence links",
                    "target": "CLAIM",
                    "target_ref_id": cid,
                    "severity": "WARN",
                    "recommended_action": "Cross-reference this claim with additional evidence sources",
                })

        # ─── 2. Weakly Supported Hypotheses ───
        for hyp in hyp_list:
            prob = float(hyp.get("probability", 0))
            key = hyp.get("hypothesis_key", "")
            evidence_summary = hyp.get("evidence_summary", "[]")

            try:
                support_items = json.loads(evidence_summary) if isinstance(evidence_summary, str) else evidence_summary
            except (json.JSONDecodeError, TypeError):
                support_items = []

            support_count = len(support_items) if isinstance(support_items, list) else 0

            if support_count < 2 and prob > 0.30:
                findings.append({
                    "type": "WEAK_SUPPORT",
                    "description": f"Hypothesis '{key}' at {prob:.0%} confidence relies on <2 evidence paths ({support_count} found)",
                    "target": "HYPOTHESIS",
                    "target_ref_id": key,
                    "severity": "CRITICAL",
                    "recommended_action": f"Collect additional evidence to strengthen or refute {key} hypothesis",
                })

        # ─── 3. Unresolved Contradictions ───
        contradictions = [r for r in relations_list if r.get("relation") == "CONTRADICTS"]
        for c in contradictions:
            from_claim = next((cl for cl in claims_list if str(cl["claim_id"]) == str(c.get("from_claim_id"))), None)
            to_claim = next((cl for cl in claims_list if str(cl["claim_id"]) == str(c.get("to_claim_id"))), None)

            from_text = from_claim["text"][:60] if from_claim else "Unknown"
            to_text = to_claim["text"][:60] if to_claim else "Unknown"

            findings.append({
                "type": "CONTRADICTION_UNRESOLVED",
                "description": f"Conflicting claims: '{from_text}' vs '{to_text}'",
                "target": "CLAIM",
                "target_ref_id": str(c.get("from_claim_id", "")),
                "severity": "HIGH",
                "recommended_action": "Investigate the source of contradiction and gather disambiguating evidence",
            })

        # ─── 4. Unused Evidence Files ───
        # Files that were uploaded but may not have been analyzed
        for f in files_list:
            doc_type = f.get("doc_type", "")
            status = f.get("status", "")

            if status != "PROCESSED":
                findings.append({
                    "type": "MISSING_EVIDENCE",
                    "description": f"File '{f.get('original_name', 'unknown')}' ({doc_type}) was uploaded but not fully processed",
                    "target": "EVIDENCE",
                    "target_ref_id": str(f.get("file_id", "")),
                    "severity": "WARN",
                    "recommended_action": f"Ensure the {doc_type} file is processed by the appropriate agent",
                })

        # ─── 5. Missing Agent Coverage ───
        expected_agents = {"evidence_parser", "format_normalizer", "autopsy_agent", "cdr_analyzer",
                           "financial_analyzer", "tod_agent", "anomaly_detector", "hotspot_engine",
                           "claim_extractor", "evidence_claim_mapper", "hypothesis_manager"}

        missing_agents = expected_agents - processed_agents
        for agent in missing_agents:
            findings.append({
                "type": "MISSING_ANALYSIS",
                "description": f"Agent '{agent}' did not produce results for this pipeline run",
                "target": "AGENT",
                "target_ref_id": agent,
                "severity": "WARN" if agent not in ("hypothesis_manager", "tod_agent") else "CRITICAL",
                "recommended_action": f"Check if {agent} was skipped due to missing input data",
            })

        # ─── Coverage Statistics ───
        coverage_stats = {
            "total_claims": len(claims_list),
            "claims_with_evidence": len(linked_claims),
            "claims_without_evidence": len(claims_list) - len(linked_claims & {str(c["claim_id"]) for c in claims_list}),
            "hypotheses_with_strong_support": sum(1 for h in hyp_list if float(h.get("probability", 0)) > 0.3),
            "contradiction_count": len(contradictions),
            "evidence_utilization_pct": round(
                sum(1 for f in files_list if f.get("status") == "PROCESSED") / max(len(files_list), 1) * 100, 1
            ),
            "total_findings": len(findings),
            "critical_findings": sum(1 for f in findings if f["severity"] == "CRITICAL"),
        }

        await self.log_step(
            "CONSISTENCY_CHECK",
            "Gap & Logic Audit",
            f"Found {len(findings)} findings ({coverage_stats['critical_findings']} critical). "
            f"Coverage: {coverage_stats['evidence_utilization_pct']}%",
            confidence=0.90,
        )

        return {
            "findings": findings,
            "coverage_stats": coverage_stats,
            "_confidence": 0.90,
        }
