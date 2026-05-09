# EXECUTION GUIDE — INTEGRATION & SYNC PROTOCOL
**Role:** Both Developers | **Priority:** CRITICAL

---

## 1. THE CORE PROBLEM

You are two developers working simultaneously inside the exact same Git repository (`d:\Program Files\forensic\aiventra`) over a grueling 24-hour hackathon. Without extreme discipline, you will encounter catastrophic merge conflicts that can burn hours of development time.

This document outlines the strict protocols you must follow to guarantee 0% merge conflicts.

---

## 2. THE GOLDEN RULE OF BOUNDARIES

**Dev A NEVER touches the `frontend/` directory.**
**Dev B NEVER touches the `services/`, `sql/`, or `models/` directories.**

There is exactly ONE file where your domains cross: `.env`.
If either developer needs to add an environment variable (e.g., a new port or an API key), you must inform the other verbally before committing.

---

## 3. GIT BRANCHING STRATEGY

You will **not** work on the `main` branch directly.

### Hour 0: Initial Setup
Both developers must run this after cloning the repository:
```powershell
git fetch origin
git checkout main
```

### Dev A (Backend) Setup:
```powershell
git checkout -b dev/backend
```

### Dev B (Frontend) Setup:
```powershell
git checkout -b dev/frontend
```

You will write all your code in these respective branches.

---

## 4. THE 10 SYNCHRONIZATION POINTS (The "Sync Dance")

In your master sprint schedule, there are predefined "Sync Points" (e.g., at Hour 3, Hour 6, Hour 10). When you reach a sync point, you must stop coding, communicate with your partner verbally, and perform the "Sync Dance".

### Step 1: Commit your own work
**DEV A (on `dev/backend`):**
```powershell
git add .
git commit -m "SYNC-1: Database and LLM Gateway complete"
git push origin dev/backend
```

**DEV B (on `dev/frontend`):**
```powershell
git add .
git commit -m "SYNC-1: CSS Globals and Layout complete"
git push origin dev/frontend
```

### Step 2: The Merge (Dev A handles this)
*Because Dev A and Dev B touched completely different folders, git will auto-merge this flawlessly without human intervention.*
**DEV A ONLY:**
```powershell
git checkout main
git pull origin main
git merge dev/backend
git merge dev/frontend
git push origin main
```

### Step 3: Dev B syncs back up
**DEV B ONLY:**
```powershell
git checkout dev/frontend
git pull origin main
```

### Step 4: Dev A returns to work
**DEV A ONLY:**
```powershell
git checkout dev/backend
git pull origin main
```

*Result:* Both developers now have each other's latest code. Dev B can immediately start testing the UI against Dev A's latest API endpoints.

---

## 5. API CONTRACT & MOCKING (Crucial for Dev B's Speed)

Dev B (Frontend) will often be faster at building UI than Dev A is at building complex ML agents. 

**Rule:** Dev B must NEVER wait for Dev A to finish an API endpoint. 
If Dev B needs to build the `TimelineTab` but Dev A hasn't finished the `TimelineAnomalyAgent`, Dev B must use **Hardcoded Mock Data** in the React component.

**Example of what Dev B should do:**
```javascript
// Inside TimelineTab.js
const [data, setData] = useState([]);

useEffect(() => {
  // TODO: Swap this out when Dev A finishes the /analysis/timeline endpoint
  // api.getTimeline(caseId).then(setData).catch(err => console.error(err)); 
  
  // MOCK DATA for now:
  setData([
    { time: '18:00', anomaly: 0.1, events: 10 },
    { time: '23:00', anomaly: 0.9, events: 50 }, // Fake anomaly
  ]);
}, [caseId]);
```

**When Dev A finishes the endpoint:** During the next Sync Point, Dev B pulls `main`, verifies the endpoint is alive using browser DevTools or Swagger (`localhost:8000/docs`), uncomments the API call, and deletes the mock data.

---

## 6. HANDLING WEBSOCKET RACE CONDITIONS

Because WebSockets are asynchronous, Dev B might render the `PipelineStrip` UI slightly before Dev A's backend fires the `AGENT_STARTED` event.

**How to handle this:**
Dev B must write UI code that gracefully handles missing or delayed state. If an agent's status is unknown, default to `PENDING` (Grey color). Do not throw `null reference` errors if `status.agents` is undefined in the first few milliseconds.

---

## 7. EMERGENCY DATABASE RESET

If Dev A discovers a flaw in the database schema and alters the `init.sql` file mid-sprint, Dev B's local database will break because Docker Postgres doesn't automatically drop existing tables on restart.

If this happens, Dev A must announce the schema change, and Dev B must run:

**DEV B ONLY:**
```powershell
docker compose down -v  # The -v DESTROYS the volume, dropping the old database
docker compose up -d    # Re-creates the DB using the new init.sql
```

This takes 5 seconds and resolves 99% of "Database schema mismatch" or "Relation does not exist" errors.
