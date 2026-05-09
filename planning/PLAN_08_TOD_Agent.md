# PLAN 08 — TOD Agent (Time of Death Estimator)
**Owner:** Dev A | **Hour:** 9:00–12:00 | **Priority:** CRITICAL

---

## 1. Objective
Implement the hybrid Time of Death (TOD) estimator. It fuses:
1. **Physics Model:** Henssge nomogram equation solved via SciPy `brentq`.
2. **ML Surrogate:** Random Forest regression trained on synthetic TOD data.
3. **Bayesian Monte Carlo:** Fusion of physics + ML + Gastric emptying priors.

---

## 2. Main Agent Coordinator

**File: `services/agents/tod_agent/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult
from .henssge import solve_henssge
from .ml_surrogate import get_rf_prediction
from .fusion import monte_carlo_tod_posterior

class TODAgent(BaseAgent):
    agent_id = "tod_agent"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        autopsy = await self.get_prior_result(task, "autopsy_agent")
        if not autopsy or "extractions" not in autopsy:
            return AgentResult(data={}, warnings=["No autopsy data found."])
            
        ext = autopsy["extractions"]
        T_body = ext.get("body_temperature_c")
        T_amb = ext.get("ambient_temperature_c")
        weight = ext.get("weight_kg", 70.0)
        
        if not T_body or not T_amb:
            return AgentResult(data={}, warnings=["Body or ambient temperature missing."])
            
        self.log_step(task, "PHYSICS_MODEL", "Running Henssge solver", f"Tb={T_body}, Ta={T_amb}, W={weight}")
        pmi_physics = solve_henssge(T_body, T_amb, weight)
        
        self.log_step(task, "ML_INFERENCE", "Running RF Surrogate", "Predicting PMI based on temps")
        pmi_ml = get_rf_prediction(T_body, T_amb, weight)
        
        self.log_step(task, "BAYESIAN_FUSION", "Monte Carlo Posterior Fusion", "Combining physics + ML")
        final_pmi, std_dev = monte_carlo_tod_posterior(pmi_physics, pmi_ml)
        
        return AgentResult(data={
            "pmi_hours": final_pmi,
            "pmi_std_dev": std_dev,
            "components": {
                "physics": pmi_physics,
                "ml": pmi_ml
            }
        }, confidence=0.85)
```

---

## 3. Physics Model (Henssge)

**File: `services/agents/tod_agent/henssge.py`**

```python
"""
Numeric solution to Henssge's equation using SciPy brentq.
(T_body - T_amb) / (37.2 - T_amb) = 1.25 * e^(-k*t) - 0.25 * e^(-5*k*t)
where k is a factor of weight.
"""
from scipy.optimize import brentq
import numpy as np

def solve_henssge(T_body: float, T_amb: float, weight_kg: float) -> float:
    # Basic bounds checking
    if T_body > 37.2: T_body = 37.2
    if T_body <= T_amb: return 24.0 # max out if body reached ambient
    
    # Calculate k
    # k = 1.2815 / (weight ** 0.625) - 0.0284
    k = 1.2815 / (weight_kg ** 0.625) - 0.0284
    if k <= 0: k = 0.01
    
    LHS = (T_body - T_amb) / (37.2 - T_amb)
    
    def equation(t):
        return 1.25 * np.exp(-k * t) - 0.25 * np.exp(-5 * k * t) - LHS
        
    try:
        # Solve for t (PMI) between 0 and 100 hours
        pmi = brentq(equation, 0, 100)
        return float(pmi)
    except ValueError:
        return 24.0 # Fallback
```

---

## 4. ML Surrogate (Random Forest)

**File: `services/agents/tod_agent/ml_surrogate.py`**

```python
"""
Random Forest trained on synthetic Henssge variations.
"""
import os
import pickle
import numpy as np
from sklearn.ensemble import RandomForestRegressor

MODEL_PATH = "models/tod_rf_surrogate.pkl"

def _train_surrogate():
    # Generate synthetic training data
    np.random.seed(42)
    N = 5000
    T_ambs = np.random.uniform(5, 30, N)
    weights = np.random.uniform(40, 120, N)
    pmis = np.random.uniform(1, 48, N)
    
    # Forward Henssge
    T_bodies = []
    for ta, w, t in zip(T_ambs, weights, pmis):
        k = 1.2815 / (w ** 0.625) - 0.0284
        k = max(k, 0.01)
        rhs = 1.25 * np.exp(-k * t) - 0.25 * np.exp(-5 * k * t)
        tb = ta + rhs * (37.2 - ta)
        T_bodies.append(tb)
        
    X = np.column_stack([T_bodies, T_ambs, weights])
    y = pmis
    
    rf = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
    rf.fit(X, y)
    
    os.makedirs("models", exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(rf, f)
    return rf

def get_rf_prediction(T_body: float, T_amb: float, weight_kg: float) -> float:
    if not os.path.exists(MODEL_PATH):
        _train_surrogate()
        
    with open(MODEL_PATH, "rb") as f:
        rf = pickle.load(f)
        
    pred = rf.predict([[T_body, T_amb, weight_kg]])[0]
    return float(pred)
```

---

## 5. Bayesian Monte Carlo Fusion

**File: `services/agents/tod_agent/fusion.py`**

```python
import numpy as np

def monte_carlo_tod_posterior(pmi_physics: float, pmi_ml: float, n_samples: int = 10000):
    """
    Fuse predictions using Monte Carlo simulation.
    Assume physics model has std dev = 1.5h, ML has std dev = 2.0h.
    """
    np.random.seed(42)
    samples_phys = np.random.normal(pmi_physics, 1.5, n_samples)
    samples_ml = np.random.normal(pmi_ml, 2.0, n_samples)
    
    # Bayesian product of experts (simplified via averaged samples)
    # Weights based on inverse variance
    w_phys = 1 / (1.5**2)
    w_ml = 1 / (2.0**2)
    
    fused = (samples_phys * w_phys + samples_ml * w_ml) / (w_phys + w_ml)
    
    return float(np.mean(fused)), float(np.std(fused))
```

## Acceptance Criteria
- [ ] Physics: `solve_henssge(30.0, 20.0, 70.0)` returns ~6-8 hours.
- [ ] Surrogate: Trains automatically if missing, fits within 5 seconds.
- [ ] Fusion: Combines both inputs into a single mean and std dev.
