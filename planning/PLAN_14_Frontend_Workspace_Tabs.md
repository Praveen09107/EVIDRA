# PLAN 14 — Frontend Workspace Tabs (Case Analysis)
**Owner:** Dev B | **Hour:** 4:00–10:00 | **Priority:** CRITICAL

---

## 1. Objective
Implement the main workspace for a specific case (`/cases/[caseId]`). This includes the file upload header, the animated pipeline status strip, and the heavy data visualization tabs (Timeline, Hotspots, Causal Graph, and Reasoning Replay).

---

## 2. Case Workspace Shell

**File: `frontend/app/cases/[caseId]/page.js`**

```jsx
'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { TelemetryClient } from '@/lib/ws';
import CaseHeader from '@/components/workspace/CaseHeader';
import PipelineStrip from '@/components/workspace/PipelineStrip';
import TimelineTab from '@/components/workspace/TimelineTab';
import HotspotsTab from '@/components/workspace/HotspotsTab';
import CausalGraphTab from '@/components/workspace/CausalGraphTab';
import ReplayTab from '@/components/workspace/ReplayTab';

export default function CaseWorkspace() {
  const params = useParams();
  const caseId = params.caseId;
  const [caseData, setCaseData] = useState(null);
  const [activeTab, setActiveTab] = useState('TIMELINE');

  useEffect(() => {
    api.getCase(caseId).then(setCaseData).catch(console.error);
    
    // Live WS updates
    const ws = new TelemetryClient((msg) => {
      if (msg.event === 'PIPELINE_COMPLETED') {
        api.getCase(caseId).then(setCaseData);
      }
    });
    ws.connect();
    return () => ws.disconnect();
  }, [caseId]);

  if (!caseData) return <div className="animate-in" style={{padding:40}}>Loading workspace...</div>;

  const TABS = ['TIMELINE', 'HOTSPOTS', 'CAUSAL_GRAPH', 'REASONING_REPLAY'];

  return (
    <div className="animate-in" style={{display:'flex', flexDirection:'column', height:'100%'}}>
      <CaseHeader caseData={caseData} onUpload={() => api.getCase(caseId).then(setCaseData)} />
      <PipelineStrip caseId={caseId} />
      
      <div style={{display:'flex', gap:24, marginTop:24, borderBottom:'1px solid var(--border-subtle)', paddingBottom:12}}>
        {TABS.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
                  style={{background:'none', border:'none', color: activeTab===t ? 'var(--accent-cyan)' : 'var(--text-muted)',
                          fontSize:'0.9rem', fontWeight: activeTab===t ? 600:400, cursor:'pointer'}}>
            {t.replace('_', ' ')}
          </button>
        ))}
      </div>

      <div style={{flex:1, marginTop:24, position:'relative'}}>
        {activeTab === 'TIMELINE' && <TimelineTab caseId={caseId} />}
        {activeTab === 'HOTSPOTS' && <HotspotsTab caseId={caseId} />}
        {activeTab === 'CAUSAL_GRAPH' && <CausalGraphTab caseId={caseId} />}
        {activeTab === 'REASONING_REPLAY' && <ReplayTab caseId={caseId} />}
      </div>
    </div>
  );
}
```

---

## 3. Timeline Tab (Recharts)

**File: `frontend/components/workspace/TimelineTab.js`**

```jsx
import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '@/lib/api';

export default function TimelineTab({ caseId }) {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    // Mock data for MVP if backend not fully wired
    setData([
      { time: '18:00', events: 10, anomaly: 0.1 },
      { time: '20:00', events: 25, anomaly: 0.2 },
      { time: '23:00', events: 50, anomaly: 0.9 }, // High anomaly
      { time: '02:00', events: 0, anomaly: 0.8 },  // Silence gap
      { time: '06:00', events: 5, anomaly: 0.1 },
    ]);
  }, [caseId]);

  return (
    <div className="card" style={{height:'100%', display:'flex', flexDirection:'column'}}>
      <h3 style={{marginBottom:16}}>Digital Timeline & Anomalies</h3>
      <div style={{flex:1}}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorAnomaly" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--anomaly-red)" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="var(--anomaly-red)" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="time" stroke="var(--text-muted)" />
            <YAxis stroke="var(--text-muted)" />
            <Tooltip contentStyle={{background:'var(--bg-elevated)', border:'1px solid var(--border-subtle)'}} />
            <Area type="monotone" dataKey="anomaly" stroke="var(--anomaly-red)" fillOpacity={1} fill="url(#colorAnomaly)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

---

## 4. Causal Graph Tab (D3.js integration stub)

**File: `frontend/components/workspace/CausalGraphTab.js`**

```jsx
import { useEffect, useRef } from 'react';
// import * as d3 from 'd3'; // Requires npm install d3

export default function CausalGraphTab({ caseId }) {
  const svgRef = useRef();

  useEffect(() => {
    // Minimal D3 stub for MVP. Full force-directed graph implemented in production.
    if (!svgRef.current) return;
    svgRef.current.innerHTML = '<text x="20" y="40" fill="var(--text-muted)">[D3 Force Graph Placeholder]</text>';
    // In actual implementation: d3.forceSimulation(nodes)...
  }, [caseId]);

  return (
    <div className="card" style={{height:'100%', position:'relative'}}>
      <h3 style={{marginBottom:16}}>Hypothesis Causal Graph</h3>
      <svg ref={svgRef} style={{width:'100%', height:'calc(100% - 40px)'}} />
    </div>
  );
}
```

## Acceptance Criteria
- [ ] Case header shows file upload button and lists uploaded files.
- [ ] Pipeline strip fetches `/pipeline/status` and shows running/complete nodes.
- [ ] Recharts Area chart renders anomaly gradient correctly.
- [ ] Tabs switch cleanly without unmounting case context.
