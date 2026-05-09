# DEV A EXECUTION GUIDE — PART 1: Infrastructure, DB, & LLM Gateway
**Role:** Backend Lead & ML Engineer
**Hours:** 0:00–3:00 | **Priority:** CRITICAL

---

## 1. PHASE 1 — THE DOCKER FOUNDATION (Hour 0:00–0:30)

Your first task is to bring the persistence layer online. Without Postgres, Redis, and MinIO, nothing else works.

### Step 1.1 — docker-compose.yml
**File: `docker-compose.yml`** (in project root)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: aiventra_user
      POSTGRES_PASSWORD: aiventra_password
      POSTGRES_DB: aiventra_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password123
    command: server /data --console-address ":9001"
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  redisdata:
  miniodata:
```

*Run `docker compose up -d`.*

### Step 1.2 — Database Connection Pool
**File: `services/database.py`**

Do NOT use psycopg2. You must use `asyncpg` for non-blocking FastAPI performance.

```python
import asyncpg
import os
from typing import Optional

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.dsn = os.getenv(
            "DATABASE_URL", 
            "postgresql://aiventra_user:aiventra_password@localhost:5432/aiventra_db"
        )

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=5, max_size=20)
            print("[DB] AsyncPG Pool Initialized")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

db = Database()
```

---

## 2. PHASE 2 — THE LLM GATEWAY (Hour 0:30–2:00)

Every agent uses Gemini Flash. If 17 agents hit the API at the exact same millisecond, you will get a `429 Too Many Requests` error. The LLM Gateway is a singleton that prevents this using semaphores and exponential backoff.

**File: `services/llm_gateway.py`**

```python
import os
import json
import asyncio
from typing import Dict, Any
from google import genai
from google.genai import types

class LLMGateway:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # Strict concurrency limit for the hackathon
        self.semaphore = asyncio.Semaphore(5)

    async def complete_json(self, system_prompt: str, user_prompt: str, retries=3) -> Dict[str, Any]:
        """
        Forces Gemini 2.0 Flash to return strict JSON.
        Handles rate limits, json-stripping, and exponential backoff.
        """
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    # Run sync SDK call in async executor thread to not block FastAPI
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model='gemini-2.5-flash',
                        contents=f"{system_prompt}\n\n{user_prompt}",
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                        )
                    )
                    
                    raw_text = response.text.strip()
                    
                    # Strip markdown fences if Gemini ignored the mime_type instruction
                    if raw_text.startswith("```"):
                        raw_text = raw_text.split("```")[1]
                        if raw_text.startswith("json"):
                            raw_text = raw_text[4:]
                    
                    return json.loads(raw_text.strip())

                except Exception as e:
                    print(f"[LLM] Error (Attempt {attempt+1}/{retries}): {str(e)}")
                    if attempt == retries - 1:
                        raise e
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

llm = LLMGateway()
```

---

## 3. PHASE 3 — REDIS STREAMS & PUB/SUB (Hour 2:00–3:00)

We use Redis for two different things:
1. **Streams (`XADD`/`XREAD`):** For queuing tasks to agents.
2. **Pub/Sub (`PUBLISH`):** For blasting live status updates to Dev B's WebSockets.

**File: `services/redis_client.py`**

```python
import redis.asyncio as redis
import os
import json

class RedisManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = None

    async def connect(self):
        if not self.client:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            print("[REDIS] Connected")

    # --- AGENT TASK QUEUES (STREAMS) ---
    async def publish_task(self, stream_name: str, payload: dict):
        """Used by Orchestrator to dispatch a task to an agent."""
        await self.client.xadd(stream_name, {"payload": json.dumps(payload)})

    async def read_tasks(self, stream_name: str, group_name: str, consumer_name: str):
        """Used by Agent Workers to pull tasks."""
        try:
            await self.client.xgroup_create(stream_name, group_name, id='0', mkstream=True)
        except redis.exceptions.ResponseError:
            pass # Group already exists
            
        return await self.client.xreadgroup(group_name, consumer_name, {stream_name: '>'}, count=1, block=5000)

    async def ack_task(self, stream_name: str, group_name: str, task_id: str):
        """Used by Agent Workers to mark task as complete."""
        await self.client.xack(stream_name, group_name, task_id)

    # --- UI WEBSOCKET UPDATES (PUB/SUB) ---
    async def publish_ws_event(self, case_id: str, event_type: str, data: dict):
        """Fires live updates to the frontend."""
        msg = {"case_id": case_id, "event": event_type, "data": data}
        await self.client.publish("ui_telemetry", json.dumps(msg))

redis_client = RedisManager()
```
