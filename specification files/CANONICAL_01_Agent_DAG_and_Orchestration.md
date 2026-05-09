# CANONICAL SPEC 01 — Complete Agent DAG & Orchestration
**Status:** FINAL | **Supersedes:** Orchestrator.txt, A to Z pipeline.txt (DAG sections only)

---

## 1. Complete Agent Registry (15 Agents + 3 Infrastructure)

| ID | Agent | Port | Tier | Category | Required |
|----|-------|------|------|----------|----------|
| M-01 | evidence_parser | 8010 | 0 | INGEST | YES |
| M-02 | ocr | 8011 | 0 | INGEST | CONDITIONAL |
| M-03 | format_normalizer | 8012 | 1 | INGEST | YES |
| M-04 | autopsy_agent | 8020 | 2 | NLP | CONDITIONAL |
| M-05 | cdr_analyzer | 8021 | 2 | TABULAR | CONDITIONAL |
| M-06 | financial_analyzer | 8022 | 2 | TABULAR | CONDITIONAL |
| M-07 | image_agent | 8023 | 2 | VISION | CONDITIONAL |
| M-08 | tod_agent | 8030 | 3 | HYBRID | CONDITIONAL |
| M-09 | timeline_anomaly | 8031 | 3 | ML | CONDITIONAL |
| M-10 | collision_agent | 8032 | 3 | TABULAR | CONDITIONAL |
| M-11 | hotspot_engine | 8040 | 4 | FUSION | CONDITIONAL |
| M-12 | claim_extractor | 8041 | 4 | NLP | CONDITIONAL |
| M-13 | evidence_claim_mapper | 8050 | 5 | NLP | CONDITIONAL |
| M-14 | hypothesis_manager | 8051 | 5 | REASONING | YES |
| M-15 | bias_uncertainty | 8052 | 5 | XAI | YES |
| M-16 | nbe_agent | 8060 | 6 | GUIDANCE | YES |
| M-17 | reasoning_replay | 8061 | 7 | AUDIT | YES |

Infrastructure: postgres (5432), redis (6379), minio (9000/9001), nginx (80/443)
Gateway: api_gateway (8000), orchestrator (8001), frontend (3000)

## 2. Canonical 8-Tier Execution DAG

```
TIER 0 — INGESTION (Parallel):
  evidence_parser ──┬── [if scanned] → ocr
                    │
TIER 1 — NORMALIZATION:
  format_normalizer ← (evidence_parser + ocr)
                    │
TIER 2 — DOMAIN ANALYSIS (Parallel, all wait for format_normalizer):
  ├── autopsy_agent        [if AUTOPSY_REPORT uploaded]
  ├── cdr_analyzer         [if CDR uploaded]
  ├── financial_analyzer   [if FINANCIAL_RECORDS uploaded]
  └── image_agent          [if DEVICE_DATA/CCTV uploaded]
                    │
TIER 3 — TEMPORAL INTELLIGENCE (Parallel, waits for Tier 2):
  ├── tod_agent            ← needs autopsy_agent
  ├── timeline_anomaly     ← needs cdr + financial + image (any available)
  └── collision_agent      ← needs image + cdr (entity tracks)
                    │
TIER 4 — FUSION (Parallel, waits for Tier 3):
  ├── hotspot_engine       ← needs tod + timeline_anomaly + collision
  └── claim_extractor      ← needs autopsy + cdr + financial (text sources)
                    │
TIER 5 — REASONING (Parallel, waits for Tier 4):
  ├── evidence_claim_mapper ← needs claim_extractor + all evidence
  ├── hypothesis_manager    ← needs hotspot + claim verdicts + all prior
  └── bias_uncertainty      ← needs all agent outputs
                    │
TIER 6 — GUIDANCE:
  └── nbe_agent            ← needs hypothesis + bias + hotspots
                    │
TIER 7 — AUDIT:
  └── reasoning_replay     ← needs ALL replay_steps from ALL agents
```

## 3. Canonical Agent Plan Builder

```python
def build_agent_plan(doc_types: Set[str], has_scanned: bool) -> Dict[str, AgentConfig]:
    plan = {}

    # TIER 0
    plan["evidence_parser"] = {"tier": 0, "depends_on": [], "required": True}
    if has_scanned:
        plan["ocr"] = {"tier": 0, "depends_on": [], "required": False}

    # TIER 1
    plan["format_normalizer"] = {
        "tier": 1,
        "depends_on": ["evidence_parser"] + (["ocr"] if has_scanned else []),
        "required": True
    }

    # TIER 2 — conditional on doc types
    tier2_agents = []
    if "AUTOPSY_REPORT" in doc_types:
        plan["autopsy_agent"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("autopsy_agent")
    if "CDR" in doc_types:
        plan["cdr_analyzer"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("cdr_analyzer")
    if "FINANCIAL_RECORDS" in doc_types:
        plan["financial_analyzer"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("financial_analyzer")
    if "DEVICE_DATA" in doc_types:
        plan["image_agent"] = {"tier": 2, "depends_on": ["format_normalizer"]}
        tier2_agents.append("image_agent")

    # TIER 3 — temporal intelligence
    if "autopsy_agent" in plan:
        plan["tod_agent"] = {"tier": 3, "depends_on": ["autopsy_agent"]}
    digital_agents = [a for a in ["cdr_analyzer", "financial_analyzer", "image_agent"] if a in plan]
    if digital_agents:
        plan["timeline_anomaly"] = {"tier": 3, "depends_on": digital_agents}
    if len(digital_agents) >= 1 and "image_agent" in plan:
        plan["collision_agent"] = {"tier": 3, "depends_on": digital_agents}

    # TIER 4 — fusion
    hotspot_deps = [a for a in ["tod_agent", "timeline_anomaly", "collision_agent"] if a in plan]
    if len(hotspot_deps) >= 2:
        plan["hotspot_engine"] = {"tier": 4, "depends_on": hotspot_deps}
    text_sources = [a for a in ["autopsy_agent", "cdr_analyzer", "financial_analyzer"] if a in plan]
    if text_sources:
        plan["claim_extractor"] = {"tier": 4, "depends_on": text_sources}

    # TIER 5 — reasoning
    tier5_deps = [a for a in plan if plan[a].get("tier", 0) <= 4]
    if "claim_extractor" in plan:
        plan["evidence_claim_mapper"] = {"tier": 5, "depends_on": ["claim_extractor"] + tier2_agents}
    plan["hypothesis_manager"] = {"tier": 5, "depends_on": tier5_deps, "required": True}
    plan["bias_uncertainty"] = {"tier": 5, "depends_on": tier5_deps, "required": True}

    # TIER 6 — guidance
    plan["nbe_agent"] = {
        "tier": 6,
        "depends_on": ["hypothesis_manager", "bias_uncertainty"],
        "required": True
    }

    # TIER 7 — audit
    plan["reasoning_replay"] = {"tier": 7, "depends_on": list(plan.keys()), "required": True}

    return plan
```

## 4. Graceful Degradation Policy

| Agent | If it fails... | Pipeline continues? |
|-------|---------------|---------------------|
| evidence_parser | PIPELINE ABORT | ❌ No |
| ocr | Skip OCR, use raw text | ✅ Yes |
| format_normalizer | PIPELINE ABORT | ❌ No |
| autopsy_agent | Skip TOD, reduce hypothesis confidence | ✅ Yes (degraded) |
| cdr_analyzer | Skip CDR anomalies | ✅ Yes (degraded) |
| financial_analyzer | Skip financial analysis | ✅ Yes (degraded) |
| image_agent | Skip CCTV tracks | ✅ Yes (degraded) |
| tod_agent | Hypothesis uses autopsy only | ✅ Yes (degraded) |
| timeline_anomaly | Skip anomaly windows | ✅ Yes (degraded) |
| collision_agent | Skip collision events | ✅ Yes (degraded) |
| hotspot_engine | Hypothesis uses raw evidence | ✅ Yes (degraded) |
| claim_extractor | Skip argument graph | ✅ Yes (degraded) |
| evidence_claim_mapper | Skip verdicts | ✅ Yes (degraded) |
| hypothesis_manager | Report "UNDETERMINED" | ✅ Yes (degraded) |
| bias_uncertainty | Skip bias warnings | ✅ Yes (degraded) |
| nbe_agent | Skip suggestions | ✅ Yes |
| reasoning_replay | PIPELINE ABORT (audit required) | ❌ No |

## 5. Retry & Circuit Breaker

```python
RETRY_POLICY = {
    "max_attempts": 3,
    "backoff_seconds": [5, 15, 45],
    "non_retryable_errors": ["INVALID_DATA", "SCHEMA_ERROR", "AUTH_FAILED"],
    "timeout_seconds": {
        "default": 120,
        "ocr": 300,          # OCR can be slow for large docs
        "image_agent": 300,  # YOLO inference
        "reasoning_replay": 60
    }
}

CIRCUIT_BREAKER = {
    "failure_threshold": 5,       # 5 consecutive failures
    "recovery_timeout_sec": 300,  # 5 min before retry
    "half_open_max_calls": 1      # 1 test call in half-open
}
```

## 6. Pipeline Re-run Versioning

- Each `trigger_pipeline` creates a NEW `pipeline_run_id`
- Old `agent_results` are NEVER deleted — kept for audit trail
- `agent_results` has `(pipeline_run_id, agent_id)` unique index
- UI shows latest run by default, with "History" dropdown to compare
- `hypothesis_history` table tracks probability changes across runs
