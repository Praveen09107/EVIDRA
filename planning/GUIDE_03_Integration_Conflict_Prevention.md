# EXECUTION GUIDE — INTEGRATION & CONFLICT PREVENTION
**Role:** Both Developers | **Priority:** CRITICAL

---

## 1. The Monorepo Problem
You are two developers working simultaneously inside the exact same Git repository (`d:\Program Files\forensic\aiventra`) over a grueling 24-hour hackathon. Without extreme discipline, you will encounter catastrophic merge conflicts that can burn hours of development time.

This document outlines the strict protocols you must follow to guarantee 0% merge conflicts.

---

## 2. The Golden Rule of Boundaries
**Dev A NEVER touches the `frontend/` directory.**
**Dev B NEVER touches the `services/`, `sql/`, or `models/` directories.**

There is exactly ONE file where your domains cross: `.env`. 
If either developer needs to add an environment variable (e.g., a new port or an API key), you must inform the other verbally before committing.

---

## 3. Git Branching Strategy

You will not work on the `main` branch directly. 

**Setup (Hour 0):**
```powershell
# Both developers run this after cloning the repo:
git fetch origin
git checkout main
```

**Dev A (Backend):**
```powershell
git checkout -b dev/backend
```

**Dev B (Frontend):**
```powershell
git checkout -b dev/frontend
```

You will write all your code in these respective branches.

---

## 4. The 10 Synchronization Points (The "Sync Dance")
In `PLAN_00_Master_Sprint.md`, there are 10 predefined "Sync Points". When you reach a sync point, you must stop coding, communicate with your partner, and perform the "Sync Dance".

**Step 1: Commit your own work**
```powershell
# DEV A (on dev/backend)
git add .
git commit -m "SYNC-1: Database and LLM Gateway complete"
git push origin dev/backend

# DEV B (on dev/frontend)
git add .
git commit -m "SYNC-1: CSS Globals and Layout complete"
git push origin dev/frontend
```

**Step 2: The Merge (Dev A handles this)**
*Because Dev A and Dev B touched completely different folders, git will auto-merge this flawlessly without human intervention.*
```powershell
# DEV A ONLY:
git checkout main
git pull origin main
git merge dev/backend
git merge dev/frontend
git push origin main
```

**Step 3: Dev B syncs back up**
```powershell
# DEV B ONLY:
git checkout dev/frontend
git pull origin main
```

**Step 4: Dev A returns to work**
```powershell
# DEV A ONLY:
git checkout dev/backend
git pull origin main
```

*Result:* Both developers now have each other's latest code. Dev B can immediately start testing the UI against Dev A's latest API endpoints.

---

## 5. API Contract & Mocking (Crucial for Speed)
Dev B (Frontend) will often be faster at building UI than Dev A is at building complex ML agents. 

**Rule:** Dev B must NEVER wait for Dev A to finish an API endpoint. 
If Dev B needs to build the `TimelineTab` but Dev A hasn't finished the `TimelineAnomalyAgent`, Dev B must use **Hardcoded Mock Data** in the React component.

Example of what Dev B should do:
```javascript
// Inside TimelineTab.js
const [data, setData] = useState([]);

useEffect(() => {
  // TODO: Swap this out when Dev A finishes the /analysis/timeline endpoint
  // api.getTimeline(caseId).then(setData); 
  
  // MOCK DATA for now:
  setData([
    { time: '18:00', anomaly: 0.1 },
    { time: '23:00', anomaly: 0.9 }, // Fake anomaly
  ]);
}, [caseId]);
```
When Dev A finishes the endpoint during a Sync Point, Dev B simply uncomments the API call and deletes the mock data.

---

## 6. Resolving WebSocket Race Conditions
Because WebSockets are asynchronous, Dev B might render the `PipelineStrip` UI slightly before Dev A's backend fires the `AGENT_STARTED` event.

**How to handle this:**
Dev B must write UI code that gracefully handles missing or delayed state. If an agent's status is unknown, default to `PENDING` (Grey color). Do not throw `null reference` errors if `status.agents` is undefined in the first few milliseconds.

## 7. Emergency DB Reset
If Dev A alters the `init.sql` schema mid-sprint, Dev B's local database will break because Docker Postgres doesn't automatically drop tables on restart.

If this happens, Dev B must run:
```powershell
# DEV B ONLY:
docker compose down -v  # The -v destroys the volume, dropping the old database
docker compose up -d    # Re-creates the DB using the new init.sql
```
This takes 5 seconds and resolves 99% of "Database schema mismatch" errors.
