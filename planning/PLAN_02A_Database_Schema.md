# PLAN 02A — PostgreSQL Schema & Database Utilities
**Owner:** Dev A | **Hour:** 0:30–1:00 | **Priority:** CRITICAL

---

## 1. Objective
Execute the complete 24-table PostgreSQL schema, create the asyncpg connection pool module, and verify all tables, triggers, and indexes are operational. This is the foundational data layer — every agent, the API gateway, and the orchestrator depend on it.

---

## 2. Full SQL Schema

**File: `sql/init.sql`**

```sql
-- ═══════════════════════════════════════════════════════════
-- AIVENTRA Forensic Intelligence Platform — Database Schema
-- PostgreSQL 16 | 24 Tables | UUID Primary Keys | JSONB
-- ═══════════════════════════════════════════════════════════

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── 1. USERS ───
CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(255) NOT NULL,
    role          VARCHAR(50) NOT NULL DEFAULT 'INVESTIGATOR'
                    CHECK (role IN ('ADMIN','INVESTIGATOR','PATHOLOGIST','LEGAL','VIEWER')),
    department    VARCHAR(255),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 2. CASES ───
CREATE TABLE cases (
    case_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_number   VARCHAR(50) UNIQUE NOT NULL,
    title         VARCHAR(500) NOT NULL,
    description   TEXT,
    status        VARCHAR(30) NOT NULL DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN','IN_ANALYSIS','REVIEW','CLOSED','ARCHIVED')),
    risk_level    VARCHAR(20) DEFAULT 'MEDIUM'
                    CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    location      VARCHAR(500),
    incident_date TIMESTAMPTZ,
    created_by    UUID REFERENCES users(user_id),
    assigned_to   UUID REFERENCES users(user_id),
    tags          TEXT[],
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_created_by ON cases(created_by);
CREATE INDEX idx_cases_created_at ON cases(created_at DESC);

-- ─── 3. CASE FILES ───
CREATE TABLE case_files (
    file_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    original_name VARCHAR(500) NOT NULL,
    s3_key        VARCHAR(1000) NOT NULL,
    mime_type     VARCHAR(100),
    file_size_bytes BIGINT,
    doc_type      VARCHAR(50) NOT NULL
                    CHECK (doc_type IN ('AUTOPSY_REPORT','CDR','FINANCIAL_RECORDS',
                           'DEVICE_DATA','CCTV','WITNESS_STATEMENT','POLICE_REPORT','OTHER')),
    status        VARCHAR(30) DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','PROCESSING','PROCESSED','FAILED')),
    sha256_hash   VARCHAR(64),
    uploaded_by   UUID REFERENCES users(user_id),
    uploaded_at   TIMESTAMPTZ DEFAULT NOW(),
    processed_at  TIMESTAMPTZ
);

CREATE INDEX idx_case_files_case ON case_files(case_id);
CREATE INDEX idx_case_files_doc_type ON case_files(doc_type);

-- ─── 4. PIPELINE RUNS ───
CREATE TABLE pipeline_runs (
    pipeline_run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    triggered_by    UUID REFERENCES users(user_id),
    status          VARCHAR(30) DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING','RUNNING','COMPLETE','FAILED','CANCELLED')),
    agent_plan      JSONB NOT NULL DEFAULT '{}',
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    run_version     INT DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pipeline_runs_case ON pipeline_runs(case_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);

-- ─── 5. AGENT TASKS ───
CREATE TABLE agent_tasks (
    task_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    agent_id        VARCHAR(50) NOT NULL,
    status          VARCHAR(30) DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING','DISPATCHED','RUNNING','COMPLETE','FAILED','SKIPPED')),
    tier            INT NOT NULL DEFAULT 0,
    depends_on      TEXT[] DEFAULT '{}',
    attempt_count   INT DEFAULT 0,
    max_attempts    INT DEFAULT 3,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_ms     INT,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_tasks_pipeline ON agent_tasks(pipeline_run_id);
CREATE INDEX idx_agent_tasks_status ON agent_tasks(status);
CREATE UNIQUE INDEX idx_agent_tasks_unique ON agent_tasks(pipeline_run_id, agent_id);

-- ─── 6. AGENT RESULTS ───
CREATE TABLE agent_results (
    result_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    agent_id        VARCHAR(50) NOT NULL,
    result_data     JSONB NOT NULL DEFAULT '{}',
    confidence      FLOAT,
    warnings        TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_agent_results_unique ON agent_results(pipeline_run_id, agent_id);
CREATE INDEX idx_agent_results_pipeline ON agent_results(pipeline_run_id);

-- ─── 7. REPLAY STEPS (Audit Trail) ───
CREATE TABLE replay_steps (
    step_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    agent_id        VARCHAR(50) NOT NULL,
    step_type       VARCHAR(50) NOT NULL
                      CHECK (step_type IN ('DATA_NORMALIZATION','LLM_EXTRACTION','MODEL_OUTPUT',
                             'ML_INFERENCE','PHYSICS_MODEL','BAYESIAN_FUSION','ANOMALY_DETECTION',
                             'CONSISTENCY_CHECK','HYPOTHESIS_SCORE','RULE','LLM_NARRATIVE','ERROR')),
    action          TEXT NOT NULL,
    interpretation  TEXT NOT NULL,
    confidence      FLOAT NOT NULL DEFAULT 0.5,
    evidence_ids    UUID[],
    warnings        TEXT[],
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_replay_steps_pipeline ON replay_steps(pipeline_run_id);
CREATE INDEX idx_replay_steps_agent ON replay_steps(agent_id);
CREATE INDEX idx_replay_steps_ts ON replay_steps(timestamp);

-- ─── 8. CANONICAL CDR EVENTS ───
CREATE TABLE canonical_cdr_events (
    event_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id             UUID NOT NULL REFERENCES cases(case_id),
    file_id             UUID REFERENCES case_files(file_id),
    source_msisdn       VARCHAR(20),
    event_timestamp     TIMESTAMPTZ NOT NULL,
    event_type          VARCHAR(20) NOT NULL
                          CHECK (event_type IN ('MOC','MTC','SMS_MO','SMS_MT','DATA','GPRS')),
    duration_seconds    INT DEFAULT 0,
    counterparty_msisdn VARCHAR(20),
    cell_tower_id       VARCHAR(50),
    imei                VARCHAR(20),
    lat                 FLOAT,
    lon                 FLOAT,
    raw_data            JSONB DEFAULT '{}'
);

CREATE INDEX idx_cdr_case ON canonical_cdr_events(case_id);
CREATE INDEX idx_cdr_timestamp ON canonical_cdr_events(event_timestamp);
CREATE INDEX idx_cdr_tower ON canonical_cdr_events(cell_tower_id);
CREATE INDEX idx_cdr_msisdn ON canonical_cdr_events(source_msisdn);

-- ─── 9. CANONICAL FINANCIAL EVENTS ───
CREATE TABLE canonical_financial_events (
    event_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL REFERENCES cases(case_id),
    file_id       UUID REFERENCES case_files(file_id),
    timestamp     TIMESTAMPTZ NOT NULL,
    txn_type      VARCHAR(20) NOT NULL CHECK (txn_type IN ('DEBIT','CREDIT')),
    amount        NUMERIC(15,2) NOT NULL,
    currency      VARCHAR(5) DEFAULT 'INR',
    narration     TEXT,
    category      VARCHAR(100),
    balance_after NUMERIC(15,2),
    counterparty  VARCHAR(255),
    bank_name     VARCHAR(100),
    raw_data      JSONB DEFAULT '{}'
);

CREATE INDEX idx_fin_case ON canonical_financial_events(case_id);
CREATE INDEX idx_fin_timestamp ON canonical_financial_events(timestamp);
CREATE INDEX idx_fin_amount ON canonical_financial_events(amount);

-- ─── 10. COLLISION EVENTS ───
CREATE TABLE collision_events (
    collision_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    time_start      TIMESTAMPTZ,
    time_end        TIMESTAMPTZ,
    collision_type  VARCHAR(30) CHECK (collision_type IN ('CO_PRESENCE','CONSISTENCY','TEMPORAL_OVERLAP')),
    participants    JSONB DEFAULT '[]',
    region_id       VARCHAR(100),
    confidence      FLOAT DEFAULT 0.5,
    explanation     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_collision_case ON collision_events(case_id);

-- ─── 11. HOTSPOTS ───
CREATE TABLE hotspots (
    hotspot_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    rank            INT,
    score           FLOAT NOT NULL,
    time_start      TIMESTAMPTZ,
    time_end        TIMESTAMPTZ,
    within_tod_band BOOLEAN DEFAULT FALSE,
    sources         JSONB DEFAULT '[]',
    explanation     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hotspots_case ON hotspots(case_id);
CREATE INDEX idx_hotspots_score ON hotspots(score DESC);

-- ─── 12. CLAIMS ───
CREATE TABLE claims (
    claim_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    text            TEXT NOT NULL,
    normalized_text TEXT,
    polarity        VARCHAR(20) DEFAULT 'ASSERT'
                      CHECK (polarity IN ('ASSERT','DENY','UNCERTAIN')),
    claim_type      VARCHAR(30) DEFAULT 'EVENT'
                      CHECK (claim_type IN ('EVENT','STATE','ALIBI','CAUSAL','MENTAL_STATE','TEMPORAL')),
    certainty       FLOAT DEFAULT 0.5,
    source_agent    VARCHAR(50),
    time_info       TIMESTAMPTZ,
    location_info   VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_claims_case ON claims(case_id);

-- ─── 13. EVIDENCE-CLAIM LINKS ───
CREATE TABLE evidence_claim_links (
    link_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id        UUID NOT NULL REFERENCES cases(case_id),
    claim_id       UUID REFERENCES claims(claim_id),
    evidence_id    UUID,
    evidence_kind  VARCHAR(50),
    label          VARCHAR(30) NOT NULL
                     CHECK (label IN ('SUPPORTS','REFUTES','PARTIAL_SUPPORT','PARTIAL_REFUTE','NOT_ENOUGH_INFO','IRRELEVANT')),
    confidence     FLOAT DEFAULT 0.5,
    explanation    TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ecl_case ON evidence_claim_links(case_id);
CREATE INDEX idx_ecl_claim ON evidence_claim_links(claim_id);

-- ─── 14. HYPOTHESIS HISTORY ───
CREATE TABLE hypothesis_history (
    history_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    hypothesis_key  VARCHAR(30) NOT NULL
                      CHECK (hypothesis_key IN ('NATURAL','ACCIDENT','SUICIDE','HOMICIDE','UNDETERMINED')),
    probability     FLOAT NOT NULL,
    trend           VARCHAR(10) DEFAULT 'STABLE' CHECK (trend IN ('UP','DOWN','STABLE')),
    evidence_summary TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hyp_case ON hypothesis_history(case_id);
CREATE INDEX idx_hyp_pipeline ON hypothesis_history(pipeline_run_id);

-- ─── 15. CAUSAL GRAPH NODES ───
CREATE TABLE causal_graph_nodes (
    node_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    label           VARCHAR(500) NOT NULL,
    kind            VARCHAR(30) NOT NULL CHECK (kind IN ('HYPOTHESIS','CLAIM','EVIDENCE','AGENT','EVENT')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cgn_case ON causal_graph_nodes(case_id);

-- ─── 16. CAUSAL GRAPH EDGES ───
CREATE TABLE causal_graph_edges (
    edge_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    source_node_id  UUID REFERENCES causal_graph_nodes(node_id),
    target_node_id  UUID REFERENCES causal_graph_nodes(node_id),
    relation        VARCHAR(30) CHECK (relation IN ('SUPPORTS','CONTRADICTS','NEUTRAL','CAUSES','CORRELATES')),
    strength        FLOAT DEFAULT 0.5,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cge_case ON causal_graph_edges(case_id);

-- ─── 17. UNCERTAINTY REPORTS ───
CREATE TABLE uncertainty_reports (
    report_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    bias_flags      JSONB DEFAULT '[]',
    escalation_recs JSONB DEFAULT '[]',
    overall_score   FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 18. NBE SUGGESTIONS ───
CREATE TABLE nbe_suggestions (
    suggestion_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    kind            VARCHAR(50),
    label           VARCHAR(500),
    description     TEXT,
    action_type     VARCHAR(30) DEFAULT 'COLLECT_EVIDENCE'
                      CHECK (action_type IN ('COLLECT_EVIDENCE','RERUN_AGENT','MANUAL_REVIEW','EXTERNAL_CONSULT')),
    priority_score  FLOAT DEFAULT 0.5,
    expected_ig     FLOAT DEFAULT 0.0,
    status          VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING','ACCEPTED','DISMISSED')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nbe_case ON nbe_suggestions(case_id);

-- ─── 19. AUDIT LOG (Append-Only) ───
CREATE TABLE audit_log (
    log_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(user_id),
    action      VARCHAR(50) NOT NULL,
    resource    VARCHAR(100),
    resource_id UUID,
    details     JSONB DEFAULT '{}',
    ip_address  INET,
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);

-- ─── 20. CHAIN OF CUSTODY ───
CREATE TABLE chain_of_custody (
    custody_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id     UUID NOT NULL REFERENCES case_files(file_id),
    action      VARCHAR(30) NOT NULL CHECK (action IN ('UPLOADED','ACCESSED','EXPORTED','MODIFIED','DELETED')),
    actor_id    UUID REFERENCES users(user_id),
    sha256_at_action VARCHAR(64),
    notes       TEXT,
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_custody_file ON chain_of_custody(file_id);

-- ─── 21. TIMELINE EVENTS (Unified) ───
CREATE TABLE timeline_events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    timestamp       TIMESTAMPTZ NOT NULL,
    source          VARCHAR(30) NOT NULL CHECK (source IN ('PHONE','FINANCIAL','DEVICE','WITNESS','FORENSIC','SYSTEM')),
    event_type      VARCHAR(50),
    description     TEXT,
    anomaly_score   FLOAT DEFAULT 0.0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_timeline_case ON timeline_events(case_id);
CREATE INDEX idx_timeline_ts ON timeline_events(timestamp);

-- ─── 22. ANOMALY WINDOWS ───
CREATE TABLE anomaly_windows (
    window_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    time_start      TIMESTAMPTZ,
    time_end        TIMESTAMPTZ,
    ae_score        FLOAT,
    if_score        FLOAT,
    fused_score     FLOAT NOT NULL,
    label           VARCHAR(20) CHECK (label IN ('CRITICAL','INTERESTING','MINOR')),
    factors         JSONB DEFAULT '[]',
    explanation     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_anomaly_case ON anomaly_windows(case_id);

-- ─── 23. REPORT SNAPSHOTS ───
CREATE TABLE report_snapshots (
    report_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    report_type     VARCHAR(30) DEFAULT 'FULL' CHECK (report_type IN ('FULL','SUMMARY','EXECUTIVE')),
    sections        JSONB NOT NULL DEFAULT '[]',
    narrative       TEXT,
    generated_by    UUID REFERENCES users(user_id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 24. SESSIONS (Token Tracking) ───
CREATE TABLE sessions (
    session_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(user_id),
    token_hash  VARCHAR(64),
    ip_address  INET,
    user_agent  TEXT,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions(user_id);

-- ═══════════════════════════════════════════════════════════
-- TRIGGERS
-- ═══════════════════════════════════════════════════════════

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_cases_updated BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Auto-generate case_number
CREATE OR REPLACE FUNCTION generate_case_number()
RETURNS TRIGGER AS $$
DECLARE
    seq_num INT;
BEGIN
    SELECT COUNT(*) + 1 INTO seq_num FROM cases WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());
    NEW.case_number = 'CASE-' || EXTRACT(YEAR FROM NOW())::TEXT || '-' || LPAD(seq_num::TEXT, 3, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_case_number BEFORE INSERT ON cases
    FOR EACH ROW WHEN (NEW.case_number IS NULL OR NEW.case_number = '')
    EXECUTE FUNCTION generate_case_number();

-- Auto-audit on case_files access
CREATE OR REPLACE FUNCTION log_file_custody()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO chain_of_custody (file_id, action, sha256_at_action)
    VALUES (NEW.file_id, 'UPLOADED', NEW.sha256_hash);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_file_custody AFTER INSERT ON case_files
    FOR EACH ROW EXECUTE FUNCTION log_file_custody();

-- ═══════════════════════════════════════════════════════════
-- SEED DATA (Development Only)
-- ═══════════════════════════════════════════════════════════

-- Default admin user (password: admin123)
INSERT INTO users (email, password_hash, full_name, role) VALUES
    ('admin@aiventra.gov', '$2b$12$LJ3m4ys4dF0G9q2o5h0rAOe.TV/0YVJz8.5BW0dO9.CQ3MfR2zEPi', 'System Admin', 'ADMIN'),
    ('investigator@police.gov', '$2b$12$LJ3m4ys4dF0G9q2o5h0rAOe.TV/0YVJz8.5BW0dO9.CQ3MfR2zEPi', 'Inspector Singh', 'INVESTIGATOR');
```

---

## 3. Database Connection Pool Module

**File: `services/database.py`**

```python
"""
Async PostgreSQL connection pool using asyncpg.
All database operations across the platform use this module.

Usage:
    from services.database import db
    rows = await db.fetch("SELECT * FROM cases WHERE status=$1", "OPEN")
    row = await db.fetchrow("SELECT * FROM users WHERE email=$1", email)
    await db.execute("INSERT INTO cases (title) VALUES ($1)", title)
"""
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

_pool = None

async def get_pool() -> asyncpg.Pool:
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.getenv("DATABASE_URL"),
            min_size=int(os.getenv("DB_MIN_POOL", "2")),
            max_size=int(os.getenv("DB_MAX_POOL", "10")),
            command_timeout=30.0,
            statement_cache_size=100,
        )
    return _pool

async def close_pool():
    """Close the connection pool gracefully."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def fetch(query: str, *args) -> list:
    """Execute a query and return all rows as list of Records."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def fetchrow(query: str, *args):
    """Execute a query and return a single row."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def fetchval(query: str, *args):
    """Execute a query and return a single value."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)

async def execute(query: str, *args) -> str:
    """Execute a query (INSERT/UPDATE/DELETE) and return status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

async def executemany(query: str, args_list: list) -> None:
    """Execute a query for each set of args in the list."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(query, args_list)

# Module-level shorthand
db = type('DB', (), {
    'get_pool': staticmethod(get_pool),
    'close_pool': staticmethod(close_pool),
    'fetch': staticmethod(fetch),
    'fetchrow': staticmethod(fetchrow),
    'fetchval': staticmethod(fetchval),
    'execute': staticmethod(execute),
    'executemany': staticmethod(executemany),
})()
```

---

## 4. Verification

```powershell
# After docker compose up -d:
docker exec -it aiventra_postgres psql -U aiventra -d aiventra_db -c "\dt"
# Should list 24 tables

# Test Python connection:
python -c "
import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv()
async def test():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    tables = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
    print(f'{len(tables)} tables found')
    for t in tables: print(f'  {t[\"tablename\"]}')
    await conn.close()
asyncio.run(test())
"
```

---

## 5. Acceptance Criteria
- [ ] `\dt` in psql shows exactly 24 tables
- [ ] All CHECK constraints are active (test invalid insert fails)
- [ ] Triggers fire: inserting a case auto-generates `case_number`
- [ ] Inserting a case_file auto-creates `chain_of_custody` record
- [ ] `database.py` pool connects and `fetch("SELECT 1")` returns
- [ ] Seed users exist and can be queried
