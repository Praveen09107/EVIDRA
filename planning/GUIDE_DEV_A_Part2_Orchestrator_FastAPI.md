# DEV A EXECUTION GUIDE — PART 2: BaseAgent Contract & FastAPI Gateway
**Role:** Backend Lead & ML Engineer
**Hours:** 3:00–6:00 | **Priority:** CRITICAL

---

## 1. PHASE 4 — THE BASE AGENT (Hour 3:00–4:30)

Every one of the 17 agents must inherit from `BaseAgent`. This is how you enforce the chain of custody. No agent is allowed to write directly to Postgres except through `self.log_step()`.

**File: `services/base_agent.py`**

```python
import json
import uuid
from typing import Dict, Any
from .database import db
from .redis_client import redis_client

class BaseAgent:
    agent_id: str = "base_agent"

    async def run(self, pipeline_run_id: str, case_id: str, payload: Dict[str, Any]):
        """The unbreakable lifecycle of an AIVENTRA agent."""
        
        # 1. Broadcast STARTED to Dev B's UI
        await redis_client.publish_ws_event(case_id, "AGENT_STARTED", {
            "agent_id": self.agent_id, 
            "pipeline_run_id": pipeline_run_id
        })

        try:
            # 2. Execute child agent logic
            result = await self.execute(case_id, payload)
            
            # 3. Store result in DB
            await db.execute(
                """
                INSERT INTO agent_results (case_id, agent_id, pipeline_run_id, output_data)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (case_id, agent_id) DO UPDATE SET output_data = $4
                """,
                case_id, self.agent_id, pipeline_run_id, json.dumps(result)
            )

            # 4. Broadcast COMPLETED to UI
            await redis_client.publish_ws_event(case_id, "AGENT_COMPLETED", {
                "agent_id": self.agent_id,
                "pipeline_run_id": pipeline_run_id,
                "duration_ms": 150  # Calculate real duration if time permits
            })

            # 5. Tell orchestrator to trigger dependents
            await redis_client.publish_task("orchestrator:eval", {
                "pipeline_run_id": pipeline_run_id,
                "case_id": case_id,
                "completed_agent": self.agent_id
            })

        except Exception as e:
            error_str = str(e)
            print(f"[{self.agent_id}] FAILED: {error_str}")
            await redis_client.publish_ws_event(case_id, "AGENT_FAILED", {
                "agent_id": self.agent_id,
                "error": error_str
            })
            # Log failure to DB
            await self.log_step(case_id, pipeline_run_id, "EXECUTION_FAILED", {"error": error_str})

    async def execute(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Child classes MUST override this."""
        raise NotImplementedError()

    async def log_step(self, case_id: str, pipeline_run_id: str, action: str, details: dict):
        """Mandatory Reasoning Replay Audit."""
        step_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO replay_steps (step_id, pipeline_run_id, case_id, agent_id, action, details)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            step_id, pipeline_run_id, case_id, self.agent_id, action, json.dumps(details)
        )

    async def get_prior_result(self, case_id: str, prior_agent_id: str) -> dict:
        """Helper to fetch data from an agent higher up in the DAG."""
        row = await db.fetch(
            "SELECT output_data FROM agent_results WHERE case_id = $1 AND agent_id = $2",
            case_id, prior_agent_id
        )
        return json.loads(row[0]['output_data']) if row else {}
```

---

## 2. PHASE 5 — FASTAPI GATEWAY (Hour 4:30–6:00)

Dev B needs these endpoints IMMEDIATELY to start building the frontend.
Do not worry about auth middleware for the 24hr sprint; just return dummy tokens for `/login` and accept everything.

**File: `services/gateway/main.py`**

```python
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import json
from ..database import db
from ..redis_client import redis_client

app = FastAPI(title="AIVENTRA API")

# VERY IMPORTANT FOR DEV B
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Next.js runs on 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.connect()
    await redis_client.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.close()

# --- AUTH & MFA (MOCK FOR SPRINT) ---
class LoginReq(BaseModel): email: str; password: str
class MFAReq(BaseModel): email: str; code: str

@app.post("/api/v1/auth/login")
async def login(req: LoginReq):
    # Returns partial auth token requesting MFA step
    return {"status": "MFA_REQUIRED", "temp_token": "mock-temp-token"}

@app.post("/api/v1/auth/mfa/verify")
async def verify_mfa(req: MFAReq):
    # In production, use pyotp to verify against stored secret
    if req.code == "123456": # Mock valid code
        return {"access_token": "mock-jwt-token-123", "role": "INVESTIGATOR"}
    return {"error": "Invalid code"}, 401

# --- CASES CRUD ---
class CaseCreate(BaseModel): title: str; description: str; location: str

@app.get("/api/v1/cases/")
async def list_cases():
    rows = await db.fetch("SELECT * FROM cases ORDER BY created_at DESC")
    return [dict(r) for r in rows]

@app.post("/api/v1/cases/")
async def create_case(case: CaseCreate):
    case_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO cases (case_id, case_number, title, description, location) VALUES ($1, $2, $3, $4, $5)",
        case_id, f"CASE-{case_id[:6].upper()}", case.title, case.description, case.location
    )
    return {"case_id": case_id}

@app.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str):
    case = await db.fetch("SELECT * FROM cases WHERE case_id = $1", case_id)
    files = await db.fetch("SELECT * FROM case_files WHERE case_id = $1", case_id)
    result = dict(case[0])
    result['files'] = [dict(f) for f in files]
    return result

# --- EVIDENCE UPLOAD ---
@app.post("/api/v1/cases/{case_id}/files")
async def upload_file(case_id: str, doc_type: str = Form(...), file: UploadFile = File(...)):
    # 1. Read file. WARNING: For huge CCTV files, stream this to MinIO instead.
    # For text/PDF/CSV, reading to memory is fine.
    content = await file.read()
    
    file_id = str(uuid.uuid4())
    
    # 2. In a real app, upload `content` to MinIO here and get an S3 URL.
    # For the sprint, if it's text, we can store it directly in Postgres for speed.
    s3_key = f"mock-s3-key/{file.filename}" 
    
    await db.execute(
        "INSERT INTO case_files (file_id, case_id, doc_type, original_name, s3_key) VALUES ($1, $2, $3, $4, $5)",
        file_id, case_id, doc_type, file.filename, s3_key
    )
    return {"file_id": file_id}

# --- TRIGGER ORCHESTRATOR ---
@app.post("/api/v1/cases/{case_id}/pipeline/trigger")
async def trigger_pipeline(case_id: str):
    run_id = str(uuid.uuid4())
    # Send the trigger to Orchestrator (Phase 1: Parsers)
    await redis_client.publish_task("orchestrator:trigger", {
        "pipeline_run_id": run_id,
        "case_id": case_id
    })
    return {"pipeline_run_id": run_id, "status": "AWAITING_REVIEW"}

@app.post("/api/v1/cases/{case_id}/pipeline/resume")
async def resume_pipeline(case_id: str):
    run_id = str(uuid.uuid4()) # Or pass existing run_id
    # Phase 2: Resume ML Agents after human verification
    await redis_client.publish_task("orchestrator:resume", {
        "pipeline_run_id": run_id,
        "case_id": case_id
    })
    return {"status": "ML_EXECUTION_STARTED"}

# --- WEBSOCKETS (CRITICAL FOR DEV B UI) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pubsub = redis_client.client.pubsub()
    await pubsub.subscribe("ui_telemetry")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        await pubsub.unsubscribe()
```

---
**SYNC POINT 1:** Push this code. Dev B can now build the entire UI shell.
