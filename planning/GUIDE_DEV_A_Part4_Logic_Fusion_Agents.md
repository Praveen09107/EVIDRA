# DEV A EXECUTION GUIDE — PART 4: The Fusion Agents & Integration
**Role:** Backend Lead & ML Engineer
**Hours:** 14:00–22:00 | **Priority:** CRITICAL

---

## 1. PHASE 8 — THE REASONING FUSION AGENTS (Hour 14:00–18:00)

These are the Tier 5+ agents. They don't look at raw evidence; they look at the *outputs* of the previous agents (Autopsy, TOD, Timeline) and fuse them together using Gemini Flash.

### Step 1.1 — Hypothesis Manager
**File: `services/agents/hypothesis_manager.py`**

This agent outputs probabilities for the 5 standard manners of death based on the compiled evidence. Dev B needs this exact JSON structure for the XAI Studio.

```python
from ..base_agent import BaseAgent
from ..llm_gateway import llm

PROMPT = """
You are a forensic Bayesian integration engine.
Review the aggregated evidence outputs (Autopsy, TOD, Timeline Anomalies).
Assign a probability (0.0 to 1.0) to each of the 5 standard manners of death.
Identify the primary driver (reason) and the trend (UP, DOWN, STABLE).

Return EXACTLY this JSON format:
{
  "hypotheses": [
    {"key": "HOMICIDE", "prob": 0.8, "trend": "UP", "reason": "string"},
    {"key": "SUICIDE", "prob": 0.1, "trend": "DOWN", "reason": "string"},
    {"key": "ACCIDENT", "prob": 0.05, "trend": "STABLE", "reason": "string"},
    {"key": "NATURAL", "prob": 0.03, "trend": "STABLE", "reason": "string"},
    {"key": "UNDETERMINED", "prob": 0.02, "trend": "DOWN", "reason": "string"}
  ]
}
"""

class HypothesisManager(BaseAgent):
    agent_id = "hypothesis_manager"

    async def execute(self, case_id: str, payload: dict) -> dict:
        # Fetch prior results
        autopsy = await self.get_prior_result(case_id, "autopsy_agent")
        tod = await self.get_prior_result(case_id, "tod_agent")
        timeline = await self.get_prior_result(case_id, "timeline_anomaly")
        
        evidence_summary = f"Autopsy: {autopsy}\nTOD: {tod}\nAnomalies: {timeline}"
        
        await self.log_step(case_id, payload["pipeline_run_id"], "EVIDENCE_FUSION", {"bytes": len(evidence_summary)})
        
        result = await llm.complete_json(PROMPT, evidence_summary)
        
        await self.log_step(case_id, payload["pipeline_run_id"], "BAYESIAN_UPDATE_COMPLETE", {"top_hypothesis": result["hypotheses"][0]["key"]})
        
        return result
```

### Step 1.2 — Reasoning Replay Agent
**File: `services/agents/reasoning_replay.py`**

This is the final agent in the DAG. It gathers all the `log_step` entries from Postgres and generates a human-readable chain of custody audit trail.

```python
from ..base_agent import BaseAgent
from ..database import db

class ReasoningReplayAgent(BaseAgent):
    agent_id = "reasoning_replay"

    async def execute(self, case_id: str, payload: dict) -> dict:
        run_id = payload["pipeline_run_id"]
        
        await self.log_step(case_id, run_id, "COMPILING_AUDIT", {"status": "started"})
        
        # Fetch every single step logged during this pipeline run
        steps = await db.fetch(
            "SELECT agent_id, action, details, timestamp FROM replay_steps WHERE pipeline_run_id = $1 ORDER BY timestamp ASC",
            run_id
        )
        
        audit_trail = []
        for step in steps:
            audit_trail.append({
                "agent": step["agent_id"],
                "action": step["action"],
                "details": step["details"],
                "time": step["timestamp"].isoformat()
            })
            
        await self.log_step(case_id, run_id, "AUDIT_COMPILED", {"total_steps": len(audit_trail)})
        
        return {"audit_trail": audit_trail}
```

---

## 2. PHASE 9 — THE WORKER RUNNER (Hour 18:00–20:00)

You need a way to run all 17 agents in the background. In production, these might be 17 separate servers. For this hackathon, we use a single asyncio worker script.

**File: `services/worker.py`**

```python
import asyncio
import json
from .database import db
from .redis_client import redis_client

# Import your agents
from .agents.evidence_parser import EvidenceParserAgent
from .agents.autopsy_agent import AutopsyAgent
from .agents.tod_agent import TODAgent
from .agents.timeline_anomaly import TimelineAnomalyAgent
from .agents.hypothesis_manager import HypothesisManager
from .agents.reasoning_replay import ReasoningReplayAgent

AGENTS = {
    "evidence_parser": EvidenceParserAgent(),
    "autopsy_agent": AutopsyAgent(),
    "tod_agent": TODAgent(),
    "timeline_anomaly": TimelineAnomalyAgent(),
    "hypothesis_manager": HypothesisManager(),
    "reasoning_replay": ReasoningReplayAgent()
}

async def process_stream(agent_id: str, agent_instance):
    """Continuously polls Redis for tasks for a specific agent."""
    stream_name = f"agent:{agent_id}:tasks"
    group_name = "worker_group"
    consumer_name = f"worker_{agent_id}_1"
    
    print(f"[{agent_id}] Listening for tasks...")
    
    while True:
        try:
            # Block for 5 seconds waiting for a task
            response = await redis_client.read_tasks(stream_name, group_name, consumer_name)
            
            if response:
                for stream, messages in response:
                    for message_id, message_data in messages:
                        payload = json.loads(message_data["payload"])
                        print(f"[{agent_id}] Received task for Case {payload['case_id']}")
                        
                        # Execute the agent
                        await agent_instance.run(payload["pipeline_run_id"], payload["case_id"], payload)
                        
                        # Acknowledge the task so it's removed from queue
                        await redis_client.ack_task(stream_name, group_name, message_id)
            
            await asyncio.sleep(0.1) # Prevent CPU pegging
            
        except Exception as e:
            print(f"[{agent_id}] Worker Error: {str(e)}")
            await asyncio.sleep(2)

async def main():
    await db.connect()
    await redis_client.connect()
    
    tasks = []
    for agent_id, instance in AGENTS.items():
        tasks.append(asyncio.create_task(process_stream(agent_id, instance)))
        
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. HOW TO TEST YOUR ENTIRE BACKEND

You now have the API, the Orchestrator, and the Worker.

**Terminal 1:**
```powershell
docker compose up -d
```

**Terminal 2:**
```powershell
uvicorn services.gateway.main:app --reload --port 8000
```

**Terminal 3:**
```powershell
python -m services.worker
```

1. Open `http://localhost:8000/docs` in your browser (FastAPI Swagger).
2. Hit the `POST /api/v1/cases/` endpoint to create a dummy case.
3. Hit the `POST /api/v1/cases/{case_id}/pipeline/trigger` endpoint.
4. Watch Terminal 3. You should see all your agents executing in order, picking up tasks from Redis, and completing them.
5. If you see `[autopsy_agent] Received task`, the pipeline is working.
