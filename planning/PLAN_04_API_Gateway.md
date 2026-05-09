# PLAN 04 — API Gateway (FastAPI, Auth, Cases, WebSockets)
**Owner:** Dev A | **Hour:** 2:00–3:00 | **Priority:** CRITICAL

---

## 1. Objective
Build the FastAPI entry point for the frontend. This includes JWT authentication, Case CRUD, Evidence file upload to MinIO, Pipeline triggering, and real-time WebSocket telemetry.

---

## 2. Main App Factory & Config

**File: `services/gateway/main.py`**

```python
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from services.database import db
from services.redis_client import get_redis, close_redis
from services.config import settings

from services.gateway.auth import router as auth_router
from services.gateway.cases import router as cases_router
from services.gateway.pipeline import router as pipeline_router
from services.gateway.analysis import router as analysis_router
from services.gateway.websocket import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connection pools
    await db.get_pool()
    await get_redis()
    yield
    # Shutdown: Close connection pools
    await db.close_pool()
    await close_redis()

app = FastAPI(
    title="AIVENTRA API Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(cases_router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(pipeline_router, prefix="/api/v1/cases", tags=["Pipeline"])
app.include_router(analysis_router, prefix="/api/v1/cases", tags=["Analysis"])
app.include_router(ws_router, tags=["WebSockets"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
```

---

## 3. JWT Authentication

**File: `services/gateway/auth.py`**

```python
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
import passlib.hash
from services.database import db
from services.config import settings

router = APIRouter()
pwd_context = passlib.hash.bcrypt

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

@router.post("/login")
async def login(req: LoginRequest):
    user = await db.fetchrow("SELECT * FROM users WHERE email=$1", req.email)
    if not user or not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(user["user_id"]), "role": user["role"]})
    return {"access_token": token, "user_id": user["user_id"], "role": user["role"]}

@router.post("/register")
async def register(req: RegisterRequest):
    hashed = pwd_context.hash(req.password)
    try:
        user_id = await db.fetchval(
            "INSERT INTO users (email, password_hash, full_name) VALUES ($1, $2, $3) RETURNING user_id",
            req.email, hashed, req.name
        )
        token = create_access_token({"sub": str(user_id), "role": "INVESTIGATOR"})
        return {"access_token": token, "user_id": user_id, "role": "INVESTIGATOR"}
    except Exception:
        raise HTTPException(status_code=400, detail="Email already registered")

# Dependency for protected routes
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## 4. Case Management & Uploads

**File: `services/gateway/cases.py`**

```python
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import List
from uuid import uuid4
from services.database import db
from services.gateway.auth import get_current_user
from services.minio_client import storage
from pydantic import BaseModel
import hashlib

router = APIRouter()

class CaseCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""

@router.get("/")
async def list_cases(user_id: str = Depends(get_current_user)):
    cases = await db.fetch("SELECT * FROM cases ORDER BY created_at DESC")
    return [dict(c) for c in cases]

@router.post("/")
async def create_case(case: CaseCreate, user_id: str = Depends(get_current_user)):
    case_id = await db.fetchval(
        "INSERT INTO cases (title, description, location, created_by) "
        "VALUES ($1, $2, $3, $4) RETURNING case_id",
        case.title, case.description, case.location, user_id
    )
    return {"case_id": case_id}

@router.get("/{case_id}")
async def get_case(case_id: str, user_id: str = Depends(get_current_user)):
    case = await db.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    
    files = await db.fetch("SELECT * FROM case_files WHERE case_id=$1", case_id)
    result = dict(case)
    result["files"] = [dict(f) for f in files]
    return result

@router.post("/{case_id}/files")
async def upload_file(
    case_id: str, 
    file: UploadFile = File(...), 
    doc_type: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    data = await file.read()
    file_id = str(uuid4())
    sha256 = hashlib.sha256(data).hexdigest()
    
    # Upload to MinIO
    s3_key = storage.upload_file(case_id, file_id, file.filename, data, file.content_type)
    
    # Save to DB
    await db.execute(
        "INSERT INTO case_files (file_id, case_id, original_name, s3_key, mime_type, file_size_bytes, doc_type, sha256_hash, uploaded_by) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        file_id, case_id, file.filename, s3_key, file.content_type, len(data), doc_type, sha256, user_id
    )
    return {"file_id": file_id, "s3_key": s3_key}
```

---

## 5. WebSockets for Live UI Telemetry

**File: `services/gateway/websocket.py`**

```python
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.redis_client import get_redis

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Frontend connects to /ws.
    We listen to a Redis pub/sub channel for pipeline events and broadcast to all connected clients.
    """
    await manager.connect(websocket)
    redis_client = await get_redis()
    pubsub = redis_client.pubsub()
    
    # Subscribe to a wildcard or all case channels
    await pubsub.psubscribe("ws:case:*")
    
    try:
        # Task to listen to Redis and broadcast to WebSocket
        async def reader():
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    await manager.broadcast(message["data"])
                    
        # Task to keep connection alive
        async def keep_alive():
            while True:
                await asyncio.sleep(20)
                await websocket.send_text(json.dumps({"event": "ping"}))

        reader_task = asyncio.create_task(reader())
        keep_alive_task = asyncio.create_task(keep_alive())
        
        # Wait until client disconnects
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        reader_task.cancel()
        keep_alive_task.cancel()
        await pubsub.punsubscribe("ws:case:*")
```

---

## 6. Acceptance Criteria
- [ ] API Gateway starts via `uvicorn services.gateway.main:app`
- [ ] `/api/v1/auth/login` returns a JWT token
- [ ] `/api/v1/cases` endpoints are protected by HTTPBearer
- [ ] Uploading a file correctly streams bytes to MinIO and inserts DB row
- [ ] WebSocket client can connect to `/ws` and receives ping messages
