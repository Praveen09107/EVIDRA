# PLAN 09 — Timeline Anomaly Agent
**Owner:** Dev A | **Hour:** 12:00–13:00 | **Priority:** HIGH

---

## 1. Objective
Implement the `TimelineAnomalyAgent` (Tier 3). It fuses PyTorch Autoencoders and Scikit-Learn Isolation Forests to score time windows across CDR and Financial events for unusual behavior.

---

## 2. Main Agent Coordinator

**File: `services/agents/timeline_anomaly/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult
from .autoencoder import score_with_autoencoder
from .isolation_forest import score_with_isolation_forest

class TimelineAnomalyAgent(BaseAgent):
    agent_id = "timeline_anomaly"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        # Get prior data
        cdr = await self.get_prior_result(task, "cdr_analyzer") or {}
        fin = await self.get_prior_result(task, "financial_analyzer") or {}
        
        events = cdr.get("events", [])
        transactions = fin.get("anomalies", [])
        
        if not events and not transactions:
            return AgentResult(data={}, warnings=["No CDR or Financial data available for timeline."])
            
        # Build hourly feature matrix
        # Columns: [cdr_event_count, cdr_duration, fin_withdrawal_amount]
        # Group by hour
        
        from collections import defaultdict
        from datetime import datetime
        
        hourly_data = defaultdict(lambda: [0.0, 0.0, 0.0])
        
        for e in events:
            hr = e["timestamp"][:13] # YYYY-MM-DDTHH
            hourly_data[hr][0] += 1
            hourly_data[hr][1] += float(e["duration"])
            
        for t in transactions:
            # Assuming financial data is YYYY-MM-DD, map to hour 12 for simplicity if no time
            hr = t["date"] + "T12" if "T" not in t["date"] else t["date"][:13]
            hourly_data[hr][2] += float(t["withdrawal"])
            
        features = list(hourly_data.values())
        keys = list(hourly_data.keys())
        
        if len(features) < 5:
            return AgentResult(data={}, warnings=["Not enough timeline data to run ML anomaly detection."])
            
        self.log_step(task, "ML_INFERENCE", "Running PyTorch Autoencoder", f"Scoring {len(features)} windows")
        ae_scores = score_with_autoencoder(features)
        
        self.log_step(task, "ML_INFERENCE", "Running Isolation Forest", f"Scoring {len(features)} windows")
        if_scores = score_with_isolation_forest(features)
        
        # Fuse scores (normalize and average)
        results = []
        for i, k in enumerate(keys):
            fused = (ae_scores[i] + if_scores[i]) / 2.0
            if fused > 0.8: # Threshold
                results.append({
                    "time_window": k,
                    "anomaly_score": fused,
                    "ae_score": ae_scores[i],
                    "if_score": if_scores[i],
                    "details": features[i]
                })
                
        results.sort(key=lambda x: x["anomaly_score"], reverse=True)
        
        return AgentResult(data={"anomalous_windows": results})
```

---

## 3. PyTorch Autoencoder

**File: `services/agents/timeline_anomaly/autoencoder.py`**

```python
import torch
import torch.nn as nn
import numpy as np

class TimelineAE(nn.Module):
    def __init__(self, input_dim=3):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 4)
        )
        self.decoder = nn.Sequential(
            nn.Linear(4, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )
        
    def forward(self, x):
        return self.decoder(self.encoder(x))

def score_with_autoencoder(features: list) -> list:
    """Train a quick AE on the features and return reconstruction error as score."""
    X = np.array(features, dtype=np.float32)
    
    # Normalize
    max_vals = X.max(axis=0) + 1e-5
    X_norm = X / max_vals
    
    model = TimelineAE(input_dim=3)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss(reduction='none')
    
    # Train quickly (few epochs for MVP)
    X_t = torch.tensor(X_norm)
    for _ in range(50):
        optimizer.zero_grad()
        out = model(X_t)
        loss = criterion(out, X_t).mean()
        loss.backward()
        optimizer.step()
        
    # Score
    with torch.no_grad():
        out = model(X_t)
        errors = criterion(out, X_t).mean(dim=1).numpy()
        
    # Min-max scale errors to 0-1
    if errors.max() > errors.min():
        errors = (errors - errors.min()) / (errors.max() - errors.min())
    else:
        errors = np.zeros_like(errors)
        
    return errors.tolist()
```

---

## 4. Isolation Forest

**File: `services/agents/timeline_anomaly/isolation_forest.py`**

```python
import numpy as np
from sklearn.ensemble import IsolationForest

def score_with_isolation_forest(features: list) -> list:
    X = np.array(features, dtype=np.float32)
    
    # Fit IF
    clf = IsolationForest(n_estimators=100, random_state=42)
    clf.fit(X)
    
    # Score (lower is more anomalous, flip it)
    scores = clf.decision_function(X)
    
    # Invert and scale to 0-1
    scores = -scores
    if scores.max() > scores.min():
        scores = (scores - scores.min()) / (scores.max() - scores.min())
    else:
        scores = np.zeros_like(scores)
        
    return scores.tolist()
```

## Acceptance Criteria
- [ ] PyTorch model trains inline over 50 epochs (takes <1s on RTX 3050).
- [ ] IsolationForest returns scores array.
- [ ] Agent correctly averages scores and filters windows > 0.8 anomaly.
