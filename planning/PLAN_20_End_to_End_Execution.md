# PLAN 20 — End-to-End Execution & Handoff Guide
**Owner:** Both Devs | **Hour:** 22:00–24:00 | **Priority:** CRITICAL

---

## 1. Objective
Bring all pieces together into a single, cohesive, running demonstration for the hackathon.

---

## 2. Bootstrapping the System

**Terminal 1 (Dev A): Data Layer**
```powershell
cd "d:\Program Files\forensic\aiventra"
docker compose up -d
```

**Terminal 2 (Dev A): API Gateway & Orchestrator**
```powershell
cd "d:\Program Files\forensic\aiventra"
uvicorn services.gateway.main:app --host 0.0.0.0 --port 8000 --reload
```
*(Wait 5 seconds, open another terminal for orchestrator)*
```powershell
python -m services.orchestrator.main
```

**Terminal 3 (Dev A): Agent Fleet**
```powershell
cd "d:\Program Files\forensic\aiventra"
python -m services.worker --all
```

**Terminal 4 (Dev B): Frontend App**
```powershell
cd "d:\Program Files\forensic\aiventra\frontend"
npm run dev
```

---

## 3. The 5-Minute Demo Script

1. **Login:** Navigate to `http://localhost:3000/login`. Login as `admin@aiventra.gov` (pass: `admin123`).
2. **Case Creation:** Go to Cases. Click "+ New Case". Title it "Arun Kumar Incident".
3. **Evidence Upload:** In the workspace, upload the 3 synthetic files generated from `PLAN_18`:
   - `autopsy_report_kumar.txt` -> Doc Type: AUTOPSY_REPORT
   - `cdr_kumar_airtel.csv` -> Doc Type: CDR
   - `financial_kumar_hdfc.csv` -> Doc Type: FINANCIAL_RECORDS
4. **Trigger Pipeline:** Click "Run AI Pipeline".
5. **Real-time Visualization:** 
   - Observe the `PipelineStrip` filling up.
   - Switch to **Command Center** in another tab to watch the active agents spike to 17.
6. **Analysis:**
   - **Timeline Tab:** Point out the anomaly score spike (red gradient) corresponding to the silence gap and the unusual 50K ATM withdrawal.
   - **Hotspots Tab:** Show how the system fused the TOD (Time of Death: 03:00 AM) with the financial/CDR anomaly to create a massive red hotspot.
   - **XAI Studio:** Show the Bayesian Hypothesis scores (HOMICIDE should be >80%).
7. **Audit & Report:** Go to Report Builder, check all boxes, and click "Generate". End the demo by showing the immutable Chain of Custody logs in the Audit tab.

---

## 4. Final Handoff Checklist
- [ ] No uncommitted code on either machine.
- [ ] No `.env` secrets leaked in Git history.
- [ ] All 24 PostgreSQL tables populated successfully.
- [ ] 17 agents can process the synthetic case without throwing any Python stack traces.
- [ ] Next.js app has no React console warnings.

*Good luck with the final sprint!*
