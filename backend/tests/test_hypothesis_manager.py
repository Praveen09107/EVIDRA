"""
Tests for: agents/fusion/hypothesis_manager.py — Bayesian scoring engine.
"""
import pytest
import numpy as np
from agents.fusion.hypothesis_manager import (
    compute_hypothesis_scores, detect_contradictions,
    HYPOTHESES, EVIDENCE_WEIGHTS,
)


class TestBayesianScoring:
    """Test the core Bayesian hypothesis scoring engine."""

    def test_uniform_prior_no_evidence(self):
        """No evidence → uniform distribution (each ~20%)."""
        result = compute_hypothesis_scores([])
        for h in HYPOTHESES:
            assert abs(result["scores"][h] - 0.2) < 0.01

    def test_probabilities_sum_to_one(self):
        """Probabilities must always sum to 1.0."""
        flags = ["defensive_wounds_present", "manner_of_death_homicide"]
        result = compute_hypothesis_scores(flags)
        total = sum(result["scores"].values())
        assert abs(total - 1.0) < 0.001

    def test_homicide_evidence_increases_homicide(self):
        """Pro-homicide evidence should push HOMICIDE above uniform 0.2."""
        flags = ["defensive_wounds_present", "manner_of_death_homicide", "blunt_force_trauma"]
        result = compute_hypothesis_scores(flags)
        assert result["scores"]["HOMICIDE"] > 0.4
        assert result["primary_hypothesis"] == "HOMICIDE"

    def test_suicide_evidence_increases_suicide(self):
        """Pro-suicide evidence should push SUICIDE up."""
        flags = ["hesitation_wounds", "manner_of_death_suicide"]
        result = compute_hypothesis_scores(flags)
        assert result["scores"]["SUICIDE"] > 0.3
        assert result["primary_hypothesis"] == "SUICIDE"

    def test_natural_evidence_increases_natural(self):
        """Pro-natural evidence should push NATURAL up."""
        flags = ["natural_disease_history", "manner_of_death_natural", "no_injuries"]
        result = compute_hypothesis_scores(flags)
        assert result["scores"]["NATURAL"] > 0.3
        assert result["primary_hypothesis"] == "NATURAL"

    def test_unknown_evidence_ignored(self):
        """Unknown evidence flags should not affect scores."""
        flags = ["totally_unknown_flag"]
        result = compute_hypothesis_scores(flags)
        assert len(result["evidence_applied"]) == 0
        for h in HYPOTHESES:
            assert abs(result["scores"][h] - 0.2) < 0.01

    def test_determinism(self):
        """Same input must always produce exact same output."""
        flags = ["defensive_wounds_present", "manner_of_death_homicide"]
        r1 = compute_hypothesis_scores(flags)
        r2 = compute_hypothesis_scores(flags)
        assert r1["scores"] == r2["scores"]

    def test_all_hypotheses_present(self):
        """Output must always contain all 5 hypotheses."""
        result = compute_hypothesis_scores(["blunt_force_trauma"])
        for h in HYPOTHESES:
            assert h in result["scores"]

    def test_evidence_applied_tracking(self):
        """Only recognized evidence should appear in applied list."""
        flags = ["defensive_wounds_present", "unknown_flag", "blunt_force_trauma"]
        result = compute_hypothesis_scores(flags)
        assert "defensive_wounds_present" in result["evidence_applied"]
        assert "blunt_force_trauma" in result["evidence_applied"]
        assert "unknown_flag" not in result["evidence_applied"]

    def test_with_custom_prior(self):
        """Custom prior should shift the starting distribution."""
        prior = {"HOMICIDE": 0.5, "SUICIDE": 0.2, "ACCIDENT": 0.15, "NATURAL": 0.1, "UNDETERMINED": 0.05}
        result = compute_hypothesis_scores([], prior_scores=prior)
        assert result["scores"]["HOMICIDE"] > result["scores"]["NATURAL"]

    def test_conflicting_evidence(self):
        """Conflicting evidence should produce mixed posteriors."""
        flags = ["manner_of_death_homicide", "hesitation_wounds"]
        result = compute_hypothesis_scores(flags)
        assert result["scores"]["HOMICIDE"] > 0.15
        assert result["scores"]["SUICIDE"] > 0.15

    def test_no_negative_probabilities(self):
        """All probabilities must be >= 0."""
        flags = list(EVIDENCE_WEIGHTS.keys())
        result = compute_hypothesis_scores(flags)
        for h, p in result["scores"].items():
            assert p >= 0, f"{h} has negative probability: {p}"

    def test_all_evidence_stress(self):
        """Pump all evidence through — should not crash."""
        flags = list(EVIDENCE_WEIGHTS.keys())
        result = compute_hypothesis_scores(flags)
        assert abs(sum(result["scores"].values()) - 1.0) < 0.001


class TestContradictionDetection:
    """Test inter-source contradiction detection."""

    def test_suicide_with_defensive_wounds(self):
        autopsy = {"manner_of_death": "SUICIDE", "defensive_wounds": True}
        result = detect_contradictions(autopsy, {}, {})
        assert "PATHOLOGIST_MANNER_VS_DEFENSIVE_WOUNDS" in result

    def test_homicide_with_hesitation_wounds(self):
        autopsy = {"manner_of_death": "HOMICIDE", "hesitation_wounds": True}
        result = detect_contradictions(autopsy, {}, {})
        assert "HOMICIDE_MANNER_VS_HESITATION_WOUNDS" in result

    def test_natural_with_injuries(self):
        autopsy = {"manner_of_death": "NATURAL", "injuries_present": True}
        result = detect_contradictions(autopsy, {}, {})
        assert "NATURAL_MANNER_VS_INJURIES_PRESENT" in result

    def test_cdr_silence_with_financial_activity(self):
        cdr = {"forensic_flags": ["SILENCE_WINDOW_DURING_TOD"]}
        fin = {"forensic_flags": ["LARGE_TRANSACTION_NEAR_TOD"]}
        result = detect_contradictions({}, cdr, fin)
        assert "CDR_SILENCE_BUT_FINANCIAL_ACTIVITY_NEAR_TOD" in result

    def test_no_contradictions(self):
        autopsy = {"manner_of_death": "HOMICIDE", "defensive_wounds": True}
        result = detect_contradictions(autopsy, {}, {})
        assert len(result) == 0

    def test_empty_inputs(self):
        result = detect_contradictions({}, {}, {})
        assert result == []
