"""
EVIDRA — Time of Death (TOD) Agent (Tier 3).

Implements the full ML Specification:
Layer 1: Henssge Numeric Solver (scipy brentq)
Layer 2: Sign Likelihoods (truncnorm)
Layer 3: Bayesian Monte Carlo Fusion
"""
import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm, truncnorm
from uuid import UUID
from datetime import datetime, timedelta
from agents.base import BaseAgent
from core.database import db

# --- Layer 1: Henssge Numeric Solver ---
def henssge_estimate(temp_rectal: float, temp_ambient: float, weight_kg: float, cf: float = 1.0) -> dict:
    if temp_rectal <= temp_ambient:
        return None
    T_norm = (temp_rectal - temp_ambient) / (37.2 - temp_ambient)
    B = 1.2815 * ((cf * weight_kg) ** -0.625) + 0.0284

    def cooling_eq(t):
        return 1.25 * np.exp(-B * t) - 0.25 * np.exp(-5 * B * t) - T_norm

    try:
        t_mean = brentq(cooling_eq, 0.01, 100.0)
    except ValueError:
        return None

    tolerance = 2.8 if t_mean <= 10 else 4.8 if t_mean <= 20 else 7.4
    return {"mean_hours": t_mean, "lower_95": max(0, t_mean - tolerance), "upper_95": t_mean + tolerance}

# --- Layer 2: Sign Likelihoods ---
SIGN_DISTRIBUTIONS = {
    "rigor": {
        "NONE":      {"mu": 1.5,  "sigma": 1.5,  "lower": 0,   "upper": 4},
        "EARLY":     {"mu": 5.0,  "sigma": 3.0,  "lower": 2,   "upper": 10},
        "FULL":      {"mu": 18.0, "sigma": 8.0,  "lower": 8,   "upper": 36},
        "RESOLVING": {"mu": 48.0, "sigma": 12.0, "lower": 30,  "upper": 96}
    },
    "livor": {
        "NONE":      {"mu": 1.0,  "sigma": 1.0,  "lower": 0,   "upper": 3},
        "EARLY":     {"mu": 4.0,  "sigma": 2.0,  "lower": 1,   "upper": 8},
        "FIXED":     {"mu": 20.0, "sigma": 8.0,  "lower": 12,  "upper": 60}
    }
}

def sign_likelihood(pmi_h: float, sign_type: str, stage: str) -> float:
    if stage not in SIGN_DISTRIBUTIONS[sign_type]: return 1.0
    dist = SIGN_DISTRIBUTIONS[sign_type][stage]
    a = (dist["lower"] - dist["mu"]) / dist["sigma"]
    b = (dist["upper"] - dist["mu"]) / dist["sigma"]
    rv = truncnorm(a, b, loc=dist["mu"], scale=dist["sigma"])
    return rv.pdf(pmi_h)

# --- Layer 3: Monte Carlo Fusion ---
def tod_monte_carlo(henssge: dict, signs: dict, discovery_time: datetime, n_samples: int = 10000):
    t_grid = np.linspace(0, 72, n_samples)
    log_weights = np.zeros(n_samples)

    if henssge:
        physics_sigma = (henssge["upper_95"] - henssge["lower_95"]) / (2 * 1.96)
        log_weights += norm.logpdf(t_grid, henssge["mean_hours"], physics_sigma)

    for sign_type, stage in signs.items():
        liks = np.array([sign_likelihood(t, sign_type, stage) for t in t_grid])
        liks = np.clip(liks, 1e-12, None)
        log_weights += np.log(liks)

    weights = np.exp(log_weights - log_weights.max())
    if weights.sum() == 0: return None
    weights /= weights.sum()

    mean_idx = int(np.average(np.arange(n_samples), weights=weights))
    tod_samples = [discovery_time - timedelta(hours=float(t)) for t in t_grid]
    
    cum_weights = np.cumsum(weights)
    lower_idx = np.searchsorted(cum_weights, 0.025)
    upper_idx = min(len(tod_samples)-1, np.searchsorted(cum_weights, 0.975))

    return {
        "median": tod_samples[mean_idx].isoformat(),
        "lower_95": tod_samples[upper_idx].isoformat(), # Reversing indices because subtracting hours
        "upper_95": tod_samples[lower_idx].isoformat()
    }

class TodAgent(BaseAgent):
    agent_id = "tod_agent"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        autopsy_res = await self.get_prior_result("autopsy_agent")
        if not autopsy_res or "pathology" not in autopsy_res:
            return {"status": "SKIPPED"}
            
        p = autopsy_res["pathology"]
        T_rectal = p["tod_indicators"].get("rectal_temp_c")
        T_ambient = p["tod_indicators"].get("ambient_temp_c")
        weight = p["demographics"].get("weight_kg", 70.0)
        
        try:
            discovery_time = datetime.fromisoformat(p["tod_indicators"]["temp_time"].replace("Z", "+00:00"))
        except Exception:
            case = await db.fetchrow("SELECT incident_date FROM cases WHERE case_id=$1", case_id)
            discovery_time = case["incident_date"] or datetime.utcnow()

        henssge = None
        if T_rectal and T_ambient:
            henssge = henssge_estimate(T_rectal, T_ambient, weight)

        signs = {
            "rigor": p["tod_indicators"].get("rigor_mortis", "NONE"),
            "livor": p["tod_indicators"].get("livor_mortis", "NONE")
        }

        posterior = tod_monte_carlo(henssge, signs, discovery_time)
        if not posterior:
             return {"status": "FAILED", "reason": "Fusion failed to converge"}

        await self.log_step(
            "BAYESIAN_FUSION",
            "Monte Carlo TOD Fusion",
            f"Fused Henssge numeric solver with truncnorm signs. Median TOD: {posterior['median']}",
            confidence=0.9
        )

        return {"posterior": posterior, "_confidence": 0.9}
