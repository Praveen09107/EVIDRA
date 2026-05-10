"""
Tests for: agents/fusion/bias_uncertainty.py — Bias detection rules and uncertainty scoring.
"""
import pytest
from agents.fusion.bias_uncertainty import detect_biases, compute_uncertainty_score


class TestBiasDetection:
    """Test rule-based bias detection engine."""

    def test_source_bias_detected(self):
        """Single source > 60% of claims → SOURCE_BIAS flag."""
        claims = [
            {"source_agent": "autopsy_agent"},
            {"source_agent": "autopsy_agent"},
            {"source_agent": "autopsy_agent"},
            {"source_agent": "autopsy_agent"},
            {"source_agent": "cdr_analyzer"},
        ]
        flags = detect_biases(claims, [], [], [])
        types = [f["type"] for f in flags]
        assert "SOURCE_BIAS" in types

    def test_no_source_bias_when_balanced(self):
        """Evenly distributed claims → no SOURCE_BIAS."""
        claims = [
            {"source_agent": "autopsy_agent"},
            {"source_agent": "cdr_analyzer"},
            {"source_agent": "financial_analyzer"},
        ]
        flags = detect_biases(claims, [], [], [])
        types = [f["type"] for f in flags]
        assert "SOURCE_BIAS" not in types

    def test_confirmation_bias_detected(self):
        """High confidence + zero contradictions → CONFIRMATION_BIAS."""
        hypotheses = [{"hypothesis_key": "HOMICIDE", "probability": 0.85}]
        relations = []  # No contradictions
        flags = detect_biases([], relations, hypotheses, [])
        types = [f["type"] for f in flags]
        assert "CONFIRMATION_BIAS" in types

    def test_no_confirmation_bias_with_contradictions(self):
        """High confidence + contradictions → no CONFIRMATION_BIAS."""
        hypotheses = [{"hypothesis_key": "HOMICIDE", "probability": 0.85}]
        relations = [{"relation": "CONTRADICTS"}]
        flags = detect_biases([], relations, hypotheses, [])
        types = [f["type"] for f in flags]
        assert "CONFIRMATION_BIAS" not in types

    def test_overconfidence_detected(self):
        """High probability + few claims → OVERCONFIDENCE."""
        hypotheses = [{"hypothesis_key": "HOMICIDE", "probability": 0.90}]
        claims = [{"source_agent": "a"}, {"source_agent": "b"}]  # 2 claims < 5
        flags = detect_biases(claims, [], hypotheses, [])
        types = [f["type"] for f in flags]
        assert "OVERCONFIDENCE" in types

    def test_no_overconfidence_with_enough_claims(self):
        """High probability + enough claims → no OVERCONFIDENCE."""
        hypotheses = [{"hypothesis_key": "HOMICIDE", "probability": 0.90}]
        claims = [{"source_agent": f"a{i}"} for i in range(10)]
        flags = detect_biases(claims, [], hypotheses, [])
        types = [f["type"] for f in flags]
        assert "OVERCONFIDENCE" not in types

    def test_missing_evidence_detected(self):
        """Missing domain agents → MISSING_EVIDENCE flags."""
        agent_results = [{"agent_id": "autopsy_agent"}]  # missing cdr + financial
        flags = detect_biases([], [], [], agent_results)
        types = [f["type"] for f in flags]
        assert "MISSING_EVIDENCE" in types
        missing_descs = [f["description"] for f in flags if f["type"] == "MISSING_EVIDENCE"]
        assert any("cdr_analyzer" in d for d in missing_descs)
        assert any("financial_analyzer" in d for d in missing_descs)

    def test_no_missing_when_all_agents_present(self):
        """All domain agents present → no MISSING_EVIDENCE."""
        agent_results = [
            {"agent_id": "autopsy_agent"},
            {"agent_id": "cdr_analyzer"},
            {"agent_id": "financial_analyzer"},
        ]
        flags = detect_biases([], [], [], agent_results)
        types = [f["type"] for f in flags]
        assert "MISSING_EVIDENCE" not in types

    def test_high_contradiction_count(self):
        """3+ contradictions → HIGH_CONTRADICTION_COUNT."""
        relations = [{"relation": "CONTRADICTS"} for _ in range(4)]
        flags = detect_biases([], relations, [], [])
        types = [f["type"] for f in flags]
        assert "HIGH_CONTRADICTION_COUNT" in types

    def test_insufficient_evidence(self):
        """< 3 claims → INSUFFICIENT_EVIDENCE."""
        claims = [{"source_agent": "a"}]
        flags = detect_biases(claims, [], [], [])
        types = [f["type"] for f in flags]
        assert "INSUFFICIENT_EVIDENCE" in types

    def test_empty_inputs(self):
        """All empty → should produce INSUFFICIENT_EVIDENCE at minimum."""
        flags = detect_biases([], [], [], [])
        types = [f["type"] for f in flags]
        assert "INSUFFICIENT_EVIDENCE" in types


class TestUncertaintyScore:
    """Test the uncertainty scoring function."""

    def test_baseline_minimum(self):
        """No flags, no contradictions, many claims → baseline 0.20."""
        score = compute_uncertainty_score([], 0, 10)
        assert score == 0.20

    def test_increases_with_high_severity_flags(self):
        """HIGH severity flags → score increases."""
        flags = [{"severity": "HIGH"}, {"severity": "HIGH"}]
        score = compute_uncertainty_score(flags, 0, 10)
        assert score > 0.20

    def test_increases_with_contradictions(self):
        """More contradictions → higher uncertainty."""
        score_0 = compute_uncertainty_score([], 0, 10)
        score_3 = compute_uncertainty_score([], 3, 10)
        assert score_3 > score_0

    def test_increases_with_low_claims(self):
        """< 3 claims → higher uncertainty."""
        score_few = compute_uncertainty_score([], 0, 2)
        score_many = compute_uncertainty_score([], 0, 10)
        assert score_few > score_many

    def test_capped_at_1(self):
        """Score should never exceed 1.0."""
        flags = [{"severity": "CRITICAL"} for _ in range(20)]
        score = compute_uncertainty_score(flags, 10, 1)
        assert score <= 1.0

    def test_never_negative(self):
        """Score should never be negative."""
        score = compute_uncertainty_score([], 0, 100)
        assert score >= 0

    def test_severity_ordering(self):
        """CRITICAL > HIGH > MEDIUM > LOW contribution."""
        s_crit = compute_uncertainty_score([{"severity": "CRITICAL"}], 0, 10)
        s_high = compute_uncertainty_score([{"severity": "HIGH"}], 0, 10)
        s_med = compute_uncertainty_score([{"severity": "MEDIUM"}], 0, 10)
        s_low = compute_uncertainty_score([{"severity": "LOW"}], 0, 10)
        assert s_crit > s_high > s_med > s_low
