# CANONICAL SPEC 05 — Docker Compose, Security Scope & Agent Communication
**Status:** FINAL | Supersedes: Docker Compose Deployment Specification.txt (service list only)

---

## 1. Canonical Docker Compose Services

```yaml
version: "3.9"

x-common-env: &common-env
  POSTGRES_HOST: postgres
  POSTGRES_PORT: 5432
  POSTGRES_DB: aiventra
  POSTGRES_USER: aiventra
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  REDIS_URL: redis://redis:6379/0
  MINIO_ENDPOINT: minio:9000
  MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
  MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
  MINIO_BUCKET: aiventra-cases
  GEMINI_API_KEY: ${GEMINI_API_KEY}
  LLM_PROVIDER: gemini
  LOG_LEVEL: INFO
  ENVIRONMENT: production

services:

  # ─── INFRASTRUCTURE ───────────────────
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: aiventra
      POSTGRES_USER: aiventra
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aiventra"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --save 60 1 --loglevel warning
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  minio:
    image: minio/minio:latest
    restart: always
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9001:9001"

  # ─── GATEWAY & ORCHESTRATOR ───────────
  api_gateway:
    image: aiventra/gateway:latest
    restart: always
    environment:
      <<: *common-env
      PORT: 8000
      JWT_SECRET: ${JWT_SECRET}
      JWT_ALGORITHM: HS256
      JWT_EXPIRY_MINUTES: 480
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }
    deploy:
      replicas: 2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s

  orchestrator:
    image: aiventra/orchestrator:latest
    restart: always
    environment:
      <<: *common-env
      PORT: 8001
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 15s

  # ─── TIER 0-1: INGESTION ──────────────
  evidence_parser:
    image: aiventra/evidence-parser:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: evidence_parser
    depends_on: [postgres, redis, minio]
    deploy: { replicas: 2 }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s

  ocr_worker:
    image: aiventra/ocr:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: ocr
      TESSERACT_LANG: eng
    depends_on: [postgres, redis, minio]
    deploy: { replicas: 2 }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8011/health"]
      interval: 30s

  format_normalizer:
    image: aiventra/normalizer:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: format_normalizer
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8012/health"]
      interval: 30s

  # ─── TIER 2: DOMAIN ANALYSIS ──────────
  autopsy_agent:
    image: aiventra/autopsy:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: autopsy_agent
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
      interval: 30s

  cdr_analyzer:
    image: aiventra/cdr:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: cdr_analyzer
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8021/health"]
      interval: 30s

  financial_analyzer:
    image: aiventra/financial:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: financial_analyzer
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8022/health"]
      interval: 30s

  image_agent:
    image: aiventra/image:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: image_agent
      YOLO_MODEL_PATH: /models/yolov8n.pt
    volumes:
      - ./models:/models:ro
    depends_on: [postgres, redis, minio]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8023/health"]
      interval: 30s

  # ─── TIER 3: TEMPORAL INTELLIGENCE ────
  tod_agent:
    image: aiventra/tod:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: tod_agent
      TOD_ML_MODEL_PATH: /models/tod_rf_v2.pkl
    volumes:
      - ./models:/models:ro
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8030/health"]
      interval: 30s

  timeline_anomaly:
    image: aiventra/timeline:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: timeline_anomaly
      AUTOENCODER_MODEL_PATH: /models/timeline_ae_v1.pt
    volumes:
      - ./models:/models:ro
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8031/health"]
      interval: 30s

  collision_agent:
    image: aiventra/collision:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: collision_agent
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8032/health"]
      interval: 30s

  # ─── TIER 4: FUSION ───────────────────
  hotspot_engine:
    image: aiventra/hotspot:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: hotspot_engine
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8040/health"]
      interval: 30s

  claim_extractor:
    image: aiventra/claim-extractor:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: claim_extractor
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8041/health"]
      interval: 30s

  # ─── TIER 5: REASONING ────────────────
  evidence_claim_mapper:
    image: aiventra/ec-mapper:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: evidence_claim_mapper
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8050/health"]
      interval: 30s

  hypothesis_manager:
    image: aiventra/hypothesis:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: hypothesis_manager
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8051/health"]
      interval: 30s

  bias_uncertainty:
    image: aiventra/bias-monitor:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: bias_uncertainty
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8052/health"]
      interval: 30s

  # ─── TIER 6-7: GUIDANCE & AUDIT ───────
  nbe_agent:
    image: aiventra/nbe:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: nbe_agent
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8060/health"]
      interval: 30s

  reasoning_replay:
    image: aiventra/replay:latest
    restart: always
    environment:
      <<: *common-env
      AGENT_ID: reasoning_replay
    depends_on: [postgres, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8061/health"]
      interval: 30s

  # ─── FRONTEND ─────────────────────────
  frontend:
    image: aiventra/frontend:latest
    restart: always
    environment:
      NEXT_PUBLIC_API_BASE_URL: /api/v1
      NEXT_PUBLIC_WS_URL: /ws
    deploy: { replicas: 2 }

  # ─── REVERSE PROXY ────────────────────
  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on: [api_gateway, frontend]

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

**Total services: 22** (was 17, added: image_agent, collision_agent, hotspot_engine, claim_extractor, evidence_claim_mapper, bias_uncertainty, nbe_agent — and health checks on ALL agents)

---

## 2. Canonical Agent Communication Protocol (IMP-06 Resolution)

```
┌─────────────────────────────────────────────────────┐
│                  COMMUNICATION RULES                 │
├─────────────────────────────────────────────────────┤
│ Task dispatch:     Redis Streams                     │
│   Key pattern:     agent:{agent_id}:tasks            │
│   Payload:         {task_token, pipeline_run_id,     │
│                     case_id, task_id}                 │
│                                                      │
│ Result storage:    PostgreSQL (agent_results table)  │
│   Read by:         Downstream agents via DB query    │
│                                                      │
│ Completion signal: Redis Streams                     │
│   Key:             orchestrator:completions           │
│   Payload:         {task_id, pipeline_run_id,        │
│                     agent_id, success, error_code}   │
│                                                      │
│ UI events:         WebSocket (via Gateway)           │
│   Published by:    Orchestrator after state changes  │
│                                                      │
│ FORBIDDEN:         Direct agent-to-agent HTTP calls  │
│                    Agents reading other agent queues  │
└─────────────────────────────────────────────────────┘
```

---

## 3. Security Scope (GAP-04 Resolution — Phased)

### Phase 1 (Hackathon — Implement Now)
| Feature | Implementation |
|---------|---------------|
| Auth | JWT HS256 tokens, 8h expiry |
| Password | bcrypt hash via pgcrypto |
| RBAC | 4 roles: INVESTIGATOR, SUPERVISOR, ADMIN, READONLY |
| API auth | Bearer token in Authorization header |
| WS auth | Token in first message after connect |
| File integrity | SHA-256 checksum on upload, stored in case_files |
| Audit log | Append-only audit_log table with immutability trigger |
| PII masking | Format Normalizer strips names/phone/Aadhaar before DB storage |
| HTTPS | TLS termination at Nginx |

### Phase 2 (Post-Hackathon — Design Only)
| Feature | Notes |
|---------|-------|
| mTLS between services | Internal Docker network provides isolation for now |
| RS256 JWT | Switch from HS256 when deploying to production |
| PII Vault service | Dedicated service with mask/demask RBAC |
| RS256-signed replay steps | Non-repudiation for court submissions |
| SOC2 compliance audit | Full chain-of-custody with tamper-proof hashing |

### JWT Token Structure (Phase 1)
```python
JWT_PAYLOAD = {
    "sub": "<user_id>",
    "org": "<org_id>",
    "role": "INVESTIGATOR",
    "iat": 1715300000,
    "exp": 1715328800,  # 8h
    "jti": "<unique_token_id>"
}

# Task tokens (internal, short-lived)
TASK_TOKEN_PAYLOAD = {
    "sub": "orchestrator",
    "agent": "tod_agent",
    "case_id": "<case_id>",
    "pipeline_run_id": "<run_id>",
    "exp": 1715301200,  # 20 min
}
```

---

## 4. Canonical .env File

```bash
# ── Database ──
POSTGRES_PASSWORD=aiventra_db_strong_pw_2026

# ── Object Storage ──
MINIO_ACCESS_KEY=aiventra_minio
MINIO_SECRET_KEY=aiventra_minio_secret_2026

# ── LLM (Primary) ──
GEMINI_API_KEY=<your-gemini-key>
LLM_PROVIDER=gemini
LLM_MAX_TOKENS_PER_RUN=100000
LLM_RATE_LIMIT_RPM=60

# ── LLM (Fallback, optional) ──
DEEPSEEK_API_KEY=
OPENAI_API_KEY=

# ── Auth ──
JWT_SECRET=<64-char-random-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=480

# ── OCR (optional cloud fallback) ──
GOOGLE_VISION_KEY=

# ── App ──
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## 5. BaseAgent Contract (IMP-01 Resolution)

Every agent MUST implement this interface:

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Canonical agent interface. All 17 agents inherit from this."""
    
    agent_id: str
    version: str = "1.0.0"
    
    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Core execution logic. Returns structured result."""
        pass
    
    async def health_check(self) -> dict:
        """GET /health endpoint."""
        return {"agent_id": self.agent_id, "status": "healthy", "version": self.version}
    
    async def run(self, task: AgentTask) -> AgentResult:
        """Standard lifecycle wrapper — DO NOT OVERRIDE."""
        self._log_start(task)
        try:
            result = await self.execute(task)
            await self._store_result(task, result)
            await self._emit_replay_steps(task, result)
            await self._signal_completion(task, success=True)
            return result
        except NonRetryableError as e:
            await self._signal_completion(task, success=False, error_code="INVALID_DATA")
            raise
        except Exception as e:
            await self._signal_completion(task, success=False, error_code="RUNTIME_ERROR")
            raise

    async def _emit_replay_steps(self, task, result):
        """Every agent emits ReplaySteps for auditability."""
        for step in result.replay_steps:
            await db.insert("replay_steps", step.dict())
    
    async def _store_result(self, task, result):
        await db.insert("agent_results", {
            "pipeline_run_id": task.pipeline_run_id,
            "case_id": task.case_id,
            "agent_id": self.agent_id,
            "result_json": result.to_json()
        })
    
    async def _signal_completion(self, task, success, error_code=None):
        await redis.xadd("orchestrator:completions", {
            "task_id": str(task.task_id),
            "pipeline_run_id": str(task.pipeline_run_id),
            "agent_id": self.agent_id,
            "success": str(success),
            "error_code": error_code or ""
        })
```
