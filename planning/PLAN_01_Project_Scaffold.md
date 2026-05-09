# PLAN 01: Master Project Scaffold & Folder Structure
**Status:** UPDATED & FINALIZED

## 1. THE FOLDER STRUCTURE (Why it is the BEST)

We are using a **Domain-Driven Monorepo**. For a 24-hour sprint with two developers, this is objectively the most efficient and conflict-free architecture possible. 

*   **Why not separate repos?** Managing Docker networks across multiple repos wastes precious hackathon hours. A monorepo allows `docker-compose up` to boot the entire stack instantly.
*   **Why not a shared `src/` folder?** By strictly sandboxing `frontend/` and `backend/`, Dev A and Dev B will never accidentally trigger merge conflicts in each other's configuration files (like `package.json` vs `requirements.txt`).

### The Final, Bulletproof Structure

```text
d:\Program Files\forensic\aiventra\
│
├── .git/
├── .gitignore
├── docker-compose.yml       # Boots Postgres, Redis, MinIO
├── README.md                # 5-minute demo script
│
├── frontend/                # DEV B'S EXCLUSIVE DOMAIN (Next.js 14)
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/                 # Next.js App Router (All 25 Pages)
│   │   ├── login/           # login, /login/mfa, /forgot-password
│   │   ├── cases/
│   │   │   ├── new/         # Multi-step case creation
│   │   │   ├── [caseId]/    # Workspace (Overview, Timeline, TOD, Anomalies, etc.)
│   │   │   │   └── evidence/
│   │   │   │       └── [fileId]/review/ # Post-parse Human Review Gate
│   │   ├── command/         # Fleet Management
│   │   ├── xai/             # Hypothesis Studio
│   │   └── audit/           # Cryptographic Chain of Custody
│   ├── components/
│   │   ├── shared/          # MetricCards, StatusBadges, Buttons
│   │   ├── workspace/       # TimelineTab, HotspotsTab, EvidenceCards
│   │   └── review/          # Extracted Fields Accordions (Cat A-F)
│   ├── lib/
│   │   ├── api.js           # REST wrapper
│   │   ├── ws.js            # TelemetryClient
│   │   └── store.js         # Zustand global state
│   └── public/              # Icons, logos, mock images
│
├── backend/                 # DEV A'S EXCLUSIVE DOMAIN (FastAPI + ML)
│   ├── requirements.txt
│   ├── main.py              # FastAPI Application Entrypoint
│   ├── worker.py            # Asyncio Daemon (Runs 17 Agents)
│   ├── core/
│   │   ├── config.py        # Typed ENV loader
│   │   ├── database.py      # AsyncPG Connection Pool
│   │   ├── redis_client.py  # Pub/Sub & Streams
│   │   └── llm_gateway.py   # Gemini API Singleton
│   ├── api/
│   │   ├── auth.py          # /login, /mfa/verify
│   │   ├── cases.py         # CRUD, /cases/new
│   │   ├── files.py         # /upload, Pre-analysis Quality Gate
│   │   └── pipeline.py      # /trigger, /resume (Human-in-loop)
│   ├── agents/
│   │   ├── base.py          # BaseAgent ABC
│   │   ├── parsers/         # Tier 0/1: Evidence, Autopsy, CDR
│   │   ├── ml/              # Tier 2/3: TOD, Timeline Anomaly
│   │   └── fusion/          # Tier 5+: Hypothesis, Reasoning Replay
│   └── orchestrator/
│       └── dag.py           # DAG builder (Pauses for Human Review)
│
├── models/                  # DEV A: Saved ML weights
│   └── isolation_forest_v1.pkl
│
└── sql/                     # DEV A: Database Initialization
    └── init.sql             # 24-table schema (Includes file status flags)
```

## 2. INITIALIZATION COMMANDS

**Step 1: Create the Monorepo**
```powershell
mkdir "d:\Program Files\forensic\aiventra"
cd "d:\Program Files\forensic\aiventra"
git init
```

**Step 2: Scaffold Frontend (Dev B)**
```powershell
npx -y create-next-app@latest frontend --use-npm --typescript=false --eslint --tailwind --app --src-dir=false --import-alias="@/*"
cd frontend
npm install recharts d3 zustand lucide-react date-fns
cd ..
```

**Step 3: Scaffold Backend (Dev A)**
```powershell
mkdir backend
cd backend
mkdir core api agents models orchestrator
type nul > requirements.txt
type nul > main.py
type nul > worker.py
cd ..
```

**Step 4: Scaffold Infrastructure**
```powershell
mkdir sql
type nul > sql\init.sql
type nul > docker-compose.yml
```
