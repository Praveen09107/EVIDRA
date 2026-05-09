# DEV B EXECUTION GUIDE — PART 1: Setup, Design System & Core Infrastructure
**Role:** Frontend Lead & Data Visualization Engineer
**Hardware:** Standard Dev Machine (no GPU required)
**Scope:** `frontend/` directory ONLY — never touch `services/`, `sql/`, `models/`
**Tech:** Next.js 14 (App Router) | Recharts | D3.js | Zustand | Vanilla CSS

---

## 1. YOUR MISSION IN DETAIL

You are responsible for the **entire visual layer** of AIVENTRA. Your job is to translate raw forensic intelligence data (JSON from Dev A's API) into a stunning, dark-themed, production-grade investigation dashboard. Every chart, every animation, every real-time status indicator — that is you.

**What success looks like at Hour 24:**
- An investigator opens the browser, logs in, creates a case, uploads 3 evidence files, clicks "Run Pipeline", and watches 17 AI agents light up one-by-one in real-time.
- They click into the Timeline tab and see a Recharts area chart with anomaly gradients.
- They click into XAI Studio and see hypothesis probabilities with color-coded confidence gauges.
- Everything feels smooth, polished, and professional.

---

## 2. YOUR FILE OWNERSHIP MAP

```
frontend/                          ← YOU OWN EVERYTHING HERE
├── app/
│   ├── globals.css                ← Design system (CSS variables, layout, animations)
│   ├── layout.js                  ← Root layout (imports Sidebar + TopHeader)
│   ├── page.js                    ← Root redirect → /cases
│   ├── login/page.js              ← JWT login/register
│   ├── cases/
│   │   ├── page.js                ← Case lobby (grid + create modal)
│   │   └── [caseId]/page.js       ← Case workspace (tabs + pipeline strip)
│   ├── command/page.js            ← Command center (global metrics)
│   ├── agents/
│   │   ├── page.js                ← Agent directory (17 agent cards)
│   │   └── [agentId]/page.js      ← Agent lab (individual agent detail)
│   ├── pipeline/[caseId]/page.js  ← Pipeline explorer (tier-grouped DAG view)
│   ├── xai/page.js                ← XAI & Uncertainty Studio
│   ├── reports/page.js            ← Report builder
│   └── audit/page.js              ← Audit & chain of custody
├── components/
│   ├── layout/
│   │   ├── Sidebar.js             ← Left navigation (7 links + branding)
│   │   ├── TopHeader.js           ← Date display + role + logout
│   │   └── InspectorPanel.js      ← Slide-in JSON inspector
│   ├── workspace/
│   │   ├── CaseHeader.js          ← Case title + file upload + trigger button
│   │   ├── PipelineStrip.js       ← Animated horizontal pipeline status
│   │   ├── TimelineTab.js         ← Recharts AreaChart with anomaly gradient
│   │   ├── HotspotsTab.js         ← Ranked hotspot cards
│   │   ├── CausalGraphTab.js      ← D3.js force-directed graph
│   │   └── ReplayTab.js           ← Reasoning replay step list
│   ├── agents/
│   │   └── AgentPill.js           ← Small pill showing agent name + status
│   └── shared/
│       ├── MetricCard.js          ← Large number with label (glassmorphism)
│       ├── StatusBadge.js         ← Colored pill for OPEN/RUNNING/COMPLETE/FAILED
│       ├── ConfidencePill.js      ← Percentage with color threshold
│       └── LoadingSpinner.js      ← Rotating circle with optional text
└── lib/
    ├── api.js                     ← REST client with automatic JWT injection
    ├── ws.js                      ← WebSocket client with auto-reconnect
    └── store.js                   ← Zustand global state store
```

**⛔ HARD BOUNDARY:** If you need a backend change (e.g., a new endpoint or different JSON shape), you must ask Dev A. Never write Python code. Never modify anything outside `frontend/`.

---

## 3. PHASE 1 — ENVIRONMENT SETUP (Hour 0:00–0:30)

### Step 3.1 — Initialize Next.js

```powershell
cd "d:\Program Files\forensic\aiventra"
npx -y create-next-app@14 frontend --js --no-tailwind --no-eslint --app --src-dir=false --import-alias="@/*"
```

**What this does:** Creates a Next.js 14 app using the App Router (not Pages Router), with JavaScript (not TypeScript), no Tailwind (we use vanilla CSS), and path aliases so `@/components/...` works.

### Step 3.2 — Install Dependencies

```powershell
cd "d:\Program Files\forensic\aiventra\frontend"
npm install recharts d3 zustand
```

| Package | Version | Purpose |
|---------|---------|---------|
| `recharts` | ^2.12 | Timeline charts, area charts, bar charts |
| `d3` | ^7.9 | Force-directed causal graph visualization |
| `zustand` | ^4.5 | Lightweight global state (replaces Redux) |

### Step 3.3 — Configure Next.js Proxy

**File: `frontend/next.config.js`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api calls to the FastAPI backend during development
  // This avoids CORS issues when calling from localhost:3000 → localhost:8000
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

> **Why a proxy?** Without this, the browser blocks cross-origin requests from `:3000` to `:8000`. Dev A also has CORS middleware on FastAPI, but the proxy is a belt-and-suspenders approach that eliminates all CORS headaches.

### Step 3.4 — Load Google Fonts

**File: `frontend/app/layout.js`** (initial version — you'll expand this later)

```jsx
import './globals.css';

export const metadata = {
  title: 'AIVENTRA — Forensic Intelligence Platform',
  description: 'AI-powered multi-agent forensic triage and analysis system',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        {/* Google Fonts: Inter (body), Outfit (headings), JetBrains Mono (code) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

### Step 3.5 — Verify Setup

```powershell
cd "d:\Program Files\forensic\aiventra\frontend"
npm run dev
```

Open `http://localhost:3000`. You should see the default Next.js page. If it loads, your environment is working.

---

## 4. PHASE 2 — DESIGN SYSTEM (Hour 0:30–1:30)

This is the visual DNA of AIVENTRA. Every component you build will reference these CSS variables. **Never hardcode hex colors in JSX.** Always use `var(--variable-name)`.

### Step 4.1 — Complete CSS File

**File: `frontend/app/globals.css`**

Replace the entire contents with the CSS from `PLAN_12_Frontend_Design_System.md`. The full CSS is there. Here are the critical design decisions explained:

**Color Palette Rationale:**
| Variable | Hex | Usage |
|----------|-----|-------|
| `--bg-dark` | `#0A0F1A` | Page background — near-black with blue undertone |
| `--bg-elevated` | `#111827` | Cards, sidebar, modals — slightly lighter than bg |
| `--accent-cyan` | `#22C7D5` | Primary action color — buttons, active nav, branding |
| `--accent-blue` | `#38BDF8` | Secondary accent — links, focus rings |
| `--success-green` | `#22C55E` | COMPLETE status, high confidence, positive trends |
| `--warning-amber` | `#FBBF24` | RUNNING status, medium confidence, IN_ANALYSIS |
| `--anomaly-red` | `#F97373` | FAILED status, anomalies, low confidence, hotspots |

**Hypothesis Colors (XAI Studio):**
| Hypothesis | Variable | Color | Rationale |
|-----------|----------|-------|-----------|
| HOMICIDE | `--hypothesis-homicide` | Red | Danger, violence |
| SUICIDE | `--hypothesis-suicide` | Amber | Caution |
| ACCIDENT | `--hypothesis-accident` | Green | Neutral |
| NATURAL | `--hypothesis-natural` | Blue | Calm |
| UNDETERMINED | `--hypothesis-undetermined` | Grey | Unknown |

**Typography:**
- `Inter` — Body text, UI labels (clean, highly legible at small sizes)
- `Outfit` — Page titles, section headers (modern geometric sans-serif)
- `JetBrains Mono` — Code blocks, case numbers, timestamps (monospaced)

**Layout System:**
- `.app-layout` — Flexbox: sidebar (240px fixed) + main content (flex: 1)
- `.sidebar` — Fixed left column, full viewport height
- `.scroll-area` — The only scrollable area (prevents double scrollbars)

**Animation Library:**
- `slideIn` — Page entry animation (opacity 0→1, translateY 10px→0)
- `pulse` — Agent RUNNING indicator (scale 1→1.05→1, opacity fade)
- Add `.animate-in` class to any page wrapper for smooth entry

### Step 4.2 — Additional CSS You Must Add (Not in PLAN_12)

Append these to the bottom of `globals.css`:

```css
/* ─── Badge ─── */
.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

/* ─── Confidence Bar ─── */
.confidence-bar {
  height: 4px;
  background: var(--border-subtle);
  border-radius: 2px;
  overflow: hidden;
}
.confidence-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}
.confidence-high { background: var(--success-green); }
.confidence-medium { background: var(--warning-amber); }
.confidence-low { background: var(--anomaly-red); }

/* ─── Table ─── */
table { font-size: 0.9rem; }
th { font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.75rem; }

/* ─── Scrollbar ─── */
.scroll-area::-webkit-scrollbar { width: 6px; }
.scroll-area::-webkit-scrollbar-track { background: transparent; }
.scroll-area::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 3px; }
.scroll-area::-webkit-scrollbar-thumb:hover { background: var(--text-faint); }

/* ─── Transitions ─── */
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
.card-glass:hover { border-color: rgba(255,255,255,0.1); }

/* ─── Modal Overlay ─── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}

/* ─── Toast Notification ─── */
.toast {
  position: fixed; bottom: 24px; right: 24px; z-index: 200;
  padding: 12px 20px; border-radius: 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  font-size: 0.85rem;
  animation: slideIn 0.3s ease;
}

/* ─── Empty State ─── */
.empty-state {
  text-align: center; padding: 80px 40px;
  color: var(--text-faint);
}
.empty-state h3 { color: var(--text-muted); margin-bottom: 8px; }

/* ─── Tab Bar ─── */
.tab-bar {
  display: flex; gap: 24px;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 12px; margin-bottom: 24px;
}
.tab-btn {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 0.9rem;
  padding: 4px 0; position: relative; transition: color 0.2s;
}
.tab-btn.active {
  color: var(--accent-cyan); font-weight: 600;
}
.tab-btn.active::after {
  content: ''; position: absolute; bottom: -13px; left: 0; right: 0;
  height: 2px; background: var(--accent-cyan); border-radius: 1px;
}

/* ─── Responsive ─── */
@media (max-width: 1200px) {
  .grid-4 { grid-template-columns: repeat(2, 1fr); }
  .grid-3 { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .sidebar { display: none; }
  .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
}
```

---

## 5. PHASE 3 — API & WEBSOCKET CLIENTS (Hour 1:30–2:00)

### Step 5.1 — REST API Client

**File: `frontend/lib/api.js`**

This is the ONLY file that makes HTTP requests. Every page imports `api` from here. Copy the exact implementation from `PLAN_12`. Key behaviors:

1. **JWT Auto-Injection:** Reads `localStorage.getItem('token')` and sets `Authorization: Bearer <token>` on every request.
2. **FormData Detection:** If `body` is a `FormData` instance (file uploads), it does NOT set `Content-Type` — the browser must set the `multipart/form-data` boundary automatically.
3. **Error Handling:** On non-2xx responses, it tries to parse the JSON error body and throws `Error(detail)`.

**Full API Method Reference (what Dev A provides):**

| Method | HTTP | Endpoint | Request Body | Response |
|--------|------|----------|-------------|----------|
| `api.login(email, pwd)` | POST | `/auth/login` | `{email, password}` | `{access_token, user_id, role}` |
| `api.getCases()` | GET | `/cases/` | — | `[{case_id, case_number, title, status, ...}]` |
| `api.createCase(data)` | POST | `/cases/` | `{title, description, location}` | `{case_id}` |
| `api.getCase(id)` | GET | `/cases/{id}` | — | `{case_id, ..., files: [...]}` |
| `api.uploadFile(id, fd)` | POST | `/cases/{id}/files` | `FormData(file, doc_type)` | `{file_id, s3_key}` |
| `api.triggerPipeline(id)` | POST | `/cases/{id}/pipeline/trigger` | — | `{pipeline_run_id}` |
| `api.getPipelineStatus(id)` | GET | `/cases/{id}/pipeline/status` | — | `{status, agents: [{agent_id, status, duration_ms}]}` |

### Step 5.2 — WebSocket Client

**File: `frontend/lib/ws.js`**

Copy the exact implementation from `PLAN_12`. Key behaviors:

1. **Auto-Reconnect:** On `onclose`, waits 2 seconds then reconnects. This handles backend restarts during development.
2. **Ping Filtering:** Backend sends `{"event":"ping"}` every 20 seconds. The client ignores these.
3. **Event Format:** All real events follow `{"case_id":"...", "event":"EVENT_NAME", "data":{...}}`.

**WebSocket Events You Will Receive:**

| Event Name | When | Data Shape | UI Action |
|-----------|------|-----------|-----------|
| `AGENT_STARTED` | Agent begins executing | `{agent_id, attempt}` | Turn AgentPill cyan + pulse |
| `AGENT_COMPLETED` | Agent finished | `{agent_id, duration_ms, confidence}` | Turn AgentPill green |
| `AGENT_FAILED` | Agent errored | `{agent_id, error}` | Turn AgentPill red |
| `PIPELINE_COMPLETED` | All agents done | `{run_id}` | Refresh case data |
| `PIPELINE_FAILED` | Required agent failed | `{run_id}` | Show error toast |

### Step 5.3 — Zustand State Store

**File: `frontend/lib/store.js`**

```javascript
import { create } from 'zustand';

export const useStore = create((set) => ({
  // Auth
  token: null,
  role: null,
  setAuth: (token, role) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
      localStorage.setItem('role', role);
    }
    set({ token, role });
  },
  clearAuth: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
    }
    set({ token: null, role: null });
  },

  // Pipeline events (from WebSocket)
  agentStatuses: {},  // { [agent_id]: "RUNNING" | "COMPLETE" | "FAILED" }
  updateAgentStatus: (agentId, status) =>
    set((state) => ({
      agentStatuses: { ...state.agentStatuses, [agentId]: status }
    })),
  resetAgentStatuses: () => set({ agentStatuses: {} }),

  // Toast notifications
  toasts: [],
  addToast: (message, type = 'info') =>
    set((state) => ({
      toasts: [...state.toasts, { id: Date.now(), message, type }]
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter(t => t.id !== id)
    })),
}));
```

---

## 6. MOCKING STRATEGY — CRITICAL FOR PARALLEL DEV

Dev A will NOT have most API endpoints ready until Hour 8+. You must keep building without waiting. Here is the exact strategy:

**Rule:** For every `api.getSomething()` call, write a fallback mock:

```javascript
// Pattern for every data-fetching component:
useEffect(() => {
  api.getSomething(id)
    .then(setData)
    .catch(() => {
      // MOCK FALLBACK — remove when Dev A's endpoint is live
      setData(MOCK_DATA);
    });
}, [id]);

const MOCK_DATA = [ /* realistic mock data here */ ];
```

**When to switch from mock to live:**
At each Sync Point (see GUIDE_03), pull Dev A's latest code. Test the API endpoint manually in your browser DevTools:
```javascript
// In browser console:
fetch('http://localhost:8000/api/v1/cases/', {
  headers: { Authorization: 'Bearer ' + localStorage.getItem('token') }
}).then(r => r.json()).then(console.log)
```
If it returns real data, remove the mock fallback from that component.

---

## 7. ACCEPTANCE CRITERIA FOR PHASE 1–3

- [ ] `npm run dev` starts Next.js at `http://localhost:3000` without errors
- [ ] Google Fonts (Inter, Outfit, JetBrains Mono) load in the browser
- [ ] CSS variables render correctly (dark background, cyan accents)
- [ ] `api.js` attaches JWT to outgoing requests (verify in DevTools → Network tab)
- [ ] `ws.js` connects to `ws://localhost:8000/ws` (will fail if backend isn't running yet — that's OK, it auto-reconnects)
- [ ] Zustand store initializes (test: `useStore.getState()` in console)
- [ ] Custom scrollbar appears on `.scroll-area` elements
- [ ] `.card:hover` lifts with shadow transition
- [ ] `.animate-in` elements fade in on page load
