# CANONICAL SPEC 03 — Contradiction Resolutions & Canonical Decisions
**Status:** FINAL | All 8 contradictions resolved with binding decisions

---

## CTR-01 RESOLVED: Case Status Enum

**Decision:** Use `OPEN | IN_ANALYSIS | REVIEW | CLOSED`

**Rationale:** `IN_ANALYSIS` is more descriptive than `TRIAGE` for a forensic context where agents are actively processing evidence.

**Affected files:** Backend API Spec.txt → update status enum
```
status IN ('OPEN', 'IN_ANALYSIS', 'REVIEW', 'CLOSED')
```

---

## CTR-02 RESOLVED: Orchestrator Tier Numbers

**Decision:** Use the **8-tier model** defined in CANONICAL_01:
```
Tier 0: evidence_parser, ocr
Tier 1: format_normalizer
Tier 2: autopsy, cdr, financial, image
Tier 3: tod, timeline_anomaly, collision
Tier 4: hotspot, claim_extractor
Tier 5: evidence_claim_mapper, hypothesis_manager, bias_uncertainty
Tier 6: nbe_agent
Tier 7: reasoning_replay
```

**Rationale:** The old 6-tier model in `A to Z pipeline.txt` and the 5-tier in `Orchestrator.txt` were both incomplete. The 8-tier model properly sequences all 17 agents with correct dependency resolution.

---

## CTR-03 RESOLVED: WebSocket Endpoint

**Decision:** Single global endpoint with channel subscription
```
Endpoint: wss://<host>/ws
Auth: Bearer token in first message after connect
Subscription: Client sends { "subscribe": ["case:<case_id>", "global"] }
```

**Event envelope:**
```json
{
  "channel": "case:550e8400...",
  "event": "pipeline_progress",
  "data": { "progress": 45, "current_agent": "tod_agent" },
  "timestamp": "2026-05-10T02:00:00Z"
}
```

**Fallback:** `GET /api/v1/cases/{id}/pipeline/status` polling every 5s if WS fails.

---

## CTR-04 RESOLVED: Hypothesis Categories

**Decision:** 5 categories internally, 4 displayed in UI
```
Internal: NATURAL | ACCIDENT | SUICIDE | HOMICIDE | UNDETERMINED
UI display: Show all 5 as hypothesis pills
UNDETERMINED pill: shown only when its probability > 0.05, displayed as grey/muted pill
```

**When to use UNDETERMINED:**
- When no hypothesis exceeds 0.40 confidence
- When Bias Monitor flags insufficient evidence
- When VerdictAggregator returns `NOT_ENOUGH_INFO` for critical claims

---

## CTR-05 RESOLVED: API Base Path

**Decision:** All REST endpoints use `/api/v1/` prefix
```
/api/v1/auth/login
/api/v1/cases
/api/v1/cases/{case_id}/files
/api/v1/cases/{case_id}/pipeline/trigger
/api/v1/cases/{case_id}/timeline
/api/v1/cases/{case_id}/hotspots
/api/v1/cases/{case_id}/graph
/api/v1/cases/{case_id}/replay
/api/v1/agents/{agent_id}/status
```

**WebSocket:** `/ws` (no prefix — separate upgrade path in Nginx)

---

## CTR-06 RESOLVED: File Upload Endpoint

**Decision:** Single unified upload endpoint with doc_type parameter
```
POST /api/v1/cases/{case_id}/files
Content-Type: multipart/form-data
Body: file=<binary>, doc_type=<CDR|AUTOPSY_REPORT|FINANCIAL_RECORDS|DEVICE_DATA|WITNESS_STATEMENT|OTHER>
```

**Response:**
```json
{
  "file_id": "uuid",
  "doc_type": "CDR",
  "status": "PENDING",
  "size_bytes": 245000,
  "checksum_sha256": "abc123..."
}
```

**Rationale:** Separate per-type endpoints (`/evidence/autopsy`, `/evidence/cdr`) create unnecessary API surface. A single endpoint with a `doc_type` field is simpler and more extensible.

---

## CTR-07 RESOLVED: Autopsy LLM Model

**Decision:** Use `gemini-2.0-flash` as PRIMARY, configurable via environment variable

```yaml
# .env canonical
LLM_PROVIDER=gemini           # gemini | openai | deepseek
LLM_MODEL_AUTOPSY=gemini-2.0-flash
LLM_MODEL_NARRATIVE=gemini-2.0-flash
LLM_MODEL_HYPOTHESIS=gemini-2.0-flash
LLM_TEMPERATURE_EXTRACT=0.1   # structured extraction
LLM_TEMPERATURE_NARRATIVE=0.3 # narrative generation
GEMINI_API_KEY=<key>
```

**LLM Gateway abstraction:**
```python
class LLMGateway:
    """Provider-agnostic LLM client. All agents call this, never raw APIs."""
    
    async def complete(self, 
        task: str,          # "autopsy_extract" | "narrative" | "nli_classify"
        prompt: str,
        temperature: float = None,
        max_tokens: int = 2000,
        response_format: str = "json"  # "json" | "text"
    ) -> LLMResponse:
        model = self._get_model_for_task(task)
        provider = self._get_provider(model)
        return await provider.call(model, prompt, temperature, max_tokens)
```

**Rationale:** `II-Medical-32B` is a specialized model not easily hostable. Gemini 2.0 Flash offers strong medical text extraction at low latency. The abstraction layer allows swapping without code changes.

---

## CTR-08 RESOLVED: Frontend Framework

**Decision:** Next.js 14 + React 18 + Vanilla CSS (no Tailwind)

```
Framework: Next.js 14 (App Router)
State: Zustand (lightweight, no Redux boilerplate)
Charts: Recharts + D3.js (for causal graph)
WS client: native WebSocket with reconnect wrapper
Styling: Vanilla CSS with CSS variables (per Frontend Spec v1.0 design system)
```

**Color palette (canonical from Frontend Spec v1.0):**
```css
:root {
  --bg-base: #05060A;
  --bg-elevated: #0F1015;
  --bg-glass: rgba(255, 255, 255, 0.04);
  --border-subtle: rgba(255, 255, 255, 0.06);
  --text-primary: #F9FAFB;
  --text-muted: #9CA3AF;
  --text-faint: #6B7280;
  --accent-cyan: #22C7D5;
  --accent-blue: #38BDF8;
  --anomaly-red: #F97373;
  --warning-amber: #FBBF24;
  --success-green: #22C55E;
  --tod-band: rgba(34, 199, 213, 0.18);
  --anomaly-heat: rgba(251, 113, 133, 0.22);
}
```

**Typography:** `Inter` (body), `Instrument Serif` (display headings)
