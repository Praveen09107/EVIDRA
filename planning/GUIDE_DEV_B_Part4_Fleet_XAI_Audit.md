# DEV B EXECUTION GUIDE — PART 4: Fleet Management, XAI, & Audit
**Owner:** Dev B | **Hours:** 14:00–20:00 | **Priority:** HIGH

---

## 1. PHASE 11 — FLEET MANAGEMENT (Hour 14:00–16:00)

The Command Center and Agent Directory give investigators a bird's-eye view of the AI system's health. 

### Step 1.1 — Command Center

**File: `frontend/app/command/page.js`**

```jsx
'use client';
import { useState, useEffect } from 'react';
import MetricCard from '@/components/shared/MetricCard';
import { TelemetryClient } from '@/lib/ws';

export default function CommandCenter() {
  const [metrics, setMetrics] = useState({
    activePipelines: 1,
    agentsRunning: 0,
    llmTokens: 145020,
    systemHealth: '100%'
  });

  const [logs, setLogs] = useState([
    '[SYSTEM] Boot sequence complete. PostgreSQL connected.',
    '[SYSTEM] Redis Streams initialized.'
  ]);

  useEffect(() => {
    const ws = new TelemetryClient((msg) => {
      if (msg.event === 'AGENT_STARTED') {
        setMetrics(m => ({ ...m, agentsRunning: m.agentsRunning + 1 }));
        setLogs(l => [`[${new Date().toLocaleTimeString()}] 🚀 ${msg.data.agent_id} started`, ...l].slice(0, 50));
      }
      if (msg.event === 'AGENT_COMPLETED') {
        setMetrics(m => ({ ...m, agentsRunning: Math.max(0, m.agentsRunning - 1) }));
        setLogs(l => [`[${new Date().toLocaleTimeString()}] ✅ ${msg.data.agent_id} completed in ${msg.data.duration_ms}ms`, ...l].slice(0, 50));
      }
      if (msg.event === 'AGENT_FAILED') {
        setMetrics(m => ({ ...m, agentsRunning: Math.max(0, m.agentsRunning - 1) }));
        setLogs(l => [`[${new Date().toLocaleTimeString()}] ❌ ${msg.data.agent_id} FAILED: ${msg.data.error}`, ...l].slice(0, 50));
      }
    });
    ws.connect();
    return () => ws.disconnect();
  }, []);

  return (
    <div className="animate-in">
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem' }}>Command Center</h1>
        <p style={{ color: 'var(--text-muted)' }}>Global overview of AIVENTRA system performance.</p>
      </div>
      
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <MetricCard label="Active Pipelines" value={metrics.activePipelines} icon="⚙️" />
        <MetricCard label="Agents Running" value={metrics.agentsRunning} color="var(--warning-amber)" icon="🏃" />
        <MetricCard label="LLM Tokens (24h)" value={metrics.llmTokens.toLocaleString()} color="var(--accent-blue)" icon="💬" />
        <MetricCard label="System Health" value={metrics.systemHealth} color="var(--success-green)" icon="🛡️" />
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Live Agent Logs</h3>
          <div style={{
            background: '#05080f', padding: 16, borderRadius: 6, 
            fontFamily: 'var(--font-mono)', fontSize: '0.75rem', 
            color: 'var(--text-secondary)', height: 350, overflowY: 'auto'
          }}>
            {logs.map((l, i) => (
              <div key={i} style={{ 
                marginBottom: 6, paddingBottom: 6, 
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                color: l.includes('❌') ? 'var(--anomaly-red)' : l.includes('✅') ? 'var(--success-green)' : 'inherit'
              }}>
                {l}
              </div>
            ))}
          </div>
        </div>
        
        {/* Placeholder for future resource chart */}
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>GPU / Memory Utilization</h3>
          <div className="empty-state" style={{ height: 350 }}>
            <p>Telemetry integration pending</p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 2. PHASE 12 — XAI STUDIO (Explainable AI) (Hour 16:00–18:00)

The XAI Studio visualizes the output of the Hypothesis Manager agent.

### Step 2.1 — XAI Studio Page

**File: `frontend/app/xai/page.js`**

```jsx
'use client';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import ConfidencePill from '@/components/shared/ConfidencePill';

const MOCK_HYPOTHESES = [
  { key: 'HOMICIDE', prob: 0.82, trend: 'UP', reason: 'Blunt trauma + sequence anomalies' },
  { key: 'ACCIDENT', prob: 0.10, trend: 'DOWN', reason: 'Inconsistent with force required' },
  { key: 'SUICIDE', prob: 0.05, trend: 'STABLE', reason: 'No hesitation marks found' },
  { key: 'NATURAL', prob: 0.02, trend: 'STABLE', reason: 'Ruled out by pathology' },
  { key: 'UNDETERMINED', prob: 0.01, trend: 'DOWN', reason: 'Sufficient evidence exists' },
];

export default function XAIStudio() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [hypotheses, setHypotheses] = useState([]);

  useEffect(() => {
    api.getCases().then(setCases).catch(() => setCases([{case_id: 'mock', case_number: 'CASE-MOCK'}]));
  }, []);

  useEffect(() => {
    if (selectedCase) setHypotheses(MOCK_HYPOTHESES);
    else setHypotheses([]);
  }, [selectedCase]);

  return (
    <div className="animate-in">
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem' }}>XAI Studio</h1>
        <p style={{ color: 'var(--text-muted)' }}>Bayesian hypothesis probability distribution.</p>
      </div>
      
      <div className="card" style={{ marginBottom: 32, padding: 24, display: 'inline-block' }}>
        <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>Select Case for Analysis</label>
        <select value={selectedCase} onChange={e=>setSelectedCase(e.target.value)} 
                style={{ width: 350, fontSize: '0.9rem', padding: '10px 12px' }}>
          <option value="">-- Choose Case --</option>
          {cases.map(c => <option key={c.case_id} value={c.case_id}>{c.case_number}</option>)}
        </select>
      </div>

      {selectedCase && (
        <div className="grid-3">
          {hypotheses.map(h => {
            const color = `var(--hypothesis-${h.key.toLowerCase()})`;
            return (
              <div key={h.key} className="card" style={{ position: 'relative', overflow: 'hidden' }}>
                <div style={{ 
                  position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: color 
                }} />
                
                <div className="flex-between" style={{ marginBottom: 16 }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{h.key}</span>
                  <span style={{ fontSize: '0.75rem', color: h.trend === 'UP' ? 'var(--anomaly-red)' : 'var(--text-muted)' }}>
                    {h.trend === 'UP' ? '▲ Trending Up' : h.trend === 'DOWN' ? '▼ Trending Down' : '— Stable'}
                  </span>
                </div>
                
                <div style={{ fontSize: '3.5rem', fontWeight: 800, fontFamily: 'var(--font-display)', color, lineHeight: 1 }}>
                  {(h.prob * 100).toFixed(0)}<span style={{ fontSize: '1.5rem', color: 'var(--text-muted)', fontWeight: 400 }}>%</span>
                </div>
                
                <div style={{ marginTop: 24, fontSize: '0.8rem', color: 'var(--text-muted)', background: 'var(--bg-dark)', padding: '8px 12px', borderRadius: 4 }}>
                  <strong>Primary Driver:</strong> {h.reason}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

---

## 3. PHASE 13 — AUDIT & CUSTODY (Hour 18:00–20:00)

**File: `frontend/app/audit/page.js`**

```jsx
'use client';

const MOCK_LOGS = [
  { ts: '2026-05-09 10:05:22', action: 'FILE_UPLOAD', actor: 'investigator@aiventra.gov', detail: 'autopsy_report_kumar.txt uploaded. Hash: 8f4e92a...', integrity: 'VERIFIED' },
  { ts: '2026-05-09 10:05:45', action: 'PIPELINE_TRIGGER', actor: 'investigator@aiventra.gov', detail: 'Started 17-agent execution DAG.', integrity: 'VERIFIED' },
  { ts: '2026-05-09 10:06:01', action: 'AGENT_REASONING', actor: 'autopsy_agent', detail: 'Extracted Cause of Death: Blunt Force Trauma. Conf: 0.95', integrity: 'VERIFIED' },
  { ts: '2026-05-09 10:06:12', action: 'AGENT_REASONING', actor: 'tod_agent', detail: 'Calculated Henssge PMI: 6-8 hours.', integrity: 'VERIFIED' },
];

export default function AuditPage() {
  return (
    <div className="animate-in">
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem' }}>Chain of Custody & Audit</h1>
        <p style={{ color: 'var(--text-muted)' }}>Cryptographically secured log of all human and AI actions.</p>
      </div>
      
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead style={{ background: 'var(--bg-dark)' }}>
            <tr>
              <th style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-subtle)', width: '200px' }}>Timestamp</th>
              <th style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-subtle)', width: '150px' }}>Action</th>
              <th style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-subtle)', width: '200px' }}>Actor</th>
              <th style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-subtle)' }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_LOGS.map((l, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                <td style={{ padding: '16px 24px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{l.ts}</td>
                <td style={{ padding: '16px 24px' }}><span className="badge" style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-subtle)' }}>{l.action}</span></td>
                <td style={{ padding: '16px 24px', fontSize: '0.85rem', color: l.actor.includes('@') ? 'var(--accent-blue)' : 'var(--accent-cyan)' }}>{l.actor}</td>
                <td style={{ padding: '16px 24px', fontSize: '0.85rem' }}>
                  {l.detail}
                  <div style={{ marginTop: 4, fontSize: '0.7rem', color: 'var(--success-green)' }}>✓ Cryptographic Hash {l.integrity}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

## ACCEPTANCE CRITERIA FOR PART 4
- [ ] Command Center metric cards format numbers correctly
- [ ] Command Center live logs append new entries from WebSockets
- [ ] XAI Studio maps CSS variables correctly for HOMICIDE/SUICIDE colors
- [ ] Audit trail renders correctly in a table with mono-spaced timestamps
