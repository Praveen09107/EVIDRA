"""
Tests for: agents/ml/tod_agent.py — Henssge nomogram solver, sign likelihoods, ML model training.
"""
import pytest
import numpy as np
from agents.ml.tod_agent import (
    henssge_estimate, compute_sign_likelihood,
    TodMLModel, CLOTHING_CORRECTION,
    SIGN_DISTRIBUTIONS, RIGOR_MAP, LIVOR_MAP, DECOMP_MAP,
)


class TestHenssgeEstimate:
    """Test Layer 1: Henssge Numeric Solver."""

    def test_normal_case(self):
        """Standard indoor case: rectal 30°C, ambient 18°C, weight 70kg."""
        result = henssge_estimate(30.0, 18.0, 70.0, cf=1.0)
        assert result is not None
        assert result["mean_hours"] > 0
        assert result["lower_95"] < result["mean_hours"]
        assert result["upper_95"] > result["mean_hours"]

    def test_fresh_body(self):
        """Nearly fresh body (36°C rectal, 20°C ambient) → short PMI."""
        result = henssge_estimate(36.0, 20.0, 70.0)
        assert result is not None
        assert result["mean_hours"] < 3.0

    def test_cold_body(self):
        """Cold body (20°C rectal, 18°C ambient) → longer PMI."""
        result = henssge_estimate(20.0, 18.0, 70.0)
        assert result is not None
        assert result["mean_hours"] > 10.0

    def test_invalid_below_ambient(self):
        """Rectal temp at or below ambient → None (no cooling)."""
        result = henssge_estimate(18.0, 18.0, 70.0)
        assert result is None

    def test_invalid_hot_ambient(self):
        """Ambient >= 37.2°C → None (not applicable)."""
        result = henssge_estimate(30.0, 38.0, 70.0)
        assert result is None

    def test_clothing_correction_heavy(self):
        """Heavy clothing → slower cooling → longer PMI."""
        result_light = henssge_estimate(30.0, 18.0, 70.0, cf=CLOTHING_CORRECTION["LIGHT"])
        result_heavy = henssge_estimate(30.0, 18.0, 70.0, cf=CLOTHING_CORRECTION["HEAVY"])
        assert result_light is not None
        assert result_heavy is not None
        assert result_heavy["mean_hours"] > result_light["mean_hours"]

    def test_heavier_body_slower_cooling(self):
        """Heavier body → slower cooling → longer PMI (same temp)."""
        result_light = henssge_estimate(30.0, 18.0, 50.0)
        result_heavy = henssge_estimate(30.0, 18.0, 100.0)
        assert result_light is not None
        assert result_heavy is not None
        assert result_heavy["mean_hours"] > result_light["mean_hours"]

    def test_tolerance_bands(self):
        """Short PMI → ±2.8h, medium → ±4.8h, long → ±7.4h."""
        short = henssge_estimate(35.0, 18.0, 70.0)
        assert short is not None
        if short["mean_hours"] <= 10:
            assert short["tolerance"] == 2.8

    def test_b_coefficient_positive(self):
        """B coefficient must always be positive."""
        result = henssge_estimate(30.0, 18.0, 70.0)
        assert result is not None
        assert result["B_coefficient"] > 0


class TestSignLikelihoods:
    """Test Layer 2: Postmortem sign likelihoods."""

    def test_rigor_none_at_1_hour(self):
        """No rigor at 1 hour → high likelihood."""
        ll = compute_sign_likelihood("rigor_mortis", "NONE", 1.0)
        assert ll > 0

    def test_rigor_full_at_12_hours(self):
        """Full rigor at 12 hours → high likelihood."""
        ll = compute_sign_likelihood("rigor_mortis", "FULL", 12.0)
        assert ll > 0

    def test_rigor_resolving_at_36_hours(self):
        """Resolving rigor at 36 hours → reasonable likelihood."""
        ll = compute_sign_likelihood("rigor_mortis", "RESOLVING", 36.0)
        assert ll > 0

    def test_livor_fixed_at_18_hours(self):
        """Fixed lividity at 18 hours → peak likelihood."""
        ll = compute_sign_likelihood("livor_mortis", "FIXED", 18.0)
        assert ll > 0

    def test_decomposition_early_at_72_hours(self):
        """Early decomposition at 72 hours → expected."""
        ll = compute_sign_likelihood("decomposition", "EARLY", 72.0)
        assert ll > 0

    def test_unknown_sign_returns_1(self):
        """Unknown sign type → uninformative (1.0)."""
        ll = compute_sign_likelihood("unknown_sign", "NONE", 5.0)
        assert ll == 1.0

    def test_unknown_stage_returns_1(self):
        """Unknown stage → uninformative (1.0)."""
        ll = compute_sign_likelihood("rigor_mortis", "UNKNOWN_STAGE", 5.0)
        assert ll == 1.0

    def test_non_negative(self):
        """Likelihoods must never be negative."""
        for sign_type, stages in SIGN_DISTRIBUTIONS.items():
            for stage in stages:
                for pmi in [0.5, 1, 5, 12, 24, 48, 72, 120]:
                    ll = compute_sign_likelihood(sign_type, stage, pmi)
                    assert ll >= 0, f"Negative likelihood for {sign_type}/{stage} at {pmi}h"


class TestTodMLModel:
    """Test Layer 3: ML Surrogate training and prediction."""

    @pytest.fixture(scope="class")
    def trained_model(self):
        model = TodMLModel()
        model.train_synthetic(n_cases=500)  # Small sample for speed
        return model

    def test_training_succeeds(self, trained_model):
        assert trained_model.is_trained is True

    def test_prediction_returns_positive(self, trained_model):
        features = np.array([30.0, 7.2, 18.0, 2, 1, 0, 70.0, 1, 1, 50, 0, 14.0, 0.5])
        result = trained_model.predict_with_uncertainty(features)
        assert result["pmi_hours_mean"] > 0

    def test_prediction_deterministic(self, trained_model):
        features = np.array([30.0, 7.2, 18.0, 2, 1, 0, 70.0, 1, 1, 50, 0, 14.0, 0.5])
        r1 = trained_model.predict_with_uncertainty(features)
        r2 = trained_model.predict_with_uncertainty(features)
        assert abs(r1["pmi_hours_mean"] - r2["pmi_hours_mean"]) < 0.01

    def test_cold_body_predicts_longer_pmi(self, trained_model):
        """Colder body → longer PMI."""
        warm = np.array([35.0, 2.2, 18.0, 0, 0, 0, 70.0, 1, 1, 50, 0, 5.0, 0.3])
        cold = np.array([20.0, 17.2, 18.0, 3, 2, 1, 70.0, 1, 1, 50, 0, 40.0, 0.8])
        r_warm = trained_model.predict_with_uncertainty(warm)
        r_cold = trained_model.predict_with_uncertainty(cold)
        assert r_cold["pmi_hours_mean"] > r_warm["pmi_hours_mean"]


class TestMappingTables:
    """Test encoding dictionaries used by ML features."""

    def test_rigor_map_complete(self):
        expected = {"NONE", "EARLY", "FULL", "RESOLVING"}
        assert set(RIGOR_MAP.keys()) == expected

    def test_livor_map_complete(self):
        expected = {"NONE", "EARLY", "FIXED"}
        assert set(LIVOR_MAP.keys()) == expected

    def test_decomp_map_complete(self):
        expected = {"NONE", "EARLY", "MODERATE", "ADVANCED"}
        assert set(DECOMP_MAP.keys()) == expected

    def test_clothing_correction_values(self):
        assert CLOTHING_CORRECTION["NONE"] < CLOTHING_CORRECTION["HEAVY"]
        assert all(v > 0 for v in CLOTHING_CORRECTION.values())
