# DEV A EXECUTION GUIDE — PART 3: Data Parsing & Core ML Agents
**Role:** Backend Lead & ML Engineer
**Hours:** 6:00–14:00 | **Priority:** CRITICAL

---

## 1. PHASE 6 — TIER 0 & TIER 1 AGENTS (Hour 6:00–9:00)

These are the ingestion agents. They parse raw files before the analytical agents run.

### Step 1.1 — Evidence Parser
**File: `services/agents/evidence_parser.py`**

```python
from ..base_agent import BaseAgent
from ..database import db

class EvidenceParserAgent(BaseAgent):
    agent_id = "evidence_parser"

    async def execute(self, case_id: str, payload: dict) -> dict:
        await self.log_step(case_id, payload["pipeline_run_id"], "FETCH_FILES", {"case": case_id})
        
        files = await db.fetch("SELECT * FROM case_files WHERE case_id = $1", case_id)
        
        parsed_data = {}
        for f in files:
            doc_type = f['doc_type']
            # For the hackathon, we assume text files are stored directly in S3/DB.
            # Here we just route them.
            if doc_type not in parsed_data:
                parsed_data[doc_type] = []
            parsed_data[doc_type].append({"file_id": f["file_id"], "name": f["original_name"]})

        await self.log_step(case_id, payload["pipeline_run_id"], "FILES_MAPPED", {"count": len(files)})
        return {"mapped_files": parsed_data}
```

### Step 1.2 — Autopsy NLP Agent
**File: `services/agents/autopsy_agent.py`**

This agent takes the raw Autopsy Report text and forces Gemini Flash to extract a structured JSON representation of the injuries.

```python
from ..base_agent import BaseAgent
from ..llm_gateway import llm

SYSTEM_PROMPT = """
You are a forensic pathologist. Extract data from the provided autopsy report.
Return ONLY valid JSON matching this schema:
{
  "cause_of_death": "string",
  "time_indicators": ["list of strings"],
  "injuries": [{"type": "string", "location": "string", "severity": "string"}]
}
"""

class AutopsyAgent(BaseAgent):
    agent_id = "autopsy_agent"

    async def execute(self, case_id: str, payload: dict) -> dict:
        parser_data = await self.get_prior_result(case_id, "evidence_parser")
        
        # In a real scenario, you'd fetch the actual text from MinIO here.
        # We'll use mock text for the prompt to test the LLM.
        mock_autopsy_text = "The victim suffered a massive subdural hematoma due to blunt force trauma to the occipital region. Rigor mortis was fully established."
        
        await self.log_step(case_id, payload["pipeline_run_id"], "CALLING_LLM", {"model": "gemini-2.5-flash"})
        
        structured_data = await llm.complete_json(SYSTEM_PROMPT, mock_autopsy_text)
        
        await self.log_step(case_id, payload["pipeline_run_id"], "JSON_EXTRACTED", {"keys": list(structured_data.keys())})
        
        return structured_data
```

---

## 2. PHASE 7 — THE MACHINE LEARNING AGENTS (Hour 9:00–14:00)

This is where your RTX 3050 and `scikit-learn` come into play. Do NOT use Gemini for math or physics calculations.

### Step 2.1 — Time of Death (TOD) Agent
**File: `services/agents/tod_agent.py`**

Uses the Henssge Nomogram formula.

```python
from ..base_agent import BaseAgent
import math
from datetime import datetime, timedelta

class TODAgent(BaseAgent):
    agent_id = "tod_agent"

    async def execute(self, case_id: str, payload: dict) -> dict:
        # We need postmortem readings (body temp, ambient temp, weight).
        # We'll hardcode mock readings for the sprint if not found in DB.
        readings = {
            "body_temp": 31.2,
            "ambient_temp": 27.4,
            "weight": 68,
            "discovery_time": "2026-05-08T22:45:00Z" # UTC
        }
        
        await self.log_step(case_id, payload["pipeline_run_id"], "HENSSGE_CALC", {"readings": readings})
        
        T_body = readings["body_temp"]
        T_ambient = readings["ambient_temp"]
        T_death = 37.2 # Standard live body temp
        weight = readings["weight"]
        cf = 0.9 # Light clothing correction factor
        
        corrected_weight = weight * cf
        B = math.exp(0.0284 * corrected_weight) - 12.9
        
        # Double exponential decay formula
        numerator = math.log((T_body - T_ambient) / (T_death - T_ambient))
        denominator = math.log(B / (B + 1))
        
        hours_since_death = numerator / denominator
        
        discovery = datetime.fromisoformat(readings["discovery_time"].replace('Z', '+00:00'))
        estimated_tod = discovery - timedelta(hours=abs(hours_since_death))
        
        result = {
            "estimated_hours_since_death": round(abs(hours_since_death), 2),
            "estimated_tod_utc": estimated_tod.isoformat(),
            "margin_hours": 2.8, # Standard Henssge 95% CI margin
            "confidence": "HIGH" if T_body > T_ambient + 2 else "LOW"
        }
        
        await self.log_step(case_id, payload["pipeline_run_id"], "TOD_ESTIMATED", result)
        return result
```

### Step 2.2 — Timeline Anomaly Agent (Isolation Forest)
**File: `services/agents/timeline_anomaly.py`**

Uses `scikit-learn` on CPU. It is extremely fast and won't touch your GPU VRAM.

```python
from ..base_agent import BaseAgent
from sklearn.ensemble import IsolationForest
import numpy as np

class TimelineAnomalyAgent(BaseAgent):
    agent_id = "timeline_anomaly"

    async def execute(self, case_id: str, payload: dict) -> dict:
        # Fetch CDR (Call Data) and CCTV logs from DB. 
        # For the hackathon, we simulate an array of timestamps (unix epoch).
        
        # Simulated events: 5 normal events, 1 gap, then a burst of events
        mock_events = [
            {"time": 1000, "type": "cdr"},
            {"time": 1050, "type": "cctv"},
            {"time": 1100, "type": "cdr"},
            # HUGE SILENCE GAP HERE
            {"time": 5000, "type": "cctv"},
            {"time": 5010, "type": "cdr"},
            {"time": 5015, "type": "cctv"}
        ]
        
        await self.log_step(case_id, payload["pipeline_run_id"], "FEATURE_EXTRACTION", {"event_count": len(mock_events)})
        
        # Calculate time difference between consecutive events
        times = [e["time"] for e in mock_events]
        time_diffs = np.diff(times, prepend=times[0]).reshape(-1, 1)
        
        # Isolation Forest flags statistical outliers in the time gaps
        clf = IsolationForest(contamination=0.1, random_state=42)
        anomaly_scores = clf.fit_predict(time_diffs)
        raw_scores = clf.score_samples(time_diffs) # lower is more anomalous
        
        results = []
        for i, event in enumerate(mock_events):
            is_anomaly = bool(anomaly_scores[i] == -1)
            # Convert raw score (negative) to a 0-1 scale for Dev B's Recharts UI
            normalized_score = round(float(abs(raw_scores[i])), 2) 
            
            event["is_anomaly"] = is_anomaly
            event["anomaly_score"] = normalized_score
            results.append(event)
            
            if is_anomaly:
                await self.log_step(case_id, payload["pipeline_run_id"], "ANOMALY_FLAGGED", event)
                
        return {"scored_timeline": results}
```
