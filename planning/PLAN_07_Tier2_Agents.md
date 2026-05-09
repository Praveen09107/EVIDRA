# PLAN 07 — Tier 2 Agents (Domain Specific Analysis)
**Owner:** Dev A | **Hour:** 5:00–9:00 | **Priority:** CRITICAL

---

## 1. Objective
Implement the 4 domain-specific agents that analyze normalized text/images and output structured intelligence.
- **Autopsy Agent (M-04):** Extracts cause of death, injuries, temperature from autopsy reports via Gemini.
- **CDR Analyzer (M-05):** Parses Call Detail Records (CSV), finds anomalies and silence gaps.
- **Financial Analyzer (M-06):** Parses Bank Statements (CSV), finds unusual large transactions.
- **Image Agent (M-07):** Uses Gemini Multimodal to extract scene context from photos.

---

## 2. Autopsy Agent (M-04)

**File: `services/agents/autopsy_agent/agent.py`**

```python
from services.base_agent import BaseAgent, AgentTask, AgentResult
from services.llm_gateway import llm

PROMPT = """You are a forensic pathologist. Analyze this autopsy report and extract key details.
Return ONLY valid JSON:
{
  "manner_of_death": "HOMICIDE|SUICIDE|ACCIDENT|NATURAL|UNDETERMINED",
  "cause_of_death": "string",
  "injuries": [{"description": "string", "severity": "SEVERE|MODERATE|MINOR", "type": "BLUNT|SHARP|GUNSHOT|ASPHYXIA"}],
  "body_temperature_c": float or null,
  "ambient_temperature_c": float or null,
  "weight_kg": float or null,
  "livor_mortis": "FIXED|BLANCHING|NONE",
  "rigor_mortis": "FULL|PARTIAL|NONE",
  "gastric_emptying_hours": float or null
}
Report text:
{text}
"""

class AutopsyAgent(BaseAgent):
    agent_id = "autopsy_agent"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        norm_data = await self.get_prior_result(task, "format_normalizer")
        files = norm_data.get("normalized_files", []) if norm_data else []
        
        autopsy_text = ""
        for f in files:
            if f["doc_type"] == "AUTOPSY_REPORT":
                autopsy_text += f["normalized_text"] + "\n"
                
        if not autopsy_text:
            return AgentResult(data={}, warnings=["No AUTOPSY_REPORT text found."])
            
        self.log_step(task, "LLM_EXTRACTION", "Extracting autopsy variables", "Sending to Gemini 2.0 Flash", confidence=0.9)
        
        try:
            result = await llm.complete_json(self.agent_id, PROMPT.format(text=autopsy_text[:30000]))
            self.log_step(task, "MODEL_OUTPUT", "Extracted cause of death", 
                          f"Manner: {result.get('manner_of_death')}, Cause: {result.get('cause_of_death')}", confidence=0.85)
            return AgentResult(data={"extractions": result})
        except Exception as e:
            return AgentResult(data={}, warnings=[f"LLM Extraction failed: {str(e)}"])
```

---

## 3. CDR Analyzer (M-05)

**File: `services/agents/cdr_analyzer/agent.py`**

```python
import csv
import io
from datetime import datetime
from services.base_agent import BaseAgent, AgentTask, AgentResult
from services.database import db

class CDRAnalyzerAgent(BaseAgent):
    agent_id = "cdr_analyzer"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        norm_data = await self.get_prior_result(task, "format_normalizer")
        files = norm_data.get("normalized_files", []) if norm_data else []
        
        cdr_text = next((f["normalized_text"] for f in files if f["doc_type"] == "CDR"), None)
        if not cdr_text:
            return AgentResult(data={}, warnings=["No CDR data found."])
            
        self.log_step(task, "DATA_NORMALIZATION", "Parsing CDR CSV", "Extracting rows", confidence=1.0)
        
        # Simple CSV parsing
        events = []
        reader = csv.DictReader(io.StringIO(cdr_text))
        for row in reader:
            try:
                # Expecting: Date & Time, Call Type, Duration(Sec), Other Party, Cell ID, IMEI
                ts_str = row.get("Date & Time", row.get("timestamp", ""))
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                
                events.append({
                    "timestamp": dt.isoformat(),
                    "type": row.get("Call Type", "UNKNOWN"),
                    "duration": int(row.get("Duration(Sec)", 0)),
                    "contact": row.get("Other Party", ""),
                    "tower": row.get("Cell ID", "")
                })
            except Exception:
                continue
                
        # Sort by time
        events.sort(key=lambda x: x["timestamp"])
        
        # Analyze Silence gaps > 4 hours
        silence_gaps = []
        if len(events) > 1:
            for i in range(1, len(events)):
                t1 = datetime.fromisoformat(events[i-1]["timestamp"])
                t2 = datetime.fromisoformat(events[i]["timestamp"])
                diff = (t2 - t1).total_seconds() / 3600
                if diff > 4.0:
                    silence_gaps.append({"start": events[i-1]["timestamp"], "end": events[i]["timestamp"], "duration_hours": diff})
                    
        self.log_step(task, "ANOMALY_DETECTION", "Analyzed CDR", 
                      f"Found {len(events)} events, {len(silence_gaps)} silence gaps.", confidence=0.9)
                      
        return AgentResult(data={
            "total_events": len(events),
            "silence_gaps": silence_gaps,
            "events": events[:1000] # Cap output to save memory
        })
```

---

## 4. Financial Analyzer (M-06)

**File: `services/agents/financial_analyzer/agent.py`**

```python
import csv
import io
import numpy as np
from services.base_agent import BaseAgent, AgentTask, AgentResult

class FinancialAnalyzerAgent(BaseAgent):
    agent_id = "financial_analyzer"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        norm_data = await self.get_prior_result(task, "format_normalizer")
        files = norm_data.get("normalized_files", []) if norm_data else []
        
        fin_text = next((f["normalized_text"] for f in files if f["doc_type"] == "FINANCIAL_RECORDS"), None)
        if not fin_text:
            return AgentResult(data={}, warnings=["No FINANCIAL data found."])
            
        reader = csv.DictReader(io.StringIO(fin_text))
        transactions = []
        withdrawals = []
        
        for row in reader:
            try:
                # Expecting: Date, Narration, Withdrawal, Deposit, Balance
                w = float(row.get("Withdrawal", 0) or 0)
                d = float(row.get("Deposit", 0) or 0)
                txn = {
                    "date": row.get("Date", ""),
                    "narration": row.get("Narration", ""),
                    "withdrawal": w,
                    "deposit": d
                }
                transactions.append(txn)
                if w > 0:
                    withdrawals.append(w)
            except Exception:
                continue
                
        # Z-score anomaly detection for withdrawals
        anomalies = []
        if len(withdrawals) > 5:
            mean_w = np.mean(withdrawals)
            std_w = np.std(withdrawals)
            for t in transactions:
                if t["withdrawal"] > 0:
                    z = (t["withdrawal"] - mean_w) / (std_w + 1e-5)
                    if z > 2.5: # 2.5 std devs
                        anomalies.append(t)
                        
        self.log_step(task, "ANOMALY_DETECTION", "Analyzed Financials", 
                      f"Found {len(anomalies)} anomalous large withdrawals.", confidence=0.85)
                      
        return AgentResult(data={
            "total_transactions": len(transactions),
            "anomalies": anomalies
        })
```

---

## 5. Image Agent (M-07)

**File: `services/agents/image_agent/agent.py`**

```python
import base64
from services.base_agent import BaseAgent, AgentTask, AgentResult
from services.database import db
from services.minio_client import storage
from services.llm_gateway import llm

PROMPT = """Analyze this forensic image. Return ONLY valid JSON:
{
  "scene_type": "INDOOR|OUTDOOR|VEHICLE",
  "objects_detected": ["string"],
  "people_count": 0,
  "key_observations": ["string"]
}"""

class ImageAgent(BaseAgent):
    agent_id = "image_agent"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        files = await db.fetch("SELECT * FROM case_files WHERE case_id=$1 AND doc_type IN ('CCTV', 'DEVICE_DATA')", task.case_id)
        if not files:
            return AgentResult(data={}, warnings=["No image files found."])
            
        extractions = []
        for file in files:
            if "image" in str(file["mime_type"]):
                file_data = storage.download_file(file["s3_key"])
                b64 = base64.b64encode(file_data).decode("utf-8")
                
                self.log_step(task, "LLM_EXTRACTION", f"Analyzing image {file['original_name']}", "Sending to Gemini Multimodal", confidence=0.9)
                try:
                    res = await llm.complete_json(self.agent_id, PROMPT, image_b64=b64)
                    extractions.append({"file_id": str(file["file_id"]), "analysis": res})
                except Exception as e:
                    self.log_step(task, "ERROR", "Image analysis failed", str(e), confidence=0.0)
                    
        return AgentResult(data={"image_extractions": extractions})
```

## Acceptance Criteria
- [ ] Autopsy outputs strictly typed JSON based on prompt.
- [ ] CDR correctly calculates gaps between consecutive timestamps.
- [ ] Financial analyzer flags withdrawals > 2.5 std devs above mean.
- [ ] Image agent correctly passes base64 images to Gemini gateway.
