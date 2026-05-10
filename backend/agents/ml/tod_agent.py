"""
EVIDRA — Time of Death (TOD) Agent (Tier 3 / M-07).

Implements Complete ML Specification §1 and §7:
Layer 1: Henssge Numeric Solver (Brentq)
Layer 2: Sign Likelihoods (truncated normal distributions)
Layer 3: ML Surrogate (RF + GBM ensemble, 13 features, 10K synthetic training)
Layer 4: Bayesian Monte Carlo Fusion (10K samples)
Layer 5: SHAP Explainability (TreeSHAP for RF)
"""
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm, truncnorm
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import logging
from uuid import UUID
from datetime import datetime, timedelta
from agents.base import BaseAgent
from core.database import db

logger = logging.getLogger("evidra.tod")

# ═══════════════════════════════════════════════════════════
# CLOTHING CORRECTION FACTORS (Henssge nomogram)
# ═══════════════════════════════════════════════════════════

CLOTHING_CORRECTION = {
    "NONE": 0.75, "LIGHT": 1.0, "MEDIUM": 1.4, "HEAVY": 2.0,
}

# ═══════════════════════════════════════════════════════════
# LAYER 1: Henssge Numeric Solver (spec §1.1)
# ═══════════════════════════════════════════════════════════

def henssge_estimate(temp_rectal: float, temp_ambient: float, weight_kg: float, cf: float = 1.0) -> dict | None:
    """
    Solve the Henssge double-exponential cooling equation for PMI.
    Q(t) = 1.25·exp(-B·t) - 0.25·exp(-5B·t)
    B = 1.2815·(cf·weight)^(-0.625) + 0.0284
    """
    if temp_rectal <= temp_ambient or temp_ambient >= 37.2:
        return None

    T_norm = (temp_rectal - temp_ambient) / (37.2 - temp_ambient)
    if T_norm <= 0 or T_norm >= 1.25:
        return None

    B = 1.2815 * ((cf * weight_kg) ** -0.625) + 0.0284

    def cooling_eq(t):
        return 1.25 * np.exp(-B * t) - 0.25 * np.exp(-5 * B * t) - T_norm

    try:
        t_mean = brentq(cooling_eq, 0.01, 120.0)
    except ValueError:
        return None

    # Henssge tolerance bands (spec §1.1)
    if t_mean <= 10:
        tolerance = 2.8
    elif t_mean <= 20:
        tolerance = 4.8
    else:
        tolerance = 7.4

    return {
        "mean_hours": round(t_mean, 2),
        "lower_95": round(max(0, t_mean - tolerance), 2),
        "upper_95": round(t_mean + tolerance, 2),
        "tolerance": tolerance,
        "B_coefficient": round(B, 6),
    }


# ═══════════════════════════════════════════════════════════
# LAYER 2: Sign Likelihoods (spec §1.2)
# ═══════════════════════════════════════════════════════════

SIGN_DISTRIBUTIONS = {
    "rigor_mortis": {
        "NONE":      {"mean": 1.0, "std": 1.0, "lower": 0, "upper": 3},
        "EARLY":     {"mean": 5.0, "std": 2.0, "lower": 2, "upper": 10},
        "FULL":      {"mean": 12.0, "std": 4.0, "lower": 6, "upper": 36},
        "RESOLVING": {"mean": 36.0, "std": 12.0, "lower": 24, "upper": 72},
    },
    "livor_mortis": {
        "NONE":  {"mean": 1.0, "std": 0.5, "lower": 0, "upper": 2},
        "EARLY": {"mean": 5.0, "std": 3.0, "lower": 1, "upper": 12},
        "FIXED": {"mean": 18.0, "std": 6.0, "lower": 8, "upper": 48},
    },
    "decomposition": {
        "NONE":     {"mean": 12.0, "std": 12.0, "lower": 0, "upper": 48},
        "EARLY":    {"mean": 72.0, "std": 24.0, "lower": 24, "upper": 120},
        "MODERATE": {"mean": 144.0, "std": 48.0, "lower": 72, "upper": 336},
        "ADVANCED": {"mean": 336.0, "std": 120.0, "lower": 168, "upper": 720},
    },
}


def compute_sign_likelihood(sign_type: str, stage: str, pmi_hours: float) -> float:
    """Compute likelihood of observing a given sign stage at a specific PMI."""
    if sign_type not in SIGN_DISTRIBUTIONS or stage not in SIGN_DISTRIBUTIONS[sign_type]:
        return 1.0  # Uninformative

    params = SIGN_DISTRIBUTIONS[sign_type][stage]
    a = (params["lower"] - params["mean"]) / params["std"]
    b = (params["upper"] - params["mean"]) / params["std"]
    return float(truncnorm.pdf(pmi_hours, a, b, loc=params["mean"], scale=params["std"]))


# ═══════════════════════════════════════════════════════════
# LAYER 3: ML Surrogate — RF + GBM Ensemble (spec §1.3)
# ═══════════════════════════════════════════════════════════

FEATURE_NAMES = [
    "temp_rectal", "delta_temp", "ambient_temp",
    "rigor_stage", "livor_stage", "decomp_stage",
    "weight_kg", "clothing", "indoor", "humidity",
    "wind_speed", "hours_last_seen", "cooling_rate",
]

RIGOR_MAP = {"NONE": 0, "EARLY": 1, "FULL": 2, "RESOLVING": 3}
LIVOR_MAP = {"NONE": 0, "EARLY": 1, "FIXED": 2}
DECOMP_MAP = {"NONE": 0, "EARLY": 1, "MODERATE": 2, "ADVANCED": 3}


class TodMLModel:
    """Ensemble of RF + GBM for robust PMI prediction (spec §1.3)."""

    def __init__(self):
        self.rf = RandomForestRegressor(
            n_estimators=500, max_depth=12, min_samples_leaf=5,
            n_jobs=-1, random_state=42,
        )
        self.gbm = GradientBoostingRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            subsample=0.8, random_state=42,
        )
        self.scaler = StandardScaler()
        self.ensemble_weights = [0.55, 0.45]  # RF, GBM
        self.is_trained = False

    def train_synthetic(self, n_cases: int = 10000):
        """Generate synthetic PMI dataset using Henssge physics as ground truth."""
        logger.info(f"Training TOD ML Surrogate on {n_cases} synthetic cases...")
        np.random.seed(42)
        records = []

        for _ in range(n_cases):
            weight = np.random.uniform(45, 110)
            ambient = np.random.uniform(10, 35)
            clothing = np.random.choice([0, 1, 2, 3])
            indoor = np.random.choice([0, 1])
            true_pmi = np.random.uniform(0.5, 72)
            humidity = np.random.uniform(30, 90)
            wind = np.random.uniform(0, 20) if not indoor else np.random.uniform(0, 2)
            hours_last_seen = true_pmi + np.random.uniform(0, 12)

            cf_map = {0: 0.75, 1: 1.0, 2: 1.4, 3: 2.0}
            cf = cf_map[clothing]
            B = 1.2815 * ((cf * weight) ** -0.625) + 0.0284
            T_norm = 1.25 * np.exp(-B * true_pmi) - 0.25 * np.exp(-5 * B * true_pmi)
            rectal = ambient + T_norm * (37.2 - ambient)
            rectal += np.random.normal(0, 0.3)  # measurement noise

            # Derive signs
            rigor = 0 if true_pmi < 2 else 1 if true_pmi < 8 else 2 if true_pmi < 36 else 3
            livor = 0 if true_pmi < 2 else 1 if true_pmi < 12 else 2
            decomp = 0 if true_pmi < 48 else 1 if true_pmi < 96 else 2 if true_pmi < 240 else 3

            # Noise on signs
            rigor = np.clip(rigor + np.random.choice([-1, 0, 0, 0, 1]), 0, 3)
            cooling_rate = (37.2 - rectal) / max(true_pmi, 0.5)

            records.append([
                rectal, rectal - ambient, ambient,
                rigor, livor, decomp,
                weight, clothing, indoor, humidity,
                wind, hours_last_seen, cooling_rate,
                true_pmi,
            ])

        data = np.array(records)
        X = data[:, :13]
        y = data[:, 13]

        X_scaled = self.scaler.fit_transform(X)
        self.rf.fit(X_scaled, y)
        self.gbm.fit(X_scaled, y)
        self.is_trained = True

        # Validate
        rf_scores = cross_val_score(self.rf, X_scaled, y, cv=5, scoring="neg_mean_absolute_error")
        logger.info(f"TOD RF Cross-Val MAE: {-rf_scores.mean():.2f}h (target: ≤4.5h)")
        logger.info("TOD ML Surrogate training complete.")

    def predict_with_uncertainty(self, features: np.ndarray) -> dict:
        if not self.is_trained:
            self.train_synthetic()

        X_scaled = self.scaler.transform(features.reshape(1, -1))

        # RF: per-tree predictions → mean + std
        rf_preds = np.array([tree.predict(X_scaled)[0] for tree in self.rf.estimators_])
        rf_mean = rf_preds.mean()
        rf_std = rf_preds.std()

        # GBM point prediction
        gbm_pred = self.gbm.predict(X_scaled)[0]

        # Weighted ensemble
        ensemble_mean = self.ensemble_weights[0] * rf_mean + self.ensemble_weights[1] * gbm_pred

        return {
            "pmi_hours_mean": round(float(ensemble_mean), 2),
            "pmi_hours_std": round(float(rf_std), 2),
            "pmi_95_lower": round(float(max(0, ensemble_mean - 1.96 * rf_std)), 2),
            "pmi_95_upper": round(float(ensemble_mean + 1.96 * rf_std), 2),
            "rf_mean": round(float(rf_mean), 2),
            "gbm_mean": round(float(gbm_pred), 2),
        }

    def feature_importance(self) -> dict:
        if not self.is_trained:
            return {}
        importances = self.rf.feature_importances_
        return dict(sorted(
            zip(FEATURE_NAMES, [round(float(v), 4) for v in importances]),
            key=lambda x: x[1], reverse=True,
        ))


# ═══════════════════════════════════════════════════════════
# LAYER 4: Bayesian Monte Carlo Fusion (spec §1.4)
# ═══════════════════════════════════════════════════════════

def tod_monte_carlo(
    henssge: dict | None,
    ml_result: dict | None,
    sign_likelihoods: dict | None,
    discovery_time: datetime,
    n_samples: int = 10000,
) -> dict | None:
    """Fuse physics, ML, and sign likelihoods via Monte Carlo."""
    t_grid = np.linspace(0.1, 72, n_samples)
    log_weights = np.zeros(n_samples)

    # Physics prior
    if henssge:
        sigma = henssge["tolerance"] / 1.96
        log_weights += norm.logpdf(t_grid, henssge["mean_hours"], sigma)

    # ML surrogate likelihood
    if ml_result:
        ml_sigma = max(ml_result["pmi_hours_std"], 1.0)
        log_weights += 0.7 * norm.logpdf(t_grid, ml_result["pmi_hours_mean"], ml_sigma)

    # Sign likelihoods
    if sign_likelihoods:
        for sign_type, stage in sign_likelihoods.items():
            for i, t in enumerate(t_grid):
                ll = compute_sign_likelihood(sign_type, stage, t)
                if ll > 0:
                    log_weights[i] += np.log(ll + 1e-30)

    # Normalize
    weights = np.exp(log_weights - log_weights.max())
    if weights.sum() == 0:
        return None
    weights /= weights.sum()

    # Point estimates
    mean_pmi = float(np.average(t_grid, weights=weights))
    cum_weights = np.cumsum(weights)
    lower_idx = int(np.searchsorted(cum_weights, 0.025))
    upper_idx = int(np.searchsorted(cum_weights, 0.975))
    median_idx = int(np.searchsorted(cum_weights, 0.5))

    tod_point = discovery_time - timedelta(hours=t_grid[median_idx])
    tod_lower = discovery_time - timedelta(hours=t_grid[upper_idx])
    tod_upper = discovery_time - timedelta(hours=t_grid[lower_idx])

    return {
        "pmi_hours_median": round(float(t_grid[median_idx]), 2),
        "pmi_hours_mean": round(mean_pmi, 2),
        "pmi_95_lower_hours": round(float(t_grid[lower_idx]), 2),
        "pmi_95_upper_hours": round(float(t_grid[upper_idx]), 2),
        "tod_point_estimate": tod_point.isoformat(),
        "tod_window_95_start": tod_lower.isoformat(),
        "tod_window_95_end": tod_upper.isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# LAYER 5: SHAP Explainability (spec §7)
# ═══════════════════════════════════════════════════════════

def compute_shap_contributions(model: TodMLModel, features: np.ndarray) -> list[dict]:
    """Compute TreeSHAP feature contributions for TOD estimate."""
    try:
        import shap
        X_scaled = model.scaler.transform(features.reshape(1, -1))
        explainer = shap.TreeExplainer(model.rf)
        shap_values = explainer.shap_values(X_scaled)[0]

        contributions = []
        for fname, sv in zip(FEATURE_NAMES, shap_values):
            contributions.append({
                "feature": fname,
                "shap_value": round(float(sv), 4),
                "direction": "EARLIER" if sv < 0 else "LATER" if sv > 0 else "NEUTRAL",
                "magnitude": round(abs(float(sv)), 4),
            })
        return sorted(contributions, key=lambda x: x["magnitude"], reverse=True)
    except ImportError:
        logger.warning("SHAP not installed — skipping explainability")
        return []
    except Exception as e:
        logger.warning(f"SHAP computation failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# TOD AGENT
# ═══════════════════════════════════════════════════════════

# Class-level model cache
_tod_model: TodMLModel | None = None


def _get_tod_model() -> TodMLModel:
    global _tod_model
    if _tod_model is None:
        _tod_model = TodMLModel()
        _tod_model.train_synthetic(n_cases=10000)
    return _tod_model


class TodAgent(BaseAgent):
    agent_id = "tod_agent"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        autopsy_res = await self.get_prior_result("autopsy_agent")
        if not autopsy_res or "pathology" not in autopsy_res:
            return {"status": "SKIPPED", "reason": "No autopsy data"}

        p = autopsy_res["pathology"]
        tod_ind = p.get("tod_indicators", {})
        demo = p.get("demographics", {})

        T_rectal = tod_ind.get("rectal_temp_c")
        T_ambient = tod_ind.get("ambient_temp_c")
        weight = demo.get("weight_kg", 70.0)
        clothing_str = tod_ind.get("clothing", "MEDIUM")
        cf = CLOTHING_CORRECTION.get(clothing_str, 1.0)
        indoor = 1 if tod_ind.get("scene_type") in ("INDOOR", None) else 0

        rigor = tod_ind.get("rigor_mortis", "NONE")
        livor = tod_ind.get("livor_mortis", "NONE")
        decomp = tod_ind.get("decomposition", "NONE")

        # Discovery time from case data
        discovery_str = p.get("found_dead_time") or tod_ind.get("temp_time")
        try:
            discovery_time = datetime.fromisoformat(discovery_str) if discovery_str else datetime.utcnow()
        except (ValueError, TypeError):
            discovery_time = datetime.utcnow()

        # Layer 1: Henssge
        henssge = None
        if T_rectal and T_ambient:
            henssge = henssge_estimate(T_rectal, T_ambient, weight, cf)
            if henssge:
                await self.log_step(
                    "PHYSICS_MODEL",
                    "Henssge Cooling Equation",
                    f"PMI: {henssge['mean_hours']:.1f}h [{henssge['lower_95']:.1f}–{henssge['upper_95']:.1f}h]. B={henssge['B_coefficient']:.5f}",
                    confidence=0.85,
                )

        # Layer 2: Sign likelihoods
        sign_data = {
            "rigor_mortis": rigor,
            "livor_mortis": livor,
            "decomposition": decomp,
        }

        await self.log_step(
            "ML_INFERENCE",
            "Sign Likelihood Computation",
            f"Signs: rigor={rigor}, livor={livor}, decomp={decomp}",
            confidence=0.80,
        )

        # Layer 3: ML Surrogate (13 features)
        ml_result = None
        feature_importance = {}
        shap_contributions = []

        if T_rectal and T_ambient:
            model = _get_tod_model()
            cooling_rate = (37.2 - T_rectal) / max(henssge["mean_hours"] if henssge else 6, 0.5)
            hours_last_seen = 0  # Will be populated from case data if available

            features = np.array([
                T_rectal,
                T_rectal - T_ambient,
                T_ambient,
                RIGOR_MAP.get(rigor, 0),
                LIVOR_MAP.get(livor, 0),
                DECOMP_MAP.get(decomp, 0),
                weight,
                list(CLOTHING_CORRECTION.values()).index(cf) if cf in CLOTHING_CORRECTION.values() else 1,
                indoor,
                50.0,  # humidity (default)
                5.0 if not indoor else 0.5,  # wind
                hours_last_seen,
                cooling_rate,
            ], dtype=np.float64)

            ml_result = model.predict_with_uncertainty(features)
            feature_importance = model.feature_importance()
            shap_contributions = compute_shap_contributions(model, features)

            await self.log_step(
                "ML_INFERENCE",
                "RF/GBM Ensemble Prediction",
                f"ML PMI: {ml_result['pmi_hours_mean']:.1f}h ± {ml_result['pmi_hours_std']:.1f}h. "
                f"RF={ml_result['rf_mean']:.1f}h, GBM={ml_result['gbm_mean']:.1f}h",
                confidence=0.88,
            )

        # Layer 4: Monte Carlo Fusion
        posterior = tod_monte_carlo(henssge, ml_result, sign_data, discovery_time)

        if posterior:
            await self.log_step(
                "BAYESIAN_FUSION",
                "Monte Carlo Posterior Fusion",
                f"Fused TOD: {posterior['tod_point_estimate']} "
                f"[{posterior['pmi_95_lower_hours']:.1f}–{posterior['pmi_95_upper_hours']:.1f}h]",
                confidence=0.90,
            )

        return {
            "henssge": henssge,
            "ml_surrogate": ml_result,
            "sign_data": sign_data,
            "posterior": posterior,
            "feature_importance": feature_importance,
            "shap_contributions": shap_contributions[:5],  # Top 5 features
            "window_start": posterior["tod_window_95_start"] if posterior else None,
            "window_end": posterior["tod_window_95_end"] if posterior else None,
            "_confidence": 0.90,
        }
