# EXECUTION GUIDE — DEV B (Frontend, UI, & Data Viz)
**Role:** Frontend Lead & Data Visualizer
**Hardware:** Standard Development Machine
**Primary Domain:** `d:\Program Files\forensic\aiventra\frontend\`

---

## 1. Your Mission
You are the architect of the platform's user experience. You will build the Next.js 14 frontend, the real-time websocket connections, and the complex data visualizations (Recharts, D3.js) that make the AI's reasoning understandable to human investigators.

## 2. Your Exact Scope (What You Touch)
**You own EVERYTHING inside:**
- `frontend/` (Next.js app, components, CSS, API/WS clients)

⛔ **STRICT BOUNDARY:** You must **NEVER** modify or create files inside the `services/`, `sql/`, or `models/` directories. If the backend is returning data in the wrong format, **ask Dev A to fix the API endpoint**. Do not write "hacky" parsers in the frontend unless absolutely necessary.

---

## 3. Step-by-Step Implementation Instructions

### Phase 1: The Design System & Shell (Hours 1–3)
1. **Initialize Next.js:** Follow `PLAN_01` to run `create-next-app`. Ensure you install `recharts`, `d3`, and `zustand`. 
2. **CSS Variables:** Copy the exact CSS from `PLAN_12` into `frontend/app/globals.css`. AIVENTRA relies heavily on strict CSS variables (e.g., `var(--accent-cyan)`). Do not hardcode hex colors in your React components.
3. **API & WS Clients:** Implement `lib/api.js` and `lib/ws.js` from `PLAN_12`. 
   *Crucial:* `api.js` automatically attaches the JWT token from `localStorage` to every request. Ensure this is working early.
4. **Layout & Sidebar:** Build the App Router shell in `PLAN_13`. The `layout.js` file should wrap every page with the Sidebar and TopHeader. 

### Phase 2: Core Pages & The Case Lobby (Hours 3–6)
1. **Shared Components:** Implement the reusable UI parts in `PLAN_19` (MetricCard, StatusBadge, AgentPill, ConfidencePill). You will use these everywhere.
2. **Login Page:** Implement `/login` (`PLAN_13`). By this hour, Dev A should have pushed the auth endpoints. Test logging in using the seed account (`admin@aiventra.gov` / `admin123`). If it works, check DevTools -> Application -> Local Storage to ensure the token is saved.
3. **Cases Lobby:** Build the `/cases` route. Ensure the "New Case" modal successfully posts to Dev A's `/api/v1/cases` endpoint.

### Phase 3: The Heavy Lifting — Workspace Tabs (Hours 7–14)
This is the most critical visual part of the application. You are building `/cases/[caseId]/page.js` (`PLAN_14`).

1. **Pipeline Strip:** This component must connect to WebSockets. When Dev A triggers a pipeline, your UI needs to listen to `PIPELINE_STARTED` and `AGENT_COMPLETED` events and animate the agent pills turning from grey to pulsing cyan, to green.
2. **Timeline Chart (Recharts):** Implement the `AreaChart`. Use the SVG `<linearGradient>` definition provided in the plan to show high anomaly scores in red, while keeping normal activity transparent.
3. **Causal Graph (D3.js):** The plan provides a stub. If you have time, use `d3-force` to render the nodes (Hypotheses, Claims, Evidence) and link them. If time is tight, render a stylized list or the stub.

### Phase 4: Fleet Management & Reporting (Hours 15–20)
1. **Command Center:** Implement `PLAN_15`. This is a global view. Use `MetricCard` heavily.
2. **XAI Studio:** Implement `PLAN_16`. The hypothesis distribution uses large, bold text. Pay attention to the color mapping (Homicide = Red, Suicide = Amber, etc. as defined in your CSS variables).
3. **Report Builder:** Create the checkboxes. 

---

## 4. How to Avoid Breaking Dev A
- **Endpoint URLs:** Ensure your `api.js` hits `http://localhost:8000/api/v1/`. Note the `v1` prefix. If you hit `/api/cases` it will 404.
- **WebSocket Protocol:** You are connecting to `ws://localhost:8000/ws`. Listen for `msg.event` and extract payload from `msg.data`.
- **API Payloads:** When you POST to `/cases/[caseId]/files`, you MUST use `FormData` because it is a file upload. Your `api.js` is already configured to omit the `Content-Type` header when sending `FormData` (so the browser can set the `multipart/form-data` boundary automatically). **Do not manually set the content-type for file uploads.**
- **Wait for Backend:** If you are building the TimelineTab but Dev A hasn't finished the Timeline Anomaly agent yet, **use mock data**. Do not stop coding. Mock the state locally, and swap it for `api.getTimeline()` when Dev A is ready.
