import pytest
from agents.fusion.hypothesis_manager import EVIDENCE_WEIGHTS, compute_hypothesis_scores

def test_evidence_weights_defined():
    # Ensure some expected weights exist
    assert "defensive_wounds_present" in EVIDENCE_WEIGHTS
    assert "manner_of_death_homicide" in EVIDENCE_WEIGHTS
    assert "manner_of_death_suicide" in EVIDENCE_WEIGHTS

def test_evidence_weights_structure():
    # Verify exact weights are numeric
    w = EVIDENCE_WEIGHTS["defensive_wounds_present"]
    assert "HOMICIDE" in w
    assert isinstance(w["HOMICIDE"], float)

def test_bayesian_fusion():
    # Starting priors
    priors = {"HOMICIDE": 0.2, "SUICIDE": 0.2, "ACCIDENT": 0.2, "NATURAL": 0.2, "UNDETERMINED": 0.2}
    
    # Evidence hits
    evidence_hits = ["defensive_wounds_present", "large_financial_txn_near_tod"]
    
    # Compute posteriors
    result = compute_hypothesis_scores(evidence_hits, priors)
    posteriors = result["scores"]
    
    # HOMICIDE should heavily increase due to defensive wounds + cash withdrawal
    assert posteriors["HOMICIDE"] > 0.3
    assert posteriors["HOMICIDE"] > posteriors["SUICIDE"]
    assert sum(posteriors.values()) == pytest.approx(1.0, 0.001)
