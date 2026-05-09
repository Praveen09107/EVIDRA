"""
EVIDRA — Redis Client (Streams + Pub/Sub).

Provides two communication patterns:
1. Redis Streams  → Durable task queues for agent dispatch (publish_task / consume_stream)
2. Redis Pub/Sub  → Real-time WebSocket events to the frontend (publish_ws_event)

Usage:
    from core.redis_client import get_redis, publish_task, publish_ws_event, close_redis

    # Dispatch an agent task via Redis Streams
    await publish_task("autopsy_agent", {"case_id": "...", "pipeline_run_id": "..."})

    # Send a real-time event to the frontend WebSocket
    await publish_ws_event(case_id, "AGENT_COMPLETED", {"agent_id": "tod_agent"})
"""
import json
import logging
import redis.asyncio as aioredis
from core.config import settings

logger = logging.getLogger("evidra.redis")

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the global Redis connection."""
    global _redis
    if _redis is None:
        logger.info(f"Connecting to Redis → {settings.REDIS_URL}")
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
        # Verify connection
        await _redis.ping()
        logger.info("Redis connected successfully")
    return _redis


async def close_redis():
    """Close the Redis connection gracefully."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


# ═══════════════════════════════════════════════════════════
# REDIS STREAMS — Durable Agent Task Dispatch
# ═══════════════════════════════════════════════════════════

async def publish_task(stream_name: str, payload: dict) -> str:
    """
    Publish a task to a Redis Stream.
    Used by the Orchestrator to dispatch agents and by agents to signal completion.

    Args:
        stream_name: e.g. "agent:autopsy_agent" or "orchestrator:completions"
        payload: dict with at minimum {"pipeline_run_id", "case_id", "agent_id"}

    Returns:
        The Redis stream message ID.
    """
    r = await get_redis()
    # Redis XADD requires all values to be strings
    str_payload = {k: str(v) for k, v in payload.items()}
    msg_id = await r.xadd(stream_name, str_payload)
    logger.debug(f"Published to {stream_name}: {msg_id}")
    return msg_id


async def consume_stream(stream_name: str, group_name: str, consumer_name: str,
                         count: int = 10, block_ms: int = 5000) -> list:
    """
    Consume messages from a Redis Stream using consumer groups.
    Creates the consumer group if it doesn't exist.

    Returns list of (message_id, data_dict) tuples.
    """
    r = await get_redis()

    # Create consumer group if not exists
    try:
        await r.xgroup_create(stream_name, group_name, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    results = await r.xreadgroup(
        groupname=group_name,
        consumername=consumer_name,
        streams={stream_name: ">"},
        count=count,
        block=block_ms
    )

    messages = []
    if results:
        for stream, msgs in results:
            for msg_id, data in msgs:
                messages.append((msg_id, data))

    return messages


async def ack_message(stream_name: str, group_name: str, message_id: str):
    """Acknowledge a processed message in a consumer group."""
    r = await get_redis()
    await r.xack(stream_name, group_name, message_id)


# ═══════════════════════════════════════════════════════════
# REDIS PUB/SUB — Real-Time WebSocket Events
# ═══════════════════════════════════════════════════════════

async def publish_ws_event(case_id: str, event_type: str, payload: dict):
    """
    Publish a real-time event to the WebSocket Pub/Sub channel.
    The WebSocket handler subscribes to "ws:case:*" and broadcasts to connected clients.

    Args:
        case_id:    The case this event belongs to.
        event_type: e.g. "AGENT_STARTED", "AGENT_COMPLETED", "PIPELINE_COMPLETED"
        payload:    Additional data to include.
    """
    r = await get_redis()
    message = json.dumps({
        "event": event_type,
        "case_id": case_id,
        "payload": payload
    })
    channel = f"ws:case:{case_id}"
    await r.publish(channel, message)
    logger.debug(f"WS event → {channel}: {event_type}")
