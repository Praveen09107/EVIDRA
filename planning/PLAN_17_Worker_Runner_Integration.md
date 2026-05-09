# PLAN 17 — Worker Runner & Pipeline Integration
**Owner:** Dev A | **Hour:** 20:00–21:00 | **Priority:** CRITICAL

---

## 1. Objective
Create a unified worker process script that can run any combination of the 17 agents by listening to their respective Redis Streams. This avoids the overhead of managing 17 separate terminal windows during development.

---

## 2. Unified Worker Script

**File: `services/worker.py`**

```python
"""
Unified Agent Worker Runner.
Usage:
  python -m services.worker --all
  python -m services.worker autopsy_agent cdr_analyzer
"""
import asyncio
import sys
import logging
from uuid import UUID
from services.database import db
from services.redis_client import get_redis
from services.base_agent import AgentTask

# Import all agents
from services.agents.evidence_parser.agent import EvidenceParserAgent
from services.agents.ocr.agent import OCRAgent
from services.agents.format_normalizer.agent import FormatNormalizerAgent
from services.agents.autopsy_agent.agent import AutopsyAgent
from services.agents.cdr_analyzer.agent import CDRAnalyzerAgent
from services.agents.financial_analyzer.agent import FinancialAnalyzerAgent
from services.agents.image_agent.agent import ImageAgent
from services.agents.tod_agent.agent import TODAgent
from services.agents.timeline_anomaly.agent import TimelineAnomalyAgent
from services.agents.collision_agent.agent import CollisionAgent
from services.agents.hotspot_engine.agent import HotspotEngine
from services.agents.claim_extractor.agent import ClaimExtractorAgent
from services.agents.evidence_claim_mapper.agent import EvidenceClaimMapperAgent
from services.agents.hypothesis_manager.agent import HypothesisManagerAgent
from services.agents.bias_uncertainty.agent import BiasUncertaintyAgent
from services.agents.nbe_agent.agent import NBEAgent
from services.agents.reasoning_replay.agent import ReasoningReplayAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")

AGENT_REGISTRY = {
    "evidence_parser": EvidenceParserAgent,
    "ocr": OCRAgent,
    "format_normalizer": FormatNormalizerAgent,
    "autopsy_agent": AutopsyAgent,
    "cdr_analyzer": CDRAnalyzerAgent,
    "financial_analyzer": FinancialAnalyzerAgent,
    "image_agent": ImageAgent,
    "tod_agent": TODAgent,
    "timeline_anomaly": TimelineAnomalyAgent,
    "collision_agent": CollisionAgent,
    "hotspot_engine": HotspotEngine,
    "claim_extractor": ClaimExtractorAgent,
    "evidence_claim_mapper": EvidenceClaimMapperAgent,
    "hypothesis_manager": HypothesisManagerAgent,
    "bias_uncertainty": BiasUncertaintyAgent,
    "nbe_agent": NBEAgent,
    "reasoning_replay": ReasoningReplayAgent,
}

async def worker_loop(agent_id: str):
    """Listen on Redis stream and run agent when task arrives."""
    agent_class = AGENT_REGISTRY[agent_id]
    agent = agent_class()
    r = await get_redis()
    stream_key = f"agent:{agent_id}:tasks"
    last_id = "0-0"
    
    logger.info(f"Worker [{agent_id}] ready. Listening on {stream_key}")
    
    while True:
        try:
            results = await r.xread({stream_key: last_id}, count=1, block=5000)
            if not results:
                continue
            
            for stream, messages in results:
                for msg_id, data in messages:
                    last_id = msg_id
                    
                    task = AgentTask(
                        task_id=UUID(data["task_id"]),
                        pipeline_run_id=UUID(data["pipeline_run_id"]),
                        case_id=UUID(data["case_id"]),
                        agent_id=data["agent_id"],
                        attempt=int(data.get("attempt", 1))
                    )
                    
                    # Execute base agent lifecycle
                    await agent.run(task)
                    
        except Exception as e:
            logger.error(f"Worker [{agent_id}] stream error: {e}")
            await asyncio.sleep(2)

async def main(agent_ids: list):
    await db.get_pool()
    logger.info(f"Starting {len(agent_ids)} agent workers...")
    
    tasks = [worker_loop(aid) for aid in agent_ids]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--all" in args:
        agent_ids = list(AGENT_REGISTRY.keys())
    elif args:
        agent_ids = [a for a in args if a in AGENT_REGISTRY]
    else:
        print("Usage: python -m services.worker [--all | agent_id1 agent_id2 ...]")
        sys.exit(1)
        
    asyncio.run(main(agent_ids))
```

## Acceptance Criteria
- [ ] `python -m services.worker --all` successfully imports all 17 agents without syntax errors.
- [ ] Workers successfully pull messages from Redis and invoke `agent.run()`.
