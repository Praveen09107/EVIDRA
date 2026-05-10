"""
Tests for: orchestrator/dag.py — DAG builder and dynamic pruning.
"""
import pytest
from orchestrator.dag import build_agent_plan, AGENT_REGISTRY


class TestDAGBuildFullEvidence:
    """Full evidence set → all agents active."""

    def test_full_evidence_activates_all(self):
        """All file types → maximum agent activation."""
        plan = build_agent_plan({"AUTOPSY_REPORT", "CDR", "FINANCIAL_RECORDS", "DEVICE_DATA", "CCTV"})
        # Core agents always present
        assert "evidence_parser" in plan
        assert "ocr" in plan
        assert "format_normalizer" in plan
        # Domain agents activated
        assert "autopsy_agent" in plan
        assert "cdr_analyzer" in plan
        assert "financial_analyzer" in plan
        assert "device_extractor" in plan
        assert "image_agent" in plan
        # ML agents propagated
        assert "tod_agent" in plan
        assert "anomaly_detector" in plan
        assert "hotspot_engine" in plan
        # Reasoning agents
        assert "hypothesis_manager" in plan
        assert "bias_uncertainty" in plan
        assert "reasoning_replay" in plan

    def test_full_plan_has_correct_tiers(self):
        plan = build_agent_plan({"AUTOPSY_REPORT", "CDR", "FINANCIAL_RECORDS"})
        for agent_id, config in plan.items():
            assert config["tier"] == AGENT_REGISTRY[agent_id]["tier"]


class TestDAGPruning:
    """Test dynamic pruning based on available evidence."""

    def test_no_autopsy_skips_tod(self):
        """Without autopsy report, TOD agent should not activate."""
        plan = build_agent_plan({"CDR", "FINANCIAL_RECORDS"})
        assert "autopsy_agent" not in plan
        assert "tod_agent" not in plan

    def test_no_cdr_skips_cdr_analyzer(self):
        plan = build_agent_plan({"AUTOPSY_REPORT", "FINANCIAL_RECORDS"})
        assert "cdr_analyzer" not in plan

    def test_no_financial_skips_financial_analyzer(self):
        plan = build_agent_plan({"AUTOPSY_REPORT", "CDR"})
        assert "financial_analyzer" not in plan

    def test_no_cctv_skips_image_agent(self):
        plan = build_agent_plan({"AUTOPSY_REPORT", "CDR"})
        assert "image_agent" not in plan

    def test_empty_evidence_keeps_core(self):
        """No files → only required (core) agents active."""
        plan = build_agent_plan(set())
        assert "evidence_parser" in plan
        assert "ocr" in plan
        assert "format_normalizer" in plan
        assert "autopsy_agent" not in plan
        assert "cdr_analyzer" not in plan

    def test_cdr_only_activates_anomaly(self):
        """CDR alone should activate anomaly_detector via propagation."""
        plan = build_agent_plan({"CDR"})
        assert "cdr_analyzer" in plan
        assert "anomaly_detector" in plan


class TestDAGDependencies:
    """Test dependency pruning in the final plan."""

    def test_pruned_dependencies_are_in_plan(self):
        """No dependency should reference an agent outside the plan."""
        plan = build_agent_plan({"AUTOPSY_REPORT", "CDR"})
        for agent_id, config in plan.items():
            for dep in config["depends_on"]:
                assert dep in plan, f"Agent '{agent_id}' depends on '{dep}' which is not in the plan"

    def test_tier_0_has_no_dependencies(self):
        plan = build_agent_plan({"AUTOPSY_REPORT", "CDR", "FINANCIAL_RECORDS"})
        for agent_id, config in plan.items():
            if config["tier"] == 0:
                assert config["depends_on"] == [], f"Tier 0 agent '{agent_id}' should have no dependencies"

    def test_topological_order(self):
        """Dependencies must be in same or lower tiers."""
        plan = build_agent_plan({"AUTOPSY_REPORT", "CDR", "FINANCIAL_RECORDS"})
        for agent_id, config in plan.items():
            for dep in config["depends_on"]:
                assert plan[dep]["tier"] <= config["tier"], \
                    f"Agent '{agent_id}' (tier {config['tier']}) depends on '{dep}' (tier {plan[dep]['tier']})"


class TestRegistryCompleteness:
    """Test the AGENT_REGISTRY constant itself."""

    def test_total_agent_count(self):
        assert len(AGENT_REGISTRY) >= 17, "Should have at least 17 registered agents"

    def test_all_tiers_represented(self):
        tiers = set(v["tier"] for v in AGENT_REGISTRY.values())
        for t in range(8):
            assert t in tiers, f"Tier {t} has no agents"

    def test_all_agents_have_required_fields(self):
        for agent_id, config in AGENT_REGISTRY.items():
            assert "tier" in config, f"Agent '{agent_id}' missing 'tier'"
            assert "depends_on" in config, f"Agent '{agent_id}' missing 'depends_on'"
            assert "required" in config, f"Agent '{agent_id}' missing 'required'"
