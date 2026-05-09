# PLAN 10 — Tier 3 & 4 Agents (Fusion & Extraction)
**Owner:** Dev A | **Hour:** 13:00–15:00 | **Priority:** HIGH

---

## 1. Objective
Implement the mid-tier agents that fuse data across domains.
- **Collision Agent (M-10 | Tier 3):** Correlates physical tracks (from images) with digital tracks (CDR cell towers).
- **Hotspot Engine (M-11 | Tier 4):** Fuses TOD, Timeline Anomalies, and Collisions into ranked spatial-temporal hotspots.
- **Claim Extractor (M-12 | Tier 4):** Uses LLM to extract atomic forensic claims (e.g., "Victim was alive at 11 PM") from text.

---

## 2. Collision Agent (M-10)

**File: `services/agents/collision_agent/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult

class CollisionAgent(BaseAgent):
    agent_id = "collision_agent"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        cdr_data = await self.get_prior_result(task, "cdr_analyzer") or {}
        img_data = await self.get_prior_result(task, "image_agent") or {}
        
        events = cdr_data.get("events", [])
        img_extractions = img_data.get("image_extractions", [])
        
        if not events or not img_extractions:
            return AgentResult(data={}, warnings=["Insufficient data for collision analysis."])
            
        self.log_step(task, "CONSISTENCY_CHECK", "Checking for physical/digital collisions", "Comparing CDR and images")
        
        collisions = []
        # Mock logic: find if a phone call happens in the same hour an image was taken
        # In reality, this would use extracted image timestamps and location matching.
        
        return AgentResult(data={"collisions": collisions})
```

---

## 3. Hotspot Engine (M-11)

**File: `services/agents/hotspot_engine/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult

class HotspotEngine(BaseAgent):
    agent_id = "hotspot_engine"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        tod_data = await self.get_prior_result(task, "tod_agent") or {}
        anomaly_data = await self.get_prior_result(task, "timeline_anomaly") or {}
        
        anomalies = anomaly_data.get("anomalous_windows", [])
        pmi = tod_data.get("pmi_hours", 0)
        
        hotspots = []
        
        # Rank by anomaly score
        for i, a in enumerate(anomalies):
            hotspots.append({
                "rank": i + 1,
                "time_window": a["time_window"],
                "score": a["anomaly_score"],
                "is_near_tod": True if pmi > 0 else False,  # Simplified check
                "sources": ["CDR", "FINANCIAL"]
            })
            
        self.log_step(task, "BAYESIAN_FUSION", "Generated Hotspots", f"Ranked {len(hotspots)} windows")
        
        return AgentResult(data={"hotspots": hotspots})
```

---

## 4. Claim Extractor (M-12)

**File: `services/agents/claim_extractor/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult
from services.llm_gateway import llm

PROMPT = """Extract atomic forensic claims from this text.
A claim is a single verifiable statement (e.g., "Victim had 5000 INR withdrawn").
Return valid JSON:
{
  "claims": [
    {"text": "string", "type": "EVENT|STATE|ALIBI", "confidence": 0.0-1.0}
  ]
}
Text:
{text}"""

class ClaimExtractorAgent(BaseAgent):
    agent_id = "claim_extractor"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        norm_data = await self.get_prior_result(task, "format_normalizer")
        files = norm_data.get("normalized_files", []) if norm_data else []
        
        all_text = ""
        for f in files:
            all_text += f["normalized_text"][:2000] + "\n"
            
        if not all_text:
            return AgentResult(data={}, warnings=["No text to extract claims from."])
            
        self.log_step(task, "LLM_EXTRACTION", "Extracting claims", "Sending to Gemini")
        result = await llm.complete_json(self.agent_id, PROMPT.format(text=all_text))
        
        claims = result.get("claims", [])
        self.log_step(task, "MODEL_OUTPUT", f"Extracted {len(claims)} claims", "Completed")
        
        return AgentResult(data={"claims": claims})
```

## Acceptance Criteria
- [ ] Hotspot engine ranks anomalies properly.
- [ ] Claim extractor returns valid atomic claims using the LLM Gateway.
