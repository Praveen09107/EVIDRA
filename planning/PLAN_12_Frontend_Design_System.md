# PLAN 12 — Frontend Design System & Globals
**Owner:** Dev B | **Hour:** 0:30–2:00 | **Priority:** CRITICAL

---

## 1. Objective
Establish the visual language of AIVENTRA. Define CSS variables for the dark, high-contrast UI, global layout constraints, the `api.js` client for communicating with the backend, and the `ws.js` WebSocket client for real-time telemetry.

---

## 2. Design System

**File: `frontend/app/globals.css`**

```css
:root {
  --bg-dark: #0A0F1A;
  --bg-elevated: #111827;
  --bg-elevated-hover: #1F2937;
  
  --text-primary: #F9FAFB;
  --text-secondary: #D1D5DB;
  --text-muted: #9CA3AF;
  --text-faint: #6B7280;

  --accent-cyan: #22C7D5;
  --accent-blue: #38BDF8;
  --success-green: #22C55E;
  --warning-amber: #FBBF24;
  --anomaly-red: #F97373;
  
  --hypothesis-homicide: #F87171;
  --hypothesis-suicide: #FBBF24;
  --hypothesis-accident: #34D399;
  --hypothesis-natural: #60A5FA;
  --hypothesis-undetermined: #9CA3AF;

  --border-subtle: #1F2937;
  --border-focus: #38BDF8;

  --font-sans: 'Inter', system-ui, sans-serif;
  --font-display: 'Outfit', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg-dark); color: var(--text-primary); font-family: var(--font-sans); }
a { color: var(--accent-cyan); text-decoration: none; }

/* Layout */
.app-layout { display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 240px; background: var(--bg-elevated); border-right: 1px solid var(--border-subtle); display: flex; flex-direction: column; }
.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar { height: 60px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; padding: 0 24px; }
.scroll-area { flex: 1; overflow-y: auto; padding: 24px; }

/* Cards */
.card { background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 16px; transition: transform 0.2s; }
.card-glass { background: rgba(17, 24, 39, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; }

/* Forms */
input, select { background: var(--bg-dark); border: 1px solid var(--border-subtle); color: var(--text-primary); padding: 8px 12px; border-radius: 6px; font-family: var(--font-sans); outline: none; }
input:focus, select:focus { border-color: var(--border-focus); }

/* Buttons */
.btn { padding: 8px 16px; border-radius: 6px; font-weight: 500; cursor: pointer; border: none; transition: 0.2s; }
.btn-primary { background: var(--accent-cyan); color: #000; }
.btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
.btn-secondary { background: var(--bg-elevated-hover); color: var(--text-primary); border: 1px solid var(--border-subtle); }
.btn-secondary:hover { border-color: var(--text-muted); }

/* Utilities */
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

/* Animations */
@keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.animate-in { animation: slideIn 0.3s ease forwards; }
@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.7; transform: scale(1.05); } 100% { opacity: 1; transform: scale(1); } }
```

---

## 3. API Client

**File: `frontend/lib/api.js`**

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';

async function request(endpoint, options = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const headers = { ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  
  if (!(options.body instanceof FormData) && options.body && typeof options.body === 'object') {
    options.body = JSON.stringify(options.body);
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (email, password) => request('/auth/login', { method: 'POST', body: { email, password } }),
  getCases: () => request('/cases/'),
  createCase: (data) => request('/cases/', { method: 'POST', body: data }),
  getCase: (id) => request(`/cases/${id}`),
  uploadFile: (id, formData) => request(`/cases/${id}/files`, { method: 'POST', body: formData }),
  triggerPipeline: (id) => request(`/cases/${id}/pipeline/trigger`, { method: 'POST' }),
  getPipelineStatus: (id) => request(`/cases/${id}/pipeline/status`),
  // Stub for analysis routes
  getTimeline: (id) => request(`/cases/${id}/analysis/timeline`).catch(() => []),
};
```

---

## 4. WebSocket Client

**File: `frontend/lib/ws.js`**

```javascript
export class TelemetryClient {
  constructor(onMessage) {
    this.ws = null;
    this.onMessage = onMessage;
  }
  
  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws');
    this.ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.event !== 'ping') this.onMessage(msg);
      } catch (err) {}
    };
    this.ws.onclose = () => setTimeout(() => this.connect(), 2000);
  }
  
  disconnect() {
    if (this.ws) this.ws.close();
  }
}
```

## Acceptance Criteria
- [ ] CSS loads with standard variables.
- [ ] `api.js` automatically attaches JWT token.
- [ ] `ws.js` attempts auto-reconnect on drop.
