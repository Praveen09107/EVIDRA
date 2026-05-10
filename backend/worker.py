"""
EVIDRA — Async Agent Worker Daemon.

Listens to multiple Redis Streams concurrently (one per agent_id).
When a task is received, it instantiates the correct Agent class and calls `agent.run()`.

Run independently via: python -m worker
"""
import asyncio
import logging
from typing import Dict, Type

from core.database import db
from core.redis_client import get_redis, consume_stream, ack_message
from agents.base import BaseAgent

# ═══════════════════════════════════════════════════════════
# IMPORT ALL AGENTS
# ═══════════════════════════════════════════════════════════

# Tier 0 — Ingestion
from agents.parsers.evidence_parser import EvidenceParser
from agents.parsers.ocr_agent import OcrAgent

# Tier 1 — Normalization
from agents.parsers.format_normalizer import FormatNormalizer

# Tier 2 — Domain Agents
from agents.parsers.autopsy_agent import AutopsyAgent
from agents.parsers.cdr_analyzer import CdrAnalyzer
from agents.ml.financial_analyzer import FinancialAnalyzer

# Tier 3 — ML Ensembles
from agents.ml.tod_agent import TodAgent
from agents.ml.timeline_anomaly import TimelineAnomalyAgent

# Tier 4 — Fusion Layer 1
from agents.fusion.hotspot_engine import HotspotEngine
from agents.fusion.claim_extractor import ClaimExtractor

# Tier 5 — NLI Mapping + Graph
from agents.fusion.evidence_claim_mapper import EvidenceClaimMapper
from agents.fusion.graph_builder import ArgumentGraphBuilder

# Tier 6 — Bayesian & Bias
from agents.fusion.hypothesis_manager import HypothesisManager
from agents.fusion.bias_uncertainty import BiasUncertaintyAgent
from agents.fusion.gap_auditor import GapAuditor

# Tier 7 — Audit & Recommendations
from agents.fusion.nbe_agent import NbeAgent
from agents.fusion.reasoning_replay import ReasoningReplay


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evidra.worker")

# ═══════════════════════════════════════════════════════════
# AGENT CLASS REGISTRY
# ═══════════════════════════════════════════════════════════

AGENT_CLASSES: Dict[str, Type[BaseAgent]] = {
    # Tier 0
    "evidence_parser":       EvidenceParser,
    "ocr":                   OcrAgent,
    # Tier 1
    "format_normalizer":     FormatNormalizer,
    # Tier 2
    "autopsy_agent":         AutopsyAgent,
    "cdr_analyzer":          CdrAnalyzer,
    "financial_analyzer":    FinancialAnalyzer,
    # Tier 3
    "tod_agent":             TodAgent,
    "anomaly_detector":      TimelineAnomalyAgent,
    # Tier 4
    "hotspot_engine":        HotspotEngine,
    "claim_extractor":       ClaimExtractor,
    # Tier 5
    "evidence_claim_mapper": EvidenceClaimMapper,
    "graph_builder":         ArgumentGraphBuilder,
    # Tier 6
    "hypothesis_manager":    HypothesisManager,
    "bias_uncertainty":      BiasUncertaintyAgent,
    "gap_auditor":           GapAuditor,
    # Tier 7
    "nbe_agent":             NbeAgent,
    "reasoning_replay":      ReasoningReplay,
}

async def process_stream(agent_id: str, agent_class: Type[BaseAgent]):
    """Background task to continuously poll a specific agent's Redis stream."""
    stream_name = f"agent:{agent_id}"
    group_name = "worker_group"
    consumer_name = "worker_1"

    logger.info(f"Listening to stream: {stream_name}")

    while True:
        try:
            messages = await consume_stream(stream_name, group_name, consumer_name, count=5, block_ms=2000)

            for msg_id, task_data in messages:
                logger.info(f"Worker picked up {agent_id} task: {task_data['task_id']}")

                # Instantiate and run
                agent = agent_class()
                await agent.run(task_data)

                # ACK the message so it isn't processed again
                await ack_message(stream_name, group_name, msg_id)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error processing stream {stream_name}: {e}", exc_info=True)
            await asyncio.sleep(5)


async def worker_loop():
    """Main loop for the Worker Daemon."""
    logger.info(f"Starting Worker Daemon with {len(AGENT_CLASSES)} registered agents...")

    await db.get_pool()
    await get_redis()

    # Spawn an async task for every registered agent
    tasks = []
    for agent_id, agent_class in AGENT_CLASSES.items():
        t = asyncio.create_task(process_stream(agent_id, agent_class))
        tasks.append(t)
        logger.info(f"  ├── {agent_id}: {agent_class.__name__}")

    logger.info(f"  └── All {len(tasks)} agent streams active.")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
