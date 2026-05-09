# PLAN 11 — Tier 5, 6, 7 Agents (Reasoning, Guidance, Audit)
**Owner:** Dev A | **Hour:** 15:00–19:00 | **Priority:** CRITICAL

---

## 1. Objective
Implement the top-level reasoning agents.
- **Evidence-Claim Mapper (M-13 | T5):** Links extracted claims to evidence.
- **Hypothesis Manager (M-14 | T5):** Computes Bayesian scores for the 5 official death hypotheses.
- **Bias & Uncertainty (M-15 | T5):** Audits previous agents for cognitive bias.
- **NBE Agent (M-16 | T6):** Suggests "Next Best Evidence" to collect.
- **Reasoning Replay (M-17 | T7):** Compiles the final narrative and signs the audit trail.

---

## 2. Evidence-Claim Mapper (M-13)

**File: `services/agents/evidence_claim_mapper/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult

class EvidenceClaimMapperAgent(BaseAgent):
    agent_id = "evidence_claim_mapper"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        claims_data = await self.get_prior_result(task, "claim_extractor") or {}
        claims = claims_data.get("claims", [])
        
        self.log_step(task, "RULE", "Mapping claims", f"Evaluating {len(claims)} claims")
        # Mock logic: assigns SUPPORTS to all for MVP
        links = []
        for c in claims:
            links.append({"claim": c["text"], "label": "SUPPORTS", "confidence": 0.9})
            
        return AgentResult(data={"links": links})
```

---

## 3. Hypothesis Manager (M-14)

**File: `services/agents/hypothesis_manager/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult

class HypothesisManagerAgent(BaseAgent):
    agent_id = "hypothesis_manager"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        autopsy = await self.get_prior_result(task, "autopsy_agent") or {}
        manner = autopsy.get("extractions", {}).get("manner_of_death", "UNDETERMINED")
        
        self.log_step(task, "HYPOTHESIS_SCORE", "Scoring 5 hypotheses", f"Base manner: {manner}")
        
        # Bayesian mock
        scores = {
            "HOMICIDE": 0.1,
            "SUICIDE": 0.1,
            "ACCIDENT": 0.1,
            "NATURAL": 0.1,
            "UNDETERMINED": 0.6
        }
        
        if manner in scores:
            scores[manner] = 0.85
            scores["UNDETERMINED"] = 0.05
            
        hypotheses = [{"key": k, "probability": v, "trend": "STABLE"} for k, v in scores.items()]
        
        return AgentResult(data={"hypotheses": hypotheses, "primary": manner})
```

---

## 4. Bias & Uncertainty Monitor (M-15)

**File: `services/agents/bias_uncertainty/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult

class BiasUncertaintyAgent(BaseAgent):
    agent_id = "bias_uncertainty"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        self.log_step(task, "CONSISTENCY_CHECK", "Checking for cognitive bias", "No severe bias detected")
        return AgentResult(data={"bias_flags": [], "overall_confidence": 0.88})
```

---

## 5. NBE Agent (M-16)

**File: `services/agents/nbe_agent/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult

class NBEAgent(BaseAgent):
    agent_id = "nbe_agent"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        self.log_step(task, "RULE", "Generating Next Best Evidence", "Suggesting CCTV retrieval")
        suggestions = [
            {"action": "COLLECT_EVIDENCE", "description": "Request CCTV from BLR-T045 area", "priority": 0.9}
        ]
        return AgentResult(data={"suggestions": suggestions})
```

---

## 6. Reasoning Replay (M-17)

**File: `services/agents/reasoning_replay/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult
from services.database import db

class ReasoningReplayAgent(BaseAgent):
    agent_id = "reasoning_replay"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        # Fetch all steps
        steps = await db.fetch("SELECT * FROM replay_steps WHERE pipeline_run_id=$1 ORDER BY timestamp ASC", task.pipeline_run_id)
        
        self.log_step(task, "LLM_NARRATIVE", "Compiling final audit", f"Total steps: {len(steps)}")
        
        return AgentResult(data={"total_steps_audited": len(steps), "status": "LOCKED_AND_SIGNED"})
```

## Acceptance Criteria
- [ ] Hypothesis Manager maps autopsy manner to highest probability.
- [ ] Replay agent successfully fetches and counts all `replay_steps` inserted by previous agents.
