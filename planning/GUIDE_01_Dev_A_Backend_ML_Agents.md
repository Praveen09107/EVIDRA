# EXECUTION GUIDE — DEV A (Backend, ML, & Agents)
**Role:** Backend Lead & ML Engineer
**Hardware:** RTX 3050 (4GB VRAM) System
**Primary Domain:** `d:\Program Files\forensic\aiventra\services\` and `sql/` and `models/`

---

## 1. Your Mission
You are the architect of the platform's brain. You will build the database layer, the FastAPI backend, the core Orchestrator (DAG engine), and all 17 intelligence agents. Your code provides the data and the reasoning that Dev B will visualize.

## 2. Your Exact Scope (What You Touch)
**You own EVERYTHING inside:**
- `sql/` (Database schema)
- `services/` (Backend, orchestrator, agents)
- `models/` (ML artifacts)
- `tests/` (Synthetic data generation)
- `docker-compose.yml` & `.env`

⛔ **STRICT BOUNDARY:** You must **NEVER** modify or create files inside the `frontend/` directory.

---

## 3. Step-by-Step Implementation Instructions

### Phase 1: Infrastructure & API Foundation (Hours 1–3)
1. **Boot the Database:** Navigate to `PLAN_01` and `PLAN_02A`. Execute the Docker Compose file. Ensure PostgreSQL, Redis, and MinIO are running. You can test your DB using `pgAdmin` or `psql` connecting to `localhost:5432`.
2. **Setup Global Config & Clients:** Copy `services/config.py`, `services/database.py` (Asyncpg pool), `services/redis_client.py`, and `services/minio_client.py` exactly as written in `PLAN_02B`. 
   *Rule:* Never use `psycopg2` or `sync` calls here. Everything must be `async`.
3. **The LLM Gateway:** Implement `services/llm_gateway.py` (from `PLAN_03A`). This is the most critical file for agent stability. Make sure your `GEMINI_API_KEY` is in the `.env` file. Test it independently by running a quick python script calling `await llm.complete_json(...)`.
4. **FastAPI Gateway:** Implement the files in `services/gateway/` (from `PLAN_04`). This is what Dev B needs immediately to start building the UI.
   *Crucial Handoff:* As soon as `/api/v1/auth/login` and `/api/v1/cases` are working, **push your code to `dev/backend` branch** and tell Dev B to pull it. They are blocked until you provide this API.

### Phase 2: The Agent Contract & Orchestrator (Hours 3–5)
1. **BaseAgent:** Implement `services/base_agent.py` (`PLAN_03B`). Understand that every agent you build from now on will inherit from this class. You will only ever override the `execute()` method.
2. **Orchestrator:** Implement `services/orchestrator/dag.py`, `dispatcher.py`, and `main.py` (`PLAN_05`).
   *How to test it without UI:* Write a small python script that inserts a fake case into the DB, adds some fake `case_files`, and calls `await dispatch_ready_agents(run_id, case_id)`. Check Redis (`redis-cli xlen agent:evidence_parser:tasks`) to see if the task was dispatched.

### Phase 3: Building the Agent Fleet (Hours 5–18)
This is where the bulk of your time goes. You will implement 17 agents across files from `PLAN_06` to `PLAN_11`.

**How to implement an Agent:**
1. Create `services/agents/<agent_name>/agent.py`.
2. Inherit from `BaseAgent`. Set `agent_id = "<agent_name>"`.
3. Write `async def execute(self, task: AgentTask) -> AgentResult:`
4. Fetch dependencies using `await self.get_prior_result(task, "dependency_agent")`.
5. Call the LLM or ML model.
6. Call `self.log_step(...)` to record the reasoning for the audit trail.
7. Return `AgentResult(data={...})`.

**Handling ML on your RTX 3050 (4GB):**
- In `PLAN_09` (Timeline Anomaly), you are using PyTorch. Since 4GB is small, ensure your batch sizes are small and your neural network layers remain tiny (e.g., `Linear(3, 16)` as written in the plan).
- When training the RandomForest for the TOD agent (`PLAN_08`), it uses scikit-learn on the CPU, so it will not impact your VRAM.
- For the Image Agent (`PLAN_07`), you are passing base64 images directly to Gemini Flash. This saves your GPU entirely.

### Phase 4: Integration & Workers (Hours 19–22)
1. **The Worker Runner:** Implement `services/worker.py` (`PLAN_17`). This script allows you to spin up all 17 agents at once. 
2. **Synthetic Data:** Implement `tests/fixtures/generate_case.py` (`PLAN_18`) to generate the "Arun Kumar" case. 
3. **End-to-End Test:** Run the API, the Orchestrator, and the Worker Runner. Upload the synthetic files via Swagger UI (`http://localhost:8000/docs`) and trigger the pipeline. Watch the orchestrator logs in your terminal to ensure all 8 tiers execute successfully.

---

## 4. How to Avoid Breaking Dev B
- **JSON Contracts:** Dev B's React code expects exact JSON keys (e.g., `pipeline_run_id`, `anomaly_score`). If you change a key in FastAPI or in an agent's output, you **will crash the frontend**. Stick strictly to the JSON outputs defined in the PLAN documents.
- **WebSockets:** Make sure your `publish_ws_event` (in `BaseAgent` and `Orchestrator`) is firing properly. Dev B's UI relies entirely on these Redis pub/sub messages to animate the pipeline. If you don't fire them, the UI will look frozen.
- **Database Schema:** If you absolutely must change a database column in `init.sql` during the sprint, you must immediately tell Dev B and perform a manual database reset (`docker compose down -v && docker compose up -d`).
