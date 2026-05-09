# PLAN 02B — Redis Client, MinIO Client & Config Module
**Owner:** Dev A | **Hour:** 1:00–1:30 | **Priority:** CRITICAL

---

## 1. Objective
Create the Redis async client (for agent task streams), MinIO S3 client (for evidence file storage), and the central config module that loads and validates all `.env` variables. These three modules are imported by every service.

---

## 2. Config Module

**File: `services/config.py`**

```python
"""
Central configuration loader.
Reads .env file and provides typed access to all settings.
Every other module imports from here — never reads os.environ directly.

Usage:
    from services.config import settings
    print(settings.DATABASE_URL)
    print(settings.JWT_SECRET)
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

def _env(key: str, default: str = None, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val

def _env_int(key: str, default: int = 0) -> int:
    return int(os.getenv(key, str(default)))

def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")

def _env_float(key: str, default: float = 0.0) -> float:
    return float(os.getenv(key, str(default)))

@dataclass(frozen=True)
class Settings:
    # Database
    DATABASE_URL: str = field(default_factory=lambda: _env("DATABASE_URL", required=True))
    DB_MIN_POOL: int = field(default_factory=lambda: _env_int("DB_MIN_POOL", 2))
    DB_MAX_POOL: int = field(default_factory=lambda: _env_int("DB_MAX_POOL", 10))

    # Redis
    REDIS_URL: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))

    # MinIO
    MINIO_ENDPOINT: str = field(default_factory=lambda: _env("MINIO_ENDPOINT", "localhost:9000"))
    MINIO_ACCESS_KEY: str = field(default_factory=lambda: _env("MINIO_ACCESS_KEY", "aiventra_minio"))
    MINIO_SECRET_KEY: str = field(default_factory=lambda: _env("MINIO_SECRET_KEY", "aiventra_minio_2026"))
    MINIO_BUCKET: str = field(default_factory=lambda: _env("MINIO_BUCKET", "aiventra-evidence"))
    MINIO_SECURE: bool = field(default_factory=lambda: _env_bool("MINIO_SECURE", False))

    # LLM
    GEMINI_API_KEY: str = field(default_factory=lambda: _env("GEMINI_API_KEY", required=True))
    LLM_MODEL: str = field(default_factory=lambda: _env("LLM_MODEL", "gemini-2.0-flash"))
    LLM_MAX_RETRIES: int = field(default_factory=lambda: _env_int("LLM_MAX_RETRIES", 3))
    LLM_TIMEOUT_SECONDS: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT_SECONDS", 60))
    LLM_RATE_LIMIT_RPM: int = field(default_factory=lambda: _env_int("LLM_RATE_LIMIT_RPM", 15))

    # Auth
    JWT_SECRET: str = field(default_factory=lambda: _env("JWT_SECRET", required=True))
    JWT_ALGORITHM: str = field(default_factory=lambda: _env("JWT_ALGORITHM", "HS256"))
    JWT_EXPIRE_MINUTES: int = field(default_factory=lambda: _env_int("JWT_EXPIRE_MINUTES", 480))

    # App
    APP_ENV: str = field(default_factory=lambda: _env("APP_ENV", "development"))
    LOG_LEVEL: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    API_PORT: int = field(default_factory=lambda: _env_int("API_PORT", 8000))
    FRONTEND_URL: str = field(default_factory=lambda: _env("FRONTEND_URL", "http://localhost:3000"))

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"

# Singleton — import this everywhere
settings = Settings()
```

---

## 3. Redis Client Module

**File: `services/redis_client.py`**

```python
"""
Async Redis client for agent task streams and pub/sub.

Redis Streams usage in AIVENTRA:
- Agent tasks dispatched via XADD to "agent:{agent_id}:tasks"
- Workers consume via XREAD (blocking)
- Orchestrator listens on "orchestrator:completions" for agent done signals
- Pipeline status cached in "pipeline:{run_id}:status" (hash)

Usage:
    from services.redis_client import get_redis, publish_task, notify_completion
    
    r = await get_redis()
    await publish_task("autopsy_agent", {"task_id": "...", "case_id": "..."})
    await notify_completion("autopsy_agent", pipeline_run_id, "COMPLETE")
"""
import json
import redis.asyncio as aioredis
from services.config import settings

_redis_client = None

async def get_redis() -> aioredis.Redis:
    """Get or create the global async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
        # Verify connection
        await _redis_client.ping()
    return _redis_client

async def close_redis():
    """Close the Redis connection gracefully."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None

async def publish_task(agent_id: str, task_data: dict) -> str:
    """
    Dispatch a task to an agent's Redis stream.
    
    Args:
        agent_id: Target agent identifier (e.g., "autopsy_agent")
        task_data: Must contain task_id, pipeline_run_id, case_id, agent_id
    
    Returns:
        Redis message ID (e.g., "1234567890-0")
    
    Example:
        msg_id = await publish_task("autopsy_agent", {
            "task_id": str(task_id),
            "pipeline_run_id": str(run_id),
            "case_id": str(case_id),
            "agent_id": "autopsy_agent"
        })
    """
    r = await get_redis()
    stream_key = f"agent:{agent_id}:tasks"
    # Flatten dict to string values for Redis streams
    flat_data = {k: str(v) for k, v in task_data.items()}
    msg_id = await r.xadd(stream_key, flat_data)
    return msg_id

async def notify_completion(agent_id: str, pipeline_run_id: str, status: str, error: str = None):
    """
    Notify the orchestrator that an agent has finished.
    Orchestrator listens on "orchestrator:completions" stream.
    
    Args:
        agent_id: Which agent completed
        pipeline_run_id: Which pipeline run this belongs to
        status: "COMPLETE" or "FAILED"
        error: Error message if FAILED
    """
    r = await get_redis()
    data = {
        "agent_id": agent_id,
        "pipeline_run_id": pipeline_run_id,
        "status": status,
    }
    if error:
        data["error"] = error
    await r.xadd("orchestrator:completions", data)

async def set_pipeline_status(pipeline_run_id: str, status_data: dict):
    """Cache pipeline status for quick UI reads."""
    r = await get_redis()
    key = f"pipeline:{pipeline_run_id}:status"
    await r.hset(key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in status_data.items()})
    await r.expire(key, 3600)  # 1h TTL

async def get_pipeline_status(pipeline_run_id: str) -> dict:
    """Get cached pipeline status."""
    r = await get_redis()
    key = f"pipeline:{pipeline_run_id}:status"
    data = await r.hgetall(key)
    return data or {}

async def publish_ws_event(case_id: str, event_type: str, data: dict):
    """Publish event for WebSocket distribution to connected clients."""
    r = await get_redis()
    msg = json.dumps({"case_id": case_id, "event": event_type, "data": data})
    await r.publish(f"ws:case:{case_id}", msg)
```

---

## 4. MinIO Client Module

**File: `services/minio_client.py`**

```python
"""
MinIO (S3-compatible) client for evidence file storage.

All uploaded evidence files are stored in MinIO with keys:
    cases/{case_id}/evidence/{file_id}/{original_filename}

Usage:
    from services.minio_client import storage
    
    # Upload
    s3_key = await storage.upload_file(case_id, file_id, filename, file_bytes)
    
    # Download
    data = await storage.download_file(s3_key)
    
    # List
    files = await storage.list_files(case_id)
"""
import io
from minio import Minio
from services.config import settings

class StorageClient:
    def __init__(self):
        self._client = None
    
    def _get_client(self) -> Minio:
        """Lazy-initialize the MinIO client."""
        if self._client is None:
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            # Ensure bucket exists
            if not self._client.bucket_exists(settings.MINIO_BUCKET):
                self._client.make_bucket(settings.MINIO_BUCKET)
        return self._client
    
    def upload_file(self, case_id: str, file_id: str, filename: str, 
                    data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Upload a file to MinIO.
        
        Args:
            case_id: UUID string of the case
            file_id: UUID string of the file record
            filename: Original filename (sanitized)
            data: Raw file bytes
            content_type: MIME type
        
        Returns:
            S3 key string for future reference
        """
        client = self._get_client()
        # Sanitize filename
        safe_name = filename.replace(" ", "_").replace("/", "_")
        s3_key = f"cases/{case_id}/evidence/{file_id}/{safe_name}"
        
        client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=s3_key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return s3_key
    
    def download_file(self, s3_key: str) -> bytes:
        """
        Download a file from MinIO.
        
        Args:
            s3_key: The full S3 key path
        
        Returns:
            Raw file bytes
        """
        client = self._get_client()
        response = client.get_object(settings.MINIO_BUCKET, s3_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    
    def delete_file(self, s3_key: str):
        """Delete a file from MinIO."""
        client = self._get_client()
        client.remove_object(settings.MINIO_BUCKET, s3_key)
    
    def list_files(self, case_id: str) -> list:
        """List all evidence files for a case."""
        client = self._get_client()
        prefix = f"cases/{case_id}/evidence/"
        objects = client.list_objects(settings.MINIO_BUCKET, prefix=prefix, recursive=True)
        return [{"key": obj.object_name, "size": obj.size, "modified": obj.last_modified} for obj in objects]
    
    def get_presigned_url(self, s3_key: str, expires_hours: int = 1) -> str:
        """Generate a temporary download URL."""
        from datetime import timedelta
        client = self._get_client()
        return client.presigned_get_object(
            settings.MINIO_BUCKET, s3_key, expires=timedelta(hours=expires_hours)
        )

# Singleton instance
storage = StorageClient()
```

---

## 5. Verification Steps

```python
# Test config:
python -c "from services.config import settings; print(f'ENV={settings.APP_ENV}, DB={settings.DATABASE_URL[:30]}...')"

# Test Redis:
python -c "
import asyncio
from services.redis_client import get_redis
async def test():
    r = await get_redis()
    await r.set('test_key', 'hello_aiventra')
    val = await r.get('test_key')
    print(f'Redis OK: {val}')
    await r.delete('test_key')
asyncio.run(test())
"

# Test MinIO:
python -c "
from services.minio_client import storage
storage.upload_file('test-case', 'test-file', 'hello.txt', b'Hello AIVENTRA')
data = storage.download_file('cases/test-case/evidence/test-file/hello.txt')
print(f'MinIO OK: {data.decode()}')
storage.delete_file('cases/test-case/evidence/test-file/hello.txt')
"
```

---

## 6. Acceptance Criteria
- [ ] `from services.config import settings` loads all env vars without error
- [ ] `settings.is_dev` returns `True` in development
- [ ] Missing required vars raise `EnvironmentError` with clear message
- [ ] Redis `ping()` returns `True`
- [ ] `publish_task` adds a message to a Redis stream and returns message ID
- [ ] `notify_completion` writes to `orchestrator:completions` stream
- [ ] MinIO bucket `aiventra-evidence` auto-created if not exists
- [ ] Upload → download round-trip returns identical bytes
- [ ] `list_files` returns objects with key, size, modified
