# PLAN 00 — Master Sprint Schedule (24-Hour Execution Blueprint)
**Document Type:** COORDINATION | **Priority:** CRITICAL | **Version:** 2.0

---

## 1. Sprint Overview

| Parameter | Value |
|-----------|-------|
| **Sprint Duration** | 24 hours (continuous) |
| **Team Size** | 2 developers (Dev A + Dev B) |
| **Architecture** | Monorepo (Git, single `aiventra/` root) |
| **Backend** | Python 3.11 + FastAPI + PostgreSQL 16 + Redis 7 |
| **Frontend** | Next.js 14 + Recharts + D3.js + Vanilla CSS |
| **ML** | PyTorch (AE), scikit-learn (RF, IF), SciPy (Henssge) |
| **LLM** | Google Gemini 2.0 Flash via `LLMGateway` singleton |
| **Comms** | Redis Streams (agent tasks), WebSocket (UI telemetry) |
| **Dev A Machine** | RTX 3050 4GB VRAM, handles all ML training |
| **Dev B Machine** | Standard dev machine, handles frontend + integration |

---

## 2. Hour-by-Hour Schedule

### Phase 0: Foundation (Hours 0–1)
| Hour | Dev A (Backend Lead) | Dev B (Frontend Lead) | Sync Point |
|------|---------------------|----------------------|------------|
| H0:00 | `PLAN_01` — Initialize monorepo, install Python deps, create folder structure | `PLAN_01` — Initialize Next.js app, install npm deps | Git initial commit |
| H0:30 | `PLAN_02A` — Run `init.sql`, verify all 24 tables, test connection pool | `PLAN_12` — Create `globals.css` design system, all CSS variables | — |
| H1:00 | `PLAN_02B` — Redis client, MinIO client, .env validation | `PLAN_12` — Sidebar, TopHeader, Layout shell | ✅ **SYNC-1**: Both push, pull, verify no conflicts |

### Phase 1: Core Services (Hours 1–3)
| Hour | Dev A | Dev B | Sync Point |
|------|-------|-------|------------|
| H1:00 | `PLAN_03A` — LLM Gateway: Gemini client, retry logic, JSON extraction | `PLAN_19` — Shared components: MetricCard, StatusBadge, ConfidencePill | — |
| H1:30 | `PLAN_03B` — BaseAgent: ABC class, run() lifecycle, replay_steps logging | `PLAN_19` — LoadingSpinner, AgentPill, InspectorPanel | — |
| H2:00 | `PLAN_04A` — FastAPI app factory, CORS, JWT auth, /auth endpoints | `PLAN_13A` — Login page with register/login toggle | — |
| H2:30 | `PLAN_04B` — /cases CRUD endpoints, file upload to MinIO | `PLAN_13B` — Case Lobby: grid, filters, create modal | ✅ **SYNC-2**: Dev B tests login against Dev A's API |
| H3:00 | `PLAN_04C` — Pipeline trigger, status, WebSocket endpoints | `PLAN_13C` — Case Workspace shell, tab router | — |

### Phase 2: Ingestion Agents (Hours 3–5)
| Hour | Dev A | Dev B | Sync Point |
|------|-------|-------|------------|
| H3:00 | `PLAN_05` — Orchestrator: DAG builder, tier dispatcher, completion monitor | `PLAN_14A` — CaseHeader component with file upload + pipeline trigger | — |
| H4:00 | `PLAN_06A` — Evidence Parser agent | `PLAN_14B` — PipelineStrip component (animated status nodes) | — |
| H4:30 | `PLAN_06B` — OCR Worker agent | `PLAN_14C` — TimelineTab: Recharts AreaChart with anomaly gradient | — |
| H5:00 | `PLAN_06C` — Format Normalizer agent (PII masking) | `PLAN_14D` — HotspotsTab: ranked hotspot cards | ✅ **SYNC-3**: End-to-end file upload test |

### Phase 3: Domain Analysis Agents (Hours 5–9)
| Hour | Dev A | Dev B | Sync Point |
|------|-------|-------|------------|
| H5:00 | `PLAN_07A` — Autopsy Agent (LLM extraction prompt + validation) | `PLAN_14E` — CausalGraphTab: D3 force-directed graph | — |
| H6:00 | `PLAN_07B` — CDR Analyzer (multi-operator, normalization, z-score) | `PLAN_14F` — ReplayTab: step list with confidence colors | — |
| H7:00 | `PLAN_07C` — Financial Analyzer (transaction parsing, anomaly detection) | `PLAN_15A` — Command Center: metrics strip + agent grid | — |
| H8:00 | `PLAN_08A` — Image Agent (Gemini 2.0 multimodal) | `PLAN_15B` — Agent Directory with type filtering | ✅ **SYNC-4**: Verify Tier 2 agents produce correct output |

### Phase 4: Temporal Intelligence (Hours 9–13)
| Hour | Dev A | Dev B | Sync Point |
|------|-------|-------|------------|
| H9:00 | `PLAN_09A` — TOD Agent: Henssge physics solver | `PLAN_15C` — Agent Lab page (info + test bench) | — |
| H10:00 | `PLAN_09B` — TOD Agent: RF surrogate (synthetic data + training) | `PLAN_15D` — Pipeline Explorer (tier-grouped view) | — |
| H11:00 | `PLAN_09C` — TOD Agent: Bayesian Monte Carlo fusion + consistency check | `PLAN_16A` — XAI Studio: confidence gauges + agent breakdown | — |
| H12:00 | `PLAN_10A` — Timeline Anomaly: Autoencoder (PyTorch) | `PLAN_16B` — XAI Studio: hypothesis distribution cards | ✅ **SYNC-5**: TOD agent tested with synthetic autopsy data |
| H13:00 | `PLAN_10B` — Timeline Anomaly: Isolation Forest + score fusion | `PLAN_16C` — Report Builder page | — |

### Phase 5: Fusion & Reasoning (Hours 13–18)
| Hour | Dev A | Dev B | Sync Point |
|------|-------|-------|------------|
| H13:00 | `PLAN_11A` — Collision Agent (tower co-presence + rapid movement) | `PLAN_16D` — Audit & Chain of Custody page | — |
| H14:00 | `PLAN_11B` — Hotspot Engine (multi-modal fusion + TOD overlap) | `PLAN_17A` — WebSocket integration: live pipeline status | — |
| H15:00 | `PLAN_12A` — Claim Extractor (LLM atomic claim mining) | `PLAN_17B` — Real-time agent progress animations | ✅ **SYNC-6**: Hotspot data renders in HotspotsTab |
| H16:00 | `PLAN_12B` — Evidence-Claim Mapper (NLI classification) | `PLAN_18A` — Frontend polish: transitions, loading states | — |
| H17:00 | `PLAN_13A_BE` — Hypothesis Manager (Bayesian 5-way scoring) | `PLAN_18B` — Responsive design + mobile adaptations | — |
| H18:00 | `PLAN_13B_BE` — Bias & Uncertainty Monitor | `PLAN_18C` — Error handling, empty states, toast notifications | ✅ **SYNC-7**: Hypothesis pills display live data |

### Phase 6: Guidance, Audit & Integration (Hours 18–22)
| Hour | Dev A | Dev B | Sync Point |
|------|-------|-------|------------|
| H18:00 | `PLAN_14A_BE` — NBE Agent (evidence suggestions) | `PLAN_19A` — Connect all API endpoints to live backend | — |
| H19:00 | `PLAN_14B_BE` — Reasoning Replay Agent (narrative generation) | `PLAN_19B` — WebSocket: real-time replay step streaming | — |
| H20:00 | `PLAN_15_BE` — Unified Worker Runner (`--all` mode) | `PLAN_20` — End-to-end UI flow testing | ✅ **SYNC-8**: Full pipeline triggers from UI |
| H21:00 | `PLAN_16_BE` — Synthetic test data generation (Kumar case) | `PLAN_21` — Demo walkthrough preparation | — |

### Phase 7: Testing & Demo (Hours 22–24)
| Hour | Dev A | Dev B | Sync Point |
|------|-------|-------|------------|
| H22:00 | `PLAN_22` — Full integration test (upload → pipeline → results) | `PLAN_22` — UI verification against live pipeline | ✅ **SYNC-9**: End-to-end demo run |
| H23:00 | Bug fixes, edge cases, error handling | Bug fixes, visual polish, screenshot generation | — |
| H24:00 | Final commit, tag v1.0.0 | Final commit, README update | ✅ **SYNC-10**: Demo-ready |

---

## 3. Git Workflow

```
BRANCH STRATEGY:
  main              — protected, only merge via sync points
  dev/backend       — Dev A works here
  dev/frontend      — Dev B works here

SYNC PROTOCOL:
  1. Dev A: git add . && git commit -m "SYNC-N: [description]" && git push origin dev/backend
  2. Dev B: git add . && git commit -m "SYNC-N: [description]" && git push origin dev/frontend
  3. Dev A: git checkout main && git merge dev/backend && git merge dev/frontend && git push
  4. Both: git checkout dev/[branch] && git merge main
```

---

## 4. Risk Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Gemini API rate limit hit | HIGH | LLMGateway has exponential backoff (2s, 4s, 8s). Cache prompts in Redis. |
| PostgreSQL connection pool exhaustion | MEDIUM | Pool max=10, min=2. Each agent releases connections in `finally` block. |
| PyTorch OOM on RTX 3050 4GB | MEDIUM | Autoencoder uses 32-dim hidden layers. RF uses CPU only. Batch size ≤ 32. |
| Redis stream consumer lag | LOW | Use XREAD with BLOCK 5000ms. Consumer groups if needed. |
| Frontend ↔ Backend schema mismatch | HIGH | Shared type definitions in `PLAN_04C`. Dev B reads API docs before coding. |
| Git merge conflicts | MEDIUM | Strict directory separation: Dev A never touches `frontend/`, Dev B never touches `services/`. |

---

## 5. Definition of Done

A feature is DONE when:
- [ ] Code compiles/runs without errors
- [ ] All acceptance criteria from its PLAN document are met
- [ ] Results visible in database (for backend) or rendered in UI (for frontend)
- [ ] Committed and pushed to the correct branch
- [ ] No regressions in existing functionality

## 6. Emergency Procedures

If a critical path agent fails:
1. **Check logs** in terminal running `python -m services.worker --all`
2. **Verify Redis** is running: `redis-cli ping` → PONG
3. **Verify Postgres**: `psql -h localhost -U aiventra -d aiventra_db -c "SELECT 1"`
4. **LLM failures**: Check `GEMINI_API_KEY` in `.env`, verify quota at console.cloud.google.com
5. **Frontend build fails**: `rm -rf frontend/.next && npm run dev`
