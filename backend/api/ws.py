"""
EVIDRA — WebSocket Pub/Sub API.

Bridges Redis Pub/Sub directly to the Frontend WebSocket clients
for real-time pipeline visualization.
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.redis_client import get_redis

logger = logging.getLogger("evidra.ws")
router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/case/{case_id}")
async def case_websocket(websocket: WebSocket, case_id: str):
    """
    WebSocket endpoint for real-time case updates.
    Subscribes to Redis channel 'ws:case:{case_id}' and pipes messages to the client.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected to case {case_id}")

    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = f"ws:case:{case_id}"
    
    await pubsub.subscribe(channel)
    
    try:
        # Keep connection alive and listen to Redis
        while True:
            # We use a timeout to check if the client disconnected
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message:
                # Pipe Redis message directly to client
                await websocket.send_text(message["data"])
            
            # Allow FastAPI to process disconnects by occasionally yielding control
            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from case {case_id}")
    except Exception as e:
        logger.error(f"WebSocket error on case {case_id}: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
