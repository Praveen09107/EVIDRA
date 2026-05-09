# CANONICAL SPEC 02 — Complete Database Schema
**Status:** FINAL | **Supersedes:** Database Schema.txt

---

## Extensions Required
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

## 1. Core Tables (Organizations, Users, Cases, Files)

```sql
-- ORGANIZATIONS
CREATE TABLE organizations (
    org_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    tier        TEXT NOT NULL DEFAULT 'STANDARD' CHECK (tier IN ('STANDARD','PREMIUM','ENTERPRISE')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- USERS
CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id        UUID NOT NULL REFERENCES organizations(org_id),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('INVESTIGATOR','SUPERVISOR','ADMIN','READONLY')),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);

-- CASES (Canonical status: OPEN | IN_ANALYSIS | REVIEW | CLOSED)
CREATE TABLE cases (
    case_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id       UUID NOT NULL REFERENCES organizations(org_id),
    case_number  TEXT UNIQUE NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    location     TEXT,
    status       TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_ANALYSIS','REVIEW','CLOSED')),
    risk_level   TEXT DEFAULT 'MEDIUM' CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    priority     TEXT NOT NULL DEFAULT 'NORMAL',
    assigned_to  UUID REFERENCES users(user_id),
    created_by   UUID NOT NULL REFERENCES users(user_id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_cases_org ON cases(org_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_created ON cases(created_at DESC);

-- CASE FILES
CREATE TABLE case_files (
    file_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    original_name   TEXT NOT NULL,
    s3_key          TEXT NOT NULL,
    doc_type        TEXT NOT NULL CHECK (doc_type IN ('CDR','AUTOPSY_REPORT','FINANCIAL_RECORDS','DEVICE_DATA','WITNESS_STATEMENT','OTHER')),
    mime_type       TEXT NOT NULL,
    size_bytes      BIGINT NOT NULL,
    checksum_sha256 TEXT,
    uploaded_by     UUID REFERENCES users(user_id),
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','PROCESSING','PROCESSED','FAILED'))
);
CREATE INDEX idx_files_case ON case_files(case_id);
CREATE INDEX idx_files_type ON case_files(doc_type);
```

## 2. Pipeline & Agent Execution

```sql
-- PIPELINE RUNS
CREATE TABLE pipeline_runs (
    pipeline_run_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id            UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    status             TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RUNNING','PARTIAL','COMPLETE','FAILED')),
    triggered_by       UUID REFERENCES users(user_id),
    started_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at       TIMESTAMPTZ,
    duration_ms        INTEGER,
    error_message      TEXT,
    overall_confidence FLOAT,
    agents_planned     JSONB NOT NULL DEFAULT '[]',
    agents_completed   JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX idx_runs_case ON pipeline_runs(case_id);

-- AGENT TASKS
CREATE TABLE agent_tasks (
    task_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id) ON DELETE CASCADE,
    case_id         UUID NOT NULL,
    agent_id        TEXT NOT NULL,
    tier            INTEGER NOT NULL,
    depends_on      JSONB NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'WAITING' CHECK (status IN ('WAITING','DISPATCHED','RUNNING','COMPLETE','FAILED','SKIPPED')),
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    dispatched_at   TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_code      TEXT,
    error_message   TEXT,
    tokens_used     INTEGER,
    duration_ms     INTEGER
);
CREATE INDEX idx_tasks_run ON agent_tasks(pipeline_run_id);
CREATE INDEX idx_tasks_agent ON agent_tasks(agent_id, status);

-- AGENT RESULTS (JSONB store per agent per run)
CREATE TABLE agent_results (
    result_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id) ON DELETE CASCADE,
    case_id         UUID NOT NULL,
    agent_id        TEXT NOT NULL,
    result_json     JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_results_run_agent ON agent_results(pipeline_run_id, agent_id);
CREATE INDEX idx_results_case ON agent_results(case_id);
```

## 3. Canonical Evidence Tables

```sql
-- CDR EVENTS
CREATE TABLE canonical_cdr_events (
    event_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id             UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    file_id             UUID NOT NULL REFERENCES case_files(file_id),
    source_msisdn       TEXT NOT NULL,
    event_timestamp     TIMESTAMPTZ NOT NULL,
    event_type          TEXT NOT NULL CHECK (event_type IN ('MOC','MTC','SMS_MO','SMS_MT','DATA')),
    duration_seconds    INTEGER,
    counterparty_msisdn TEXT,
    cell_tower_id       TEXT,
    tower_latitude      FLOAT,
    tower_longitude     FLOAT,
    imei                TEXT,
    raw_source_operator TEXT
);
CREATE INDEX idx_cdr_case_ts ON canonical_cdr_events(case_id, event_timestamp);
CREATE INDEX idx_cdr_msisdn ON canonical_cdr_events(source_msisdn);

-- FINANCIAL EVENTS
CREATE TABLE canonical_financial_events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    file_id         UUID NOT NULL REFERENCES case_files(file_id),
    timestamp       TIMESTAMPTZ NOT NULL,
    txn_type        TEXT NOT NULL CHECK (txn_type IN ('DEBIT','CREDIT')),
    amount          NUMERIC(18,2) NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'INR',
    narration       TEXT,
    category        TEXT,
    counterparty_id TEXT,
    balance_after   NUMERIC(18,2),
    institution     TEXT
);
CREATE INDEX idx_fin_case_ts ON canonical_financial_events(case_id, timestamp);
```

## 4. Collision & Hotspot Tables (NEW — GAP-02 fix)

```sql
-- ENTITY TRACKS (from Image Agent + CDR + IoT)
CREATE TABLE entity_tracks (
    track_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id     UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    entity_id   TEXT NOT NULL,
    entity_kind TEXT NOT NULL CHECK (entity_kind IN ('PERSON','DEVICE','OBJECT')),
    source      TEXT NOT NULL CHECK (source IN ('CCTV','PHONE','IOT','SCENE','MANUAL')),
    segments    JSONB NOT NULL,
    confidence  FLOAT NOT NULL DEFAULT 0.5,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_tracks_case ON entity_tracks(case_id);

-- COLLISION EVENTS
CREATE TABLE collision_events (
    collision_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id           UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    pipeline_run_id   UUID REFERENCES pipeline_runs(pipeline_run_id),
    time_start        TIMESTAMPTZ NOT NULL,
    time_end          TIMESTAMPTZ NOT NULL,
    region_id         TEXT,
    collision_type    TEXT NOT NULL CHECK (collision_type IN ('CO_PRESENCE','NEAR_MISS','CONSISTENCY','CONTRADICTION')),
    participants      JSONB NOT NULL,
    source_evidence   JSONB NOT NULL DEFAULT '[]',
    confidence        FLOAT NOT NULL,
    explanation       TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_collision_case ON collision_events(case_id);
CREATE INDEX idx_collision_time ON collision_events(time_start, time_end);

-- HOTSPOTS
CREATE TABLE hotspots (
    hotspot_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id             UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    pipeline_run_id     UUID REFERENCES pipeline_runs(pipeline_run_id),
    rank                INTEGER NOT NULL,
    score               FLOAT NOT NULL,
    time_start          TIMESTAMPTZ NOT NULL,
    time_end            TIMESTAMPTZ NOT NULL,
    within_tod_band     BOOLEAN DEFAULT FALSE,
    overlap_tod_fraction FLOAT DEFAULT 0,
    sources             JSONB NOT NULL DEFAULT '[]',
    anomaly_ids         UUID[] DEFAULT '{}',
    key_event_ids       UUID[] DEFAULT '{}',
    hypothesis_impacts  JSONB NOT NULL DEFAULT '[]',
    explanation         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_hotspots_case ON hotspots(case_id);
CREATE INDEX idx_hotspots_score ON hotspots(score DESC);
```

## 5. Claims & Argument Graph Tables (NEW — GAP-02 fix)

```sql
-- CLAIMS (from Claim Extractor)
CREATE TABLE claims (
    claim_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id           UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    pipeline_run_id   UUID REFERENCES pipeline_runs(pipeline_run_id),
    source_document_id UUID REFERENCES case_files(file_id),
    source_span       JSONB,
    text              TEXT NOT NULL,
    normalized_text   TEXT NOT NULL,
    subject_entities  JSONB DEFAULT '[]',
    predicate         TEXT,
    objects           JSONB DEFAULT '[]',
    time_info         JSONB,
    location_info     JSONB,
    polarity          TEXT CHECK (polarity IN ('ASSERT','DENY','UNCERTAIN')),
    claim_type        TEXT CHECK (claim_type IN ('EVENT','STATE','ALIBI','CAUSAL','MENTAL_STATE','NORMATIVE')),
    certainty         FLOAT DEFAULT 0.5,
    speaker_id        TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_claims_case ON claims(case_id);

-- CLAIM RELATIONS
CREATE TABLE claim_relations (
    relation_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL,
    from_claim_id UUID NOT NULL REFERENCES claims(claim_id),
    to_claim_id   UUID NOT NULL REFERENCES claims(claim_id),
    relation      TEXT NOT NULL CHECK (relation IN ('CONTRADICTS','SUPPORTS','REFINES','TEMPORALLY_BEFORE')),
    confidence    FLOAT NOT NULL DEFAULT 0.5
);

-- EVIDENCE-CLAIM LINKS (from Evidence-Claim Mapper)
CREATE TABLE evidence_claim_links (
    link_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL,
    claim_id      UUID NOT NULL REFERENCES claims(claim_id),
    evidence_id   UUID NOT NULL,
    evidence_kind TEXT NOT NULL,
    label         TEXT NOT NULL CHECK (label IN ('SUPPORTS','REFUTES','PARTIAL_SUPPORT','PARTIAL_REFUTE','NOT_ENOUGH_INFO','IRRELEVANT')),
    confidence    FLOAT NOT NULL,
    explanation   TEXT,
    attribution_score FLOAT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ecl_claim ON evidence_claim_links(claim_id);

-- CLAIM VERDICTS (from Verdict Aggregation)
CREATE TABLE claim_verdicts (
    verdict_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id        UUID NOT NULL,
    claim_id       UUID NOT NULL REFERENCES claims(claim_id),
    verdict        TEXT NOT NULL CHECK (verdict IN ('SUPPORTED','REFUTED','CONFLICTING','NOT_ENOUGH_INFO')),
    confidence     FLOAT NOT NULL,
    support_mass   FLOAT,
    refute_mass    FLOAT,
    nei_mass       FLOAT,
    justification  TEXT,
    flags          JSONB DEFAULT '[]',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- CAUSAL GRAPH
CREATE TABLE causal_graph_nodes (
    node_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    kind          TEXT NOT NULL CHECK (kind IN ('HYPOTHESIS','CLAIM','EVIDENCE')),
    label         TEXT NOT NULL,
    probability   FLOAT,
    importance    FLOAT,
    metadata      JSONB DEFAULT '{}'
);
CREATE INDEX idx_graph_nodes_case ON causal_graph_nodes(case_id);

CREATE TABLE causal_graph_edges (
    edge_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id  UUID NOT NULL,
    source   UUID NOT NULL REFERENCES causal_graph_nodes(node_id),
    target   UUID NOT NULL REFERENCES causal_graph_nodes(node_id),
    relation TEXT NOT NULL CHECK (relation IN ('SUPPORTS','CONTRADICTS','NEUTRAL')),
    strength FLOAT NOT NULL DEFAULT 0.5
);
```

## 6. Hypothesis & Reasoning Tables (NEW — GAP-02 fix)

```sql
-- HYPOTHESIS HISTORY (versioned per pipeline run)
CREATE TABLE hypothesis_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    hypothesis_key  TEXT NOT NULL CHECK (hypothesis_key IN ('NATURAL','ACCIDENT','SUICIDE','HOMICIDE','UNDETERMINED')),
    probability     FLOAT NOT NULL,
    trend           TEXT CHECK (trend IN ('UP','DOWN','STABLE')),
    evidence_summary TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_hyp_case ON hypothesis_history(case_id, pipeline_run_id);

-- UNCERTAINTY REPORTS (from Bias & Uncertainty Monitor)
CREATE TABLE uncertainty_reports (
    report_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    model_assessments    JSONB NOT NULL DEFAULT '[]',
    cross_agent_findings JSONB NOT NULL DEFAULT '[]',
    bias_flags           JSONB NOT NULL DEFAULT '[]',
    escalation_recs      JSONB NOT NULL DEFAULT '[]',
    narrative            TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- NBE SUGGESTIONS & FEEDBACK
CREATE TABLE nbe_suggestions (
    suggestion_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id          UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    pipeline_run_id  UUID REFERENCES pipeline_runs(pipeline_run_id),
    kind             TEXT NOT NULL,
    label            TEXT NOT NULL,
    description      TEXT NOT NULL,
    action_type      TEXT NOT NULL,
    action_params    JSONB DEFAULT '{}',
    expected_ig      FLOAT,
    expected_cost    FLOAT,
    priority_score   FLOAT NOT NULL,
    targets          JSONB DEFAULT '[]',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE nbe_feedback (
    feedback_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suggestion_id UUID NOT NULL REFERENCES nbe_suggestions(suggestion_id),
    case_id       UUID NOT NULL,
    action_taken  TEXT NOT NULL CHECK (action_taken IN ('ACCEPTED','IGNORED','REJECTED','NOT_POSSIBLE')),
    outcome       TEXT CHECK (outcome IN ('HELPFUL','NOT_HELPFUL','UNKNOWN')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 7. Replay & Audit Tables

```sql
-- REPLAY STEPS (append-only)
CREATE TABLE replay_steps (
    step_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id) ON DELETE CASCADE,
    case_id         UUID NOT NULL,
    agent_id        TEXT NOT NULL,
    step_index      INTEGER NOT NULL,
    global_index    INTEGER,
    trigger_type    TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    input_summary   TEXT NOT NULL,
    interpretation  TEXT NOT NULL,
    confidence      FLOAT NOT NULL,
    evidence_ids    UUID[] NOT NULL DEFAULT '{}',
    warnings        TEXT[] NOT NULL DEFAULT '{}',
    tokens_used     INTEGER,
    duration_ms     INTEGER,
    parent_step_ids UUID[] NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_steps_run ON replay_steps(pipeline_run_id);
CREATE INDEX idx_steps_global ON replay_steps(global_index);

-- AUDIT LOG (append-only, immutable)
CREATE TABLE audit_log (
    log_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID,
    org_id        UUID,
    action        TEXT NOT NULL,
    resource_type TEXT,
    resource_id   UUID,
    ip_address    INET,
    user_agent    TEXT,
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata      JSONB
);
CREATE INDEX idx_audit_user ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);

-- CUSTODY LOG (append-only, immutable)
CREATE TABLE custody_log (
    log_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id     UUID NOT NULL REFERENCES cases(case_id),
    file_id     UUID REFERENCES case_files(file_id),
    action      TEXT NOT NULL CHECK (action IN ('UPLOADED','ACCESSED','PROCESSED','EXPORTED','DELETED')),
    actor_id    UUID,
    actor_type  TEXT CHECK (actor_type IN ('USER','AGENT','SYSTEM')),
    checksum    TEXT,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB
);
CREATE INDEX idx_custody_case ON custody_log(case_id, timestamp);

-- IMMUTABILITY TRIGGERS (append-only enforcement)
CREATE OR REPLACE FUNCTION prevent_update_delete() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'UPDATE/DELETE not permitted on append-only table %', TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_immutable BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_custody_immutable BEFORE UPDATE OR DELETE ON custody_log
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_replay_immutable BEFORE UPDATE OR DELETE ON replay_steps
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();
```

## 8. Model Calibration Stats (for Bias Monitor)

```sql
CREATE TABLE model_calibration_stats (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id          TEXT NOT NULL,
    model_type        TEXT NOT NULL CHECK (model_type IN ('ML','LLM','RULE','HYBRID')),
    calibration_status TEXT DEFAULT 'UNCALIBRATED',
    global_brier_score FLOAT,
    ece               FLOAT,
    training_data_note TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_calibration_model ON model_calibration_stats(model_id);
```

**Total Tables: 24** (was 10, added 14 missing tables + 3 immutability triggers)
