"""
Tests for: Evidence weight table completeness and mathematical properties.
"""
import pytest
from agents.fusion.hypothesis_manager import EVIDENCE_WEIGHTS, HYPOTHESES


class TestEvidenceWeightTable:
    """Validate the evidence weight table for mathematical correctness."""

    def test_all_weights_have_core_hypotheses(self):
        """Every weight entry must cover HOMICIDE, SUICIDE, ACCIDENT, NATURAL."""
        core = {"HOMICIDE", "SUICIDE", "ACCIDENT", "NATURAL"}
        for evidence, weights in EVIDENCE_WEIGHTS.items():
            covered = set(weights.keys())
            missing = core - covered
            assert not missing, f"Evidence '{evidence}' is missing weights for: {missing}"

    def test_weights_are_bounded(self):
        """All weight values should be in [-0.5, +0.5] (reasonable range)."""
        for evidence, weights in EVIDENCE_WEIGHTS.items():
            for hyp, w in weights.items():
                assert -0.5 <= w <= 0.5, f"Weight for {evidence}/{hyp} = {w} is out of bounds"

    def test_no_all_zero_evidence(self):
        """No evidence entry should have all-zero weights (useless signal)."""
        for evidence, weights in EVIDENCE_WEIGHTS.items():
            total = sum(abs(v) for v in weights.values())
            assert total > 0, f"Evidence '{evidence}' has all-zero weights"

    def test_minimum_evidence_count(self):
        """Should have at least 15 evidence types for a real forensic system."""
        assert len(EVIDENCE_WEIGHTS) >= 15

    def test_complementary_signals_exist(self):
        """Both pro-homicide and pro-suicide evidence types must exist."""
        has_homicide_signal = any(
            w.get("HOMICIDE", 0) > 0.3 for w in EVIDENCE_WEIGHTS.values()
        )
        has_suicide_signal = any(
            w.get("SUICIDE", 0) > 0.3 for w in EVIDENCE_WEIGHTS.values()
        )
        has_natural_signal = any(
            w.get("NATURAL", 0) > 0.3 for w in EVIDENCE_WEIGHTS.values()
        )
        assert has_homicide_signal, "No strong pro-homicide evidence"
        assert has_suicide_signal, "No strong pro-suicide evidence"
        assert has_natural_signal, "No strong pro-natural evidence"
