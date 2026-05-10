-- ═══════════════════════════════════════════════════════════
-- EVIDRA Forensic Intelligence Platform — Database Schema
-- PostgreSQL 16 | 30 Tables | UUID Primary Keys | JSONB
-- Generated from PLAN_02A (Audit-Fixed 2026-05-10)
-- ═══════════════════════════════════════════════════════════

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ─── 1. ORGANIZATIONS ───
CREATE TABLE organizations (
    org_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    tier        TEXT NOT NULL DEFAULT 'STANDARD' CHECK (tier IN ('STANDARD','PREMIUM','ENTERPRISE')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO organizations (org_id, name, tier) VALUES
    ('00000000-0000-0000-0000-000000000001', 'EVIDRA Default Org', 'ENTERPRISE');

-- ─── 2. USERS ───
CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id        UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001' REFERENCES organizations(org_id),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'INVESTIGATOR'
                    CHECK (role IN ('ADMIN','INVESTIGATOR','SUPERVISOR','PATHOLOGIST','LEGAL','VIEWER')),
    department    TEXT,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 3. CASES ───
CREATE TABLE cases (
    case_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id        UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001' REFERENCES organizations(org_id),
    case_number   TEXT UNIQUE NOT NULL DEFAULT '',
    title         TEXT NOT NULL,
    description   TEXT,
    status        TEXT NOT NULL DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN','IN_ANALYSIS','PAUSED_FOR_REVIEW','REVIEW','CLOSED','ARCHIVED')),
    risk_level    TEXT DEFAULT 'MEDIUM'
                    CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    location      TEXT,
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

-- ─── 4. CASE FILES ───
CREATE TABLE case_files (
    file_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    s3_key        TEXT NOT NULL,
    mime_type     TEXT,
    file_size_bytes BIGINT,
    doc_type      TEXT NOT NULL
                    CHECK (doc_type IN ('AUTOPSY_REPORT','CDR','FINANCIAL_RECORDS',
                           'DEVICE_DATA','CCTV','WITNESS_STATEMENT','POLICE_REPORT','OTHER')),
    status        TEXT DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','PROCESSING','PROCESSED','FAILED')),
    sha256_hash   VARCHAR(64),
    uploaded_by   UUID REFERENCES users(user_id),
    uploaded_at   TIMESTAMPTZ DEFAULT NOW(),
    processed_at  TIMESTAMPTZ
);

CREATE INDEX idx_case_files_case ON case_files(case_id);
CREATE INDEX idx_case_files_doc_type ON case_files(doc_type);

-- ─── 5. PIPELINE RUNS ───
CREATE TABLE pipeline_runs (
    pipeline_run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    triggered_by    UUID REFERENCES users(user_id),
    status          TEXT DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING','RUNNING','PAUSED_FOR_REVIEW','PARTIAL','COMPLETE','FAILED','CANCELLED')),
    agent_plan      JSONB NOT NULL DEFAULT '{}',
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    run_version     INT DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pipeline_runs_case ON pipeline_runs(case_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);

-- ─── 6. AGENT TASKS ───
CREATE TABLE agent_tasks (
    task_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    agent_id        TEXT NOT NULL,
    status          TEXT DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING','WAITING','DISPATCHED','RUNNING','COMPLETE','FAILED','SKIPPED')),
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

-- ─── 7. AGENT RESULTS ───
CREATE TABLE agent_results (
    result_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    agent_id        TEXT NOT NULL,
    result_data     JSONB NOT NULL DEFAULT '{}',
    confidence      FLOAT,
    warnings        TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_agent_results_unique ON agent_results(pipeline_run_id, agent_id);
CREATE INDEX idx_agent_results_pipeline ON agent_results(pipeline_run_id);
CREATE INDEX idx_agent_results_case ON agent_results(case_id);

-- ─── 8. REPLAY STEPS (Audit Trail — IMMUTABLE) ───
CREATE TABLE replay_steps (
    step_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    agent_id        TEXT NOT NULL,
    step_type       TEXT NOT NULL
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
CREATE INDEX idx_replay_steps_case ON replay_steps(case_id);
CREATE INDEX idx_replay_steps_agent ON replay_steps(agent_id);
CREATE INDEX idx_replay_steps_ts ON replay_steps(timestamp);

-- ─── 9. CANONICAL CDR EVENTS ───
CREATE TABLE canonical_cdr_events (
    event_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id             UUID NOT NULL REFERENCES cases(case_id),
    file_id             UUID REFERENCES case_files(file_id),
    source_msisdn       TEXT,
    event_timestamp     TIMESTAMPTZ NOT NULL,
    event_type          TEXT NOT NULL
                          CHECK (event_type IN ('MOC','MTC','SMS_MO','SMS_MT','DATA','GPRS')),
    duration_seconds    INT DEFAULT 0,
    counterparty_msisdn TEXT,
    cell_tower_id       TEXT,
    imei                TEXT,
    lat                 FLOAT,
    lon                 FLOAT,
    raw_data            JSONB DEFAULT '{}'
);

CREATE INDEX idx_cdr_case ON canonical_cdr_events(case_id);
CREATE INDEX idx_cdr_timestamp ON canonical_cdr_events(event_timestamp);
CREATE INDEX idx_cdr_tower ON canonical_cdr_events(cell_tower_id);
CREATE INDEX idx_cdr_msisdn ON canonical_cdr_events(source_msisdn);

-- ─── 10. CANONICAL FINANCIAL EVENTS ───
CREATE TABLE canonical_financial_events (
    event_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL REFERENCES cases(case_id),
    file_id       UUID REFERENCES case_files(file_id),
    timestamp     TIMESTAMPTZ NOT NULL,
    txn_type      TEXT NOT NULL CHECK (txn_type IN ('DEBIT','CREDIT')),
    amount        NUMERIC(15,2) NOT NULL,
    currency      TEXT DEFAULT 'INR',
    narration     TEXT,
    category      TEXT,
    balance_after NUMERIC(15,2),
    counterparty  TEXT,
    bank_name     TEXT,
    raw_data      JSONB DEFAULT '{}'
);

CREATE INDEX idx_fin_case ON canonical_financial_events(case_id);
CREATE INDEX idx_fin_timestamp ON canonical_financial_events(timestamp);
CREATE INDEX idx_fin_amount ON canonical_financial_events(amount);

-- ─── 11. ENTITY TRACKS ───
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

-- ─── 12. COLLISION EVENTS ───
CREATE TABLE collision_events (
    collision_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    time_start      TIMESTAMPTZ,
    time_end        TIMESTAMPTZ,
    collision_type  TEXT CHECK (collision_type IN ('CO_PRESENCE','CONSISTENCY','TEMPORAL_OVERLAP')),
    participants    JSONB DEFAULT '[]',
    region_id       TEXT,
    confidence      FLOAT DEFAULT 0.5,
    explanation     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_collision_case ON collision_events(case_id);

-- ─── 13. HOTSPOTS ───
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

-- ─── 14. CLAIMS ───
CREATE TABLE claims (
    claim_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    text            TEXT NOT NULL,
    normalized_text TEXT,
    polarity        TEXT DEFAULT 'ASSERT'
                      CHECK (polarity IN ('ASSERT','DENY','UNCERTAIN')),
    claim_type      TEXT DEFAULT 'EVENT'
                      CHECK (claim_type IN ('EVENT','STATE','ALIBI','CAUSAL','MENTAL_STATE','TEMPORAL')),
    certainty       FLOAT DEFAULT 0.5,
    source_agent    TEXT,
    time_info       TIMESTAMPTZ,
    location_info   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_claims_case ON claims(case_id);

-- ─── 15. CLAIM RELATIONS ───
CREATE TABLE claim_relations (
    relation_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id       UUID NOT NULL REFERENCES cases(case_id),
    from_claim_id UUID NOT NULL REFERENCES claims(claim_id),
    to_claim_id   UUID NOT NULL REFERENCES claims(claim_id),
    relation      TEXT NOT NULL CHECK (relation IN ('CONTRADICTS','SUPPORTS','REFINES','TEMPORALLY_BEFORE')),
    confidence    FLOAT NOT NULL DEFAULT 0.5,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clrel_case ON claim_relations(case_id);

-- ─── 16. EVIDENCE-CLAIM LINKS ───
CREATE TABLE evidence_claim_links (
    link_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id        UUID NOT NULL REFERENCES cases(case_id),
    claim_id       UUID REFERENCES claims(claim_id),
    evidence_id    UUID,
    evidence_kind  TEXT,
    label          TEXT NOT NULL
                     CHECK (label IN ('SUPPORTS','REFUTES','PARTIAL_SUPPORT','PARTIAL_REFUTE','NOT_ENOUGH_INFO','IRRELEVANT')),
    confidence     FLOAT DEFAULT 0.5,
    explanation    TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ecl_case ON evidence_claim_links(case_id);
CREATE INDEX idx_ecl_claim ON evidence_claim_links(claim_id);

-- ─── 17. CLAIM VERDICTS ───
CREATE TABLE claim_verdicts (
    verdict_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id        UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
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

CREATE INDEX idx_cv_claim ON claim_verdicts(claim_id);

-- ─── 18. HYPOTHESIS HISTORY ───
CREATE TABLE hypothesis_history (
    history_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    hypothesis_key  TEXT NOT NULL
                      CHECK (hypothesis_key IN ('NATURAL','ACCIDENT','SUICIDE','HOMICIDE','UNDETERMINED')),
    probability     FLOAT NOT NULL,
    trend           TEXT DEFAULT 'STABLE' CHECK (trend IN ('UP','DOWN','STABLE')),
    evidence_summary TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hyp_case ON hypothesis_history(case_id);
CREATE INDEX idx_hyp_pipeline ON hypothesis_history(pipeline_run_id);

-- ─── 19. CAUSAL GRAPH NODES ───
CREATE TABLE causal_graph_nodes (
    node_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    label           TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('HYPOTHESIS','CLAIM','EVIDENCE','AGENT','EVENT')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cgn_case ON causal_graph_nodes(case_id);

-- ─── 20. CAUSAL GRAPH EDGES ───
CREATE TABLE causal_graph_edges (
    edge_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    source_node_id  UUID REFERENCES causal_graph_nodes(node_id),
    target_node_id  UUID REFERENCES causal_graph_nodes(node_id),
    relation        TEXT CHECK (relation IN ('SUPPORTS','CONTRADICTS','NEUTRAL','CAUSES','CORRELATES')),
    strength        FLOAT DEFAULT 0.5,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cge_case ON causal_graph_edges(case_id);

-- ─── 21. UNCERTAINTY REPORTS ───
CREATE TABLE uncertainty_reports (
    report_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    bias_flags      JSONB DEFAULT '[]',
    escalation_recs JSONB DEFAULT '[]',
    overall_score   FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 22. NBE SUGGESTIONS ───
CREATE TABLE nbe_suggestions (
    suggestion_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    kind            TEXT,
    label           TEXT,
    description     TEXT,
    action_type     TEXT DEFAULT 'COLLECT_EVIDENCE'
                      CHECK (action_type IN ('COLLECT_EVIDENCE','RERUN_AGENT','MANUAL_REVIEW','EXTERNAL_CONSULT')),
    priority_score  FLOAT DEFAULT 0.5,
    expected_ig     FLOAT DEFAULT 0.0,
    status          TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING','ACCEPTED','DISMISSED')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nbe_case ON nbe_suggestions(case_id);

-- ─── 23. NBE FEEDBACK ───
CREATE TABLE nbe_feedback (
    feedback_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suggestion_id UUID NOT NULL REFERENCES nbe_suggestions(suggestion_id),
    case_id       UUID NOT NULL REFERENCES cases(case_id),
    action_taken  TEXT NOT NULL CHECK (action_taken IN ('ACCEPTED','IGNORED','REJECTED','NOT_POSSIBLE')),
    outcome       TEXT CHECK (outcome IN ('HELPFUL','NOT_HELPFUL','UNKNOWN')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── 24. AUDIT LOG (Append-Only — IMMUTABLE) ───
CREATE TABLE audit_log (
    log_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id     UUID REFERENCES cases(case_id),
    user_id     UUID REFERENCES users(user_id),
    actor       TEXT,
    action      TEXT NOT NULL,
    resource    TEXT,
    resource_id UUID,
    details     JSONB DEFAULT '{}',
    prev_entry_hash TEXT DEFAULT 'GENESIS',
    entry_hash  TEXT,
    ip_address  INET,
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);

-- ─── 25. CHAIN OF CUSTODY (Append-Only — IMMUTABLE) ───
CREATE TABLE chain_of_custody (
    custody_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id     UUID REFERENCES cases(case_id),
    file_id     UUID NOT NULL REFERENCES case_files(file_id),
    action      TEXT NOT NULL,
    actor       TEXT,
    actor_id    UUID REFERENCES users(user_id),
    sha256_at_action VARCHAR(64),
    file_hash   TEXT,
    details     TEXT,
    notes       TEXT,
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_custody_file ON chain_of_custody(file_id);

-- ─── 26. TIMELINE EVENTS (Unified) ───
CREATE TABLE timeline_events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    timestamp       TIMESTAMPTZ NOT NULL,
    source          TEXT NOT NULL CHECK (source IN ('PHONE','FINANCIAL','DEVICE','WITNESS','FORENSIC','SYSTEM')),
    event_type      TEXT,
    description     TEXT,
    anomaly_score   FLOAT DEFAULT 0.0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_timeline_case ON timeline_events(case_id);
CREATE INDEX idx_timeline_ts ON timeline_events(timestamp);

-- ─── 27. ANOMALY WINDOWS ───
CREATE TABLE anomaly_windows (
    window_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    time_start      TIMESTAMPTZ,
    time_end        TIMESTAMPTZ,
    ae_score        FLOAT,
    if_score        FLOAT,
    fused_score     FLOAT NOT NULL,
    label           TEXT CHECK (label IN ('CRITICAL','INTERESTING','MINOR')),
    factors         JSONB DEFAULT '[]',
    explanation     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_anomaly_case ON anomaly_windows(case_id);

-- ─── 28. REPORT SNAPSHOTS ───
CREATE TABLE report_snapshots (
    report_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    pipeline_run_id UUID REFERENCES pipeline_runs(pipeline_run_id),
    report_type     TEXT DEFAULT 'FULL' CHECK (report_type IN ('FULL','SUMMARY','EXECUTIVE')),
    sections        JSONB NOT NULL DEFAULT '[]',
    narrative       TEXT,
    generated_by    UUID REFERENCES users(user_id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 29. SESSIONS ───
CREATE TABLE sessions (
    session_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(user_id),
    token_hash  TEXT,
    ip_address  INET,
    user_agent  TEXT,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions(user_id);

-- ─── 30. MODEL CALIBRATION STATS ───
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

-- Auto-audit on case_files insert
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
-- IMMUTABILITY TRIGGERS — Court Readiness
-- Prevent UPDATE/DELETE on append-only forensic tables
-- ═══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION prevent_update_delete() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'UPDATE/DELETE not permitted on append-only table %', TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_immutable BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_custody_immutable BEFORE UPDATE OR DELETE ON chain_of_custody
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_replay_immutable BEFORE UPDATE OR DELETE ON replay_steps
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();


-- ═══════════════════════════════════════════════════════════
-- SEED DATA (Development)
-- ═══════════════════════════════════════════════════════════

-- Default admin user (password: admin123)
INSERT INTO users (email, password_hash, full_name, role) VALUES
    ('admin@evidra.gov', '$2b$12$LJ3m4ys4dF0G9q2o5h0rAOe.TV/0YVJz8.5BW0dO9.CQ3MfR2zEPi', 'System Admin', 'ADMIN'),
    ('investigator@police.gov', '$2b$12$LJ3m4ys4dF0G9q2o5h0rAOe.TV/0YVJz8.5BW0dO9.CQ3MfR2zEPi', 'Inspector Singh', 'INVESTIGATOR');

-- Seed model calibration entries
INSERT INTO model_calibration_stats (model_id, model_type, calibration_status, training_data_note) VALUES
    ('gemini-2.0-flash', 'LLM', 'UNCALIBRATED', 'Pre-trained LLM, no domain calibration'),
    ('isolation_forest_v1', 'ML', 'UNCALIBRATED', 'Trained on synthetic anomaly data'),
    ('henssge_nomogram', 'RULE', 'CALIBRATED', 'Physics-based model, empirically validated'),
    ('bayesian_hypothesis', 'HYBRID', 'UNCALIBRATED', 'Prior-initialized, calibrated during pipeline run');
