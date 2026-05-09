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

# Import Agents as they are built
from agents.parsers.evidence_parser import EvidenceParser
from agents.parsers.format_normalizer import FormatNormalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evidra.worker")

# Registry linking agent_id to the Class implementation
AGENT_CLASSES: Dict[str, Type[BaseAgent]] = {
    "evidence_parser": EvidenceParser,
    "format_normalizer": FormatNormalizer,
    # Domain
    # "autopsy_agent": AutopsyAgent,
    # "cdr_analyzer": CdrAnalyzer,
    # "financial_analyzer": FinancialAnalyzer,
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
    logger.info("Starting Worker Daemon...")
    
    await db.get_pool()
    await get_redis()
    
    # Spawn an async task for every registered agent
    tasks = []
    for agent_id, agent_class in AGENT_CLASSES.items():
        t = asyncio.create_task(process_stream(agent_id, agent_class))
        tasks.append(t)
        
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
