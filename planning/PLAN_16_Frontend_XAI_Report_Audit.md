# PLAN 16 — Frontend XAI, Report Builder & Audit
**Owner:** Dev B | **Hour:** 14:00–18:00 | **Priority:** HIGH

---

## 1. Objective
Implement the Explainable AI (XAI) Studio for visualizing hypothesis confidence, the Report Builder for exporting forensic reports, and the Audit & Chain of Custody page.

---

## 2. XAI & Uncertainty Studio

**File: `frontend/app/xai/page.js`**

```jsx
'use client';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export default function XAIStudio() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [hypotheses, setHypotheses] = useState([]);

  useEffect(() => {
    api.getCases().then(setCases).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedCase) {
      // Mock data for MVP:
      setHypotheses([
        { key: 'HOMICIDE', prob: 0.82, trend: 'UP' },
        { key: 'ACCIDENT', prob: 0.10, trend: 'DOWN' },
        { key: 'SUICIDE', prob: 0.05, trend: 'STABLE' },
        { key: 'NATURAL', prob: 0.02, trend: 'STABLE' },
        { key: 'UNDETERMINED', prob: 0.01, trend: 'DOWN' },
      ]);
    }
  }, [selectedCase]);

  return (
    <div className="animate-in">
      <h1 style={{fontFamily:'var(--font-display)', marginBottom:24}}>XAI & Uncertainty Studio</h1>
      
      <select value={selectedCase} onChange={e=>setSelectedCase(e.target.value)} style={{marginBottom:24, width:300}}>
        <option value="">Select a case...</option>
        {cases.map(c => <option key={c.case_id} value={c.case_id}>{c.case_number} — {c.title}</option>)}
      </select>

      {selectedCase && (
        <div className="grid-3">
          {hypotheses.map(h => (
            <div key={h.key} className="card" style={{textAlign:'center', padding:32}}>
              <p style={{color:'var(--text-faint)', fontSize:'0.85rem', marginBottom:8}}>{h.key}</p>
              <p style={{fontSize:'3rem', fontWeight:700, color: `var(--hypothesis-${h.key.toLowerCase()})`}}>
                {(h.prob * 100).toFixed(0)}%
              </p>
              <p style={{fontSize:'0.8rem', color:'var(--text-muted)', marginTop:8}}>
                Trend: {h.trend}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## 3. Report Builder

**File: `frontend/app/reports/page.js`**

```jsx
'use client';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

const SECTIONS = [
  'Executive Summary', 'Ingestion Details', 'Autopsy Findings', 
  'Time of Death', 'Timeline Anomalies', 'Hypothesis Scores'
];

export default function ReportBuilder() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [enabled, setEnabled] = useState(new Set(SECTIONS));

  useEffect(() => { api.getCases().then(setCases).catch(console.error); }, []);

  const toggle = (s) => {
    const n = new Set(enabled);
    n.has(s) ? n.delete(s) : n.add(s);
    setEnabled(n);
  };

  return (
    <div className="animate-in">
      <h1 style={{fontFamily:'var(--font-display)', marginBottom:24}}>Report Builder</h1>
      <div className="grid-2">
        <div>
          <select value={selectedCase} onChange={e=>setSelectedCase(e.target.value)} style={{marginBottom:24, width:'100%'}}>
            <option value="">Select a case to export...</option>
            {cases.map(c => <option key={c.case_id} value={c.case_id}>{c.case_number}</option>)}
          </select>

          <div className="card">
            <h3 style={{marginBottom:16}}>Included Sections</h3>
            {SECTIONS.map(s => (
              <label key={s} style={{display:'flex', alignItems:'center', gap:8, marginBottom:8, cursor:'pointer'}}>
                <input type="checkbox" checked={enabled.has(s)} onChange={() => toggle(s)} />
                <span>{s}</span>
              </label>
            ))}
            <button className="btn btn-primary" style={{marginTop:24, width:'100%'}}>Generate PDF Report</button>
          </div>
        </div>
        
        <div className="card" style={{padding:32}}>
          <h3 style={{color:'var(--text-muted)', textAlign:'center', marginTop:100}}>PDF Preview Canvas</h3>
        </div>
      </div>
    </div>
  );
}
```

---

## 4. Audit Trail

**File: `frontend/app/audit/page.js`**

```jsx
'use client';

const MOCK_LOGS = [
  { ts: '10:05:22', action: 'FILE_UPLOAD', user: 'investigator@police.gov', detail: 'autopsy.pdf (sha256: 8f4e...)' },
  { ts: '10:05:45', action: 'PIPELINE_TRIGGER', user: 'investigator@police.gov', detail: 'Started 14 agents' },
  { ts: '10:06:12', action: 'AGENT_COMPLETE', user: 'SYSTEM', detail: 'autopsy_agent finished' },
];

export default function AuditPage() {
  return (
    <div className="animate-in">
      <h1 style={{fontFamily:'var(--font-display)', marginBottom:24}}>Audit & Custody Log</h1>
      
      <div className="card" style={{padding:0}}>
        <table style={{width:'100%', borderCollapse:'collapse', textAlign:'left'}}>
          <thead>
            <tr style={{borderBottom:'1px solid var(--border-subtle)', color:'var(--text-faint)'}}>
              <th style={{padding:16}}>Timestamp</th>
              <th style={{padding:16}}>Action</th>
              <th style={{padding:16}}>User</th>
              <th style={{padding:16}}>Details</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_LOGS.map((l, i) => (
              <tr key={i} style={{borderBottom:'1px solid var(--border-subtle)'}}>
                <td style={{padding:16, color:'var(--text-muted)'}}>{l.ts}</td>
                <td style={{padding:16}}><span className="badge" style={{background:'var(--bg-dark)'}}>{l.action}</span></td>
                <td style={{padding:16}}>{l.user}</td>
                <td style={{padding:16}}>{l.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

## Acceptance Criteria
- [ ] XAI Studio displays percentage gauges with correct color coding.
- [ ] Report builder has togglable checkboxes for sections.
- [ ] Audit trail renders tabular event history.
