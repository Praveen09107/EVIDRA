"""
EVIDRA — Orchestrator Daemon Loop.

Listens to Redis streams for:
1. orchestrator:trigger -> Initialize DAG and start Tier 0
2. orchestrator:completions -> Evaluate DAG and dispatch downstream agents

Run independently via: python -m orchestrator.main
"""
import asyncio
import logging
from uuid import UUID

from core.database import db
from core.redis_client import get_redis, consume_stream, ack_message
from orchestrator.dispatcher import create_pipeline_run, dispatch_ready_agents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evidra.orchestrator.daemon")

async def orchestrator_loop():
    """Main loop for the Orchestrator Daemon."""
    logger.info("Starting Orchestrator Daemon...")
    
    # Ensure connections
    await db.get_pool()
    await get_redis()
    
    while True:
        try:
            # 1. Check for new triggers (API -> Orchestrator)
            trigger_msgs = await consume_stream(
                "orchestrator:trigger", "orch_group", "orch_worker", count=10, block_ms=1000
            )
            for msg_id, data in trigger_msgs:
                case_id = UUID(data["case_id"])
                run_id = UUID(data["pipeline_run_id"])
                logger.info(f"Received trigger for run {run_id}")
                
                await create_pipeline_run(case_id, run_id)
                await dispatch_ready_agents(run_id, case_id)
                await ack_message("orchestrator:trigger", "orch_group", msg_id)
            
            # 2. Check for agent completions (Worker -> Orchestrator)
            comp_msgs = await consume_stream(
                "orchestrator:completions", "orch_group", "orch_worker", count=20, block_ms=1000
            )
            for msg_id, data in comp_msgs:
                case_id = UUID(data["case_id"])
                run_id = UUID(data["pipeline_run_id"])
                agent_id = data["agent_id"]
                status = data["status"]
                
                logger.info(f"Agent {agent_id} completed with status {status}")
                await dispatch_ready_agents(run_id, case_id)
                await ack_message("orchestrator:completions", "orch_group", msg_id)

            await asyncio.sleep(0.1)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            await asyncio.sleep(5) # Backoff on error
            
    logger.info("Shutting down Orchestrator Daemon...")

if __name__ == "__main__":
    try:
        asyncio.run(orchestrator_loop())
    except KeyboardInterrupt:
        pass
