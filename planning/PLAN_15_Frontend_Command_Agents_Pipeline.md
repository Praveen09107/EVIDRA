# PLAN 15 — Frontend Fleet Management
**Owner:** Dev B | **Hour:** 10:00–14:00 | **Priority:** HIGH

---

## 1. Objective
Build the Command Center (global metrics), Agent Directory (list of all 17 agents), Agent Lab (testing an individual agent), and Pipeline Explorer (visualizing pipeline runs).

---

## 2. Command Center

**File: `frontend/app/command/page.js`**

```jsx
'use client';
import { useState, useEffect } from 'react';
import MetricCard from '@/components/shared/MetricCard';
import { TelemetryClient } from '@/lib/ws';

export default function CommandCenter() {
  const [metrics, setMetrics] = useState({
    activePipelines: 0,
    agentsRunning: 0,
    llmTokens: 0,
    systemHealth: '100%'
  });

  useEffect(() => {
    // In production, fetch from /api/v1/system/metrics
    // Using a mock WS update for MVP
    const ws = new TelemetryClient((msg) => {
      if (msg.event === 'AGENT_STARTED') {
        setMetrics(m => ({ ...m, agentsRunning: m.agentsRunning + 1 }));
      }
      if (msg.event === 'AGENT_COMPLETED') {
        setMetrics(m => ({ ...m, agentsRunning: Math.max(0, m.agentsRunning - 1) }));
      }
    });
    ws.connect();
    return () => ws.disconnect();
  }, []);

  return (
    <div className="animate-in">
      <h1 style={{fontFamily:'var(--font-display)', marginBottom:24}}>Command Center</h1>
      
      <div className="grid-4" style={{marginBottom:32}}>
        <MetricCard label="Active Pipelines" value={metrics.activePipelines} />
        <MetricCard label="Agents Running" value={metrics.agentsRunning} color="var(--warning-amber)" />
        <MetricCard label="LLM Tokens (24h)" value={metrics.llmTokens.toLocaleString()} color="var(--accent-blue)" />
        <MetricCard label="System Health" value={metrics.systemHealth} color="var(--success-green)" />
      </div>

      <div className="card">
        <h3 style={{marginBottom:16}}>System Logs</h3>
        <div style={{background:'var(--bg-dark)', padding:16, borderRadius:6, fontFamily:'var(--font-mono)', fontSize:'0.8rem', color:'var(--text-secondary)', height:300, overflowY:'auto'}}>
          [10:00:01] System started...<br/>
          [10:00:05] Connected to PostgreSQL.<br/>
          [10:00:06] Connected to Redis.<br/>
        </div>
      </div>
    </div>
  );
}
```

---

## 3. Agent Directory

**File: `frontend/app/agents/page.js`**

```jsx
'use client';
import { useRouter } from 'next/navigation';

const AGENTS = [
  { id: 'evidence_parser', tier: 0, category: 'INGEST' },
  { id: 'ocr', tier: 0, category: 'INGEST' },
  { id: 'format_normalizer', tier: 1, category: 'INGEST' },
  { id: 'autopsy_agent', tier: 2, category: 'NLP' },
  { id: 'tod_agent', tier: 3, category: 'HYBRID' },
  { id: 'hypothesis_manager', tier: 5, category: 'REASONING' },
  { id: 'reasoning_replay', tier: 7, category: 'AUDIT' },
  // ... and others
];

export default function AgentDirectory() {
  const router = useRouter();

  return (
    <div className="animate-in">
      <h1 style={{fontFamily:'var(--font-display)', marginBottom:24}}>Agent Directory</h1>
      
      <div className="grid-3">
        {AGENTS.map(agent => (
          <div key={agent.id} className="card" style={{cursor:'pointer'}} onClick={() => router.push(`/agents/${agent.id}`)}>
            <div className="flex-between" style={{marginBottom:12}}>
              <span className="badge" style={{background:'var(--bg-dark)'}}>Tier {agent.tier}</span>
              <span style={{fontSize:'0.8rem', color:'var(--text-muted)'}}>{agent.category}</span>
            </div>
            <h3 style={{color:'var(--accent-cyan)'}}>{agent.id}</h3>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 4. Pipeline Explorer

**File: `frontend/app/pipeline/[caseId]/page.js`**

```jsx
'use client';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import AgentPill from '@/components/agents/AgentPill';

export default function PipelineExplorer() {
  const { caseId } = useParams();
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api.getPipelineStatus(caseId).then(setStatus);
    const interval = setInterval(() => api.getPipelineStatus(caseId).then(setStatus), 3000);
    return () => clearInterval(interval);
  }, [caseId]);

  if (!status) return <div>Loading...</div>;

  // Group by tier (mock tiers for UI)
  const tiers = [0,1,2,3,4,5,6,7];

  return (
    <div className="animate-in">
      <h1 style={{fontFamily:'var(--font-display)', marginBottom:24}}>Pipeline Explorer: {caseId.split('-')[0]}</h1>
      <div className="card">
        {tiers.map(t => (
          <div key={t} style={{display:'flex', gap:16, marginBottom:24, alignItems:'center'}}>
            <div style={{width:80, color:'var(--text-muted)', fontSize:'0.9rem', fontWeight:600}}>Tier {t}</div>
            <div style={{display:'flex', gap:12, flexWrap:'wrap', flex:1}}>
              {status.agents?.filter(a => a.tier === t).map(agent => (
                <AgentPill key={agent.agent_id} agentId={agent.agent_id} status={agent.status} />
              )) || <span style={{color:'var(--text-faint)'}}>No agents</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Acceptance Criteria
- [ ] Command Center displays 4 metric cards.
- [ ] Agent Directory lists the agents and routes to `[agentId]`.
- [ ] Pipeline Explorer fetches `/pipeline/status` every 3s and renders tier-grouped AgentPills.
