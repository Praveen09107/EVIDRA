# DEV B EXECUTION GUIDE — PART 3: Case Workspace & Data Visualization
**Owner:** Dev B | **Hours:** 6:00–14:00 | **Priority:** CRITICAL

---

## 1. PHASE 8 — CASE WORKSPACE SHELL (Hour 6:00–7:00)

The workspace (`/cases/[caseId]`) is the heart of AIVENTRA. It consists of the Header (for uploads), the Pipeline Strip (live telemetry), and the Tabbed interface for deep analysis.

### Step 1.1 — Main Workspace Page

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
import LoadingSpinner from '@/components/shared/LoadingSpinner';

const TABS = [
  { id: 'TIMELINE', label: 'Timeline & Anomalies' },
  { id: 'HOTSPOTS', label: 'Spatial Hotspots' },
  { id: 'CAUSAL_GRAPH', label: 'Hypothesis Graph' },
  { id: 'REASONING_REPLAY', label: 'Reasoning Replay' }
];

export default function CaseWorkspace() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [activeTab, setActiveTab] = useState('TIMELINE');
  const [error, setError] = useState(null);

  const fetchCase = () => {
    api.getCase(caseId)
       .then(setCaseData)
       .catch(err => {
         console.error(err);
         // Mock fallback
         setCaseData({ case_id: caseId, case_number: 'CASE-MOCK', title: 'Mock Case', status: 'IN_ANALYSIS', files: [] });
       });
  };

  useEffect(() => {
    fetchCase();
    
    // Live WS updates
    const ws = new TelemetryClient((msg) => {
      // Refresh case data when pipeline finishes to get new outputs
      if (msg.event === 'PIPELINE_COMPLETED' && msg.case_id === caseId) {
        fetchCase();
      }
    });
    ws.connect();
    return () => ws.disconnect();
  }, [caseId]);

  if (error) return <div className="empty-state" style={{color: 'var(--anomaly-red)'}}>{error}</div>;
  if (!caseData) return <LoadingSpinner text="Loading workspace..." size={40} />;

  return (
    <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* ── 1. Case Header & Uploads ── */}
      <CaseHeader caseData={caseData} onRefresh={fetchCase} />
      
      {/* ── 2. Live Pipeline Telemetry ── */}
      <PipelineStrip caseId={caseId} />
      
      {/* ── 3. Tab Navigation ── */}
      <div className="tab-bar">
        {TABS.map(t => (
          <button key={t.id} 
                  className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── 4. Active Tab Content ── */}
      <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
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

## 2. PHASE 9 — EVIDENCE UPLOAD & PIPELINE CONTROL (Hour 7:00–8:30)

### Step 2.1 — CaseHeader & File Uploads

**File: `frontend/components/workspace/CaseHeader.js`**

```jsx
import { useState } from 'react';
import { api } from '@/lib/api';
import StatusBadge from '@/components/shared/StatusBadge';

const DOC_TYPES = ['AUTOPSY_REPORT', 'CDR', 'FINANCIAL_RECORDS', 'CCTV', 'DEVICE_DATA'];

export default function CaseHeader({ caseData, onRefresh }) {
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState('AUTOPSY_REPORT');
  const [triggering, setTriggering] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('doc_type', docType);
    
    try {
      await api.uploadFile(caseData.case_id, fd);
      onRefresh(); // Refresh file list
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
      e.target.value = ''; // Reset input
    }
  };

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await api.triggerPipeline(caseData.case_id);
      // Let WS handle the status refresh, but we can do an optimistic refresh
      setTimeout(onRefresh, 1000);
    } catch (err) {
      alert('Trigger failed: ' + err.message);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 24, padding: 24 }}>
      <div className="flex-between">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.8rem', margin: 0 }}>
              {caseData.title}
            </h1>
            <StatusBadge status={caseData.status} />
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <span style={{ fontFamily: 'var(--font-mono)' }}>{caseData.case_number}</span>
            <span style={{ margin: '0 8px' }}>•</span>
            📍 {caseData.location}
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <select value={docType} onChange={e=>setDocType(e.target.value)} 
                    style={{ fontSize: '0.75rem', padding: '4px 8px' }}>
              {DOC_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
            <label className="btn btn-secondary" style={{ textAlign: 'center', fontSize: '0.8rem' }}>
              {uploading ? 'Uploading...' : 'Upload Evidence'}
              <input type="file" onChange={handleUpload} style={{ display: 'none' }} disabled={uploading} />
            </label>
          </div>
          
          <button className="btn btn-primary" onClick={handleTrigger} disabled={triggering || caseData.files?.length === 0}
                  style={{ padding: '16px 24px', fontSize: '1rem' }}>
            {triggering ? 'Initiating...' : 'Run AI Pipeline ▶'}
          </button>
        </div>
      </div>

      {/* Uploaded Files List */}
      {caseData.files?.length > 0 && (
        <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {caseData.files.map(f => (
            <div key={f.file_id} style={{
              background: 'var(--bg-dark)', padding: '6px 12px', borderRadius: 4,
              border: '1px solid var(--border-subtle)', fontSize: '0.75rem',
              display: 'flex', alignItems: 'center', gap: 8
            }}>
              <span style={{ color: 'var(--accent-blue)' }}>{f.doc_type}</span>
              <span style={{ color: 'var(--text-muted)' }}>{f.original_name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Step 2.2 — Live Pipeline Strip

**File: `frontend/components/workspace/PipelineStrip.js`**

```jsx
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { TelemetryClient } from '@/lib/ws';
import AgentPill from '@/components/agents/AgentPill';

// The canonical order of agents for the visual strip
const STRIP_AGENTS = [
  'evidence_parser', 'format_normalizer', 'autopsy_agent', 'cdr_analyzer', 
  'tod_agent', 'timeline_anomaly', 'hotspot_engine', 'hypothesis_manager', 'reasoning_replay'
];

export default function PipelineStrip({ caseId }) {
  const [pipelineState, setPipelineState] = useState({});

  useEffect(() => {
    // Initial fetch
    api.getPipelineStatus(caseId)
       .then(res => {
         if (res.agents) {
           const states = {};
           res.agents.forEach(a => states[a.agent_id] = a.status);
           setPipelineState(states);
         }
       }).catch(() => {});

    // Listen for live updates
    const ws = new TelemetryClient((msg) => {
      if (msg.case_id !== caseId) return;
      if (msg.event === 'AGENT_STARTED') {
        setPipelineState(prev => ({ ...prev, [msg.data.agent_id]: 'RUNNING' }));
      }
      if (msg.event === 'AGENT_COMPLETED') {
        setPipelineState(prev => ({ ...prev, [msg.data.agent_id]: 'COMPLETE' }));
      }
      if (msg.event === 'AGENT_FAILED') {
        setPipelineState(prev => ({ ...prev, [msg.data.agent_id]: 'FAILED' }));
      }
    });
    ws.connect();
    return () => ws.disconnect();
  }, [caseId]);

  return (
    <div className="card-glass" style={{ padding: '16px 24px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8, overflowX: 'auto' }}>
      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginRight: 16 }}>
        Live Execution
      </span>
      
      {STRIP_AGENTS.map((agentId, i) => (
        <div key={agentId} style={{ display: 'flex', alignItems: 'center' }}>
          <AgentPill agentId={agentId} status={pipelineState[agentId] || 'PENDING'} />
          {i < STRIP_AGENTS.length - 1 && (
            <div style={{
              width: 24, height: 2, margin: '0 8px',
              background: pipelineState[agentId] === 'COMPLETE' ? 'var(--success-green)' : 'var(--border-subtle)',
              opacity: pipelineState[agentId] === 'COMPLETE' ? 0.5 : 1
            }} />
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## 3. PHASE 10 — VISUALIZATION TABS (Hour 8:30–14:00)

### Step 3.1 — TimelineTab (Recharts)

**File: `frontend/components/workspace/TimelineTab.js`**

```jsx
import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { api } from '@/lib/api';

const MOCK_TIMELINE = [
  { time: 'May 8 18:00', events: 10, anomaly: 0.1, desc: 'Normal calling pattern' },
  { time: 'May 8 20:00', events: 25, anomaly: 0.2, desc: 'Increased location pinging' },
  { time: 'May 8 23:00', events: 50, anomaly: 0.95, desc: 'Hotspot: Sudden silence + 50k withdrawal' },
  { time: 'May 9 02:00', events: 0, anomaly: 0.85, desc: 'Estimated TOD overlap' },
  { time: 'May 9 06:00', events: 5, anomaly: 0.1, desc: 'Body discovered' },
];

export default function TimelineTab({ caseId }) {
  const [data, setData] = useState([]);

  useEffect(() => {
    // Swap with API when ready
    setData(MOCK_TIMELINE);
  }, [caseId]);

  return (
    <div className="card" style={{ height: 500, display: 'flex', flexDirection: 'column' }}>
      <h3 style={{ marginBottom: 16 }}>Digital Timeline & Anomaly Scores</h3>
      <div style={{ flex: 1, padding: '10px 0' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorAnomaly" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--anomaly-red)" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="var(--anomaly-red)" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
            <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickMargin={10} />
            <YAxis stroke="var(--text-muted)" fontSize={12} />
            
            <Tooltip 
              contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 8 }}
              labelStyle={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: 8 }}
              itemStyle={{ fontSize: '0.85rem' }}
            />
            
            <Area type="monotone" dataKey="events" name="Event Volume" stroke="var(--accent-blue)" fillOpacity={1} fill="url(#colorEvents)" />
            <Area type="monotone" dataKey="anomaly" name="Anomaly Score" stroke="var(--anomaly-red)" strokeWidth={2} fillOpacity={1} fill="url(#colorAnomaly)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

### Step 3.2 — CausalGraphTab (D3.js integration)

**File: `frontend/components/workspace/CausalGraphTab.js`**

*Note: For the 24h sprint, we will use a simplified React representation if D3 forces are too complex, but here is a functional D3 snippet.*

```jsx
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const MOCK_GRAPH = {
  nodes: [
    { id: 'Hypothesis: Homicide', group: 1, radius: 20 },
    { id: 'Claim: Blunt Trauma', group: 2, radius: 15 },
    { id: 'Evidence: Autopsy', group: 3, radius: 10 },
    { id: 'Claim: Left at 10PM', group: 2, radius: 15 },
    { id: 'Evidence: CCTV', group: 3, radius: 10 },
  ],
  links: [
    { source: 'Claim: Blunt Trauma', target: 'Hypothesis: Homicide', value: 1 },
    { source: 'Evidence: Autopsy', target: 'Claim: Blunt Trauma', value: 1 },
    { source: 'Evidence: CCTV', target: 'Claim: Left at 10PM', value: 1 },
  ]
};

export default function CausalGraphTab({ caseId }) {
  const svgRef = useRef();

  useEffect(() => {
    if (!svgRef.current) return;
    const width = svgRef.current.parentElement.clientWidth;
    const height = 450;
    
    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove();
    
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);
      
    const simulation = d3.forceSimulation(MOCK_GRAPH.nodes)
      .force('link', d3.forceLink(MOCK_GRAPH.links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));
      
    const link = svg.append('g')
      .selectAll('line')
      .data(MOCK_GRAPH.links)
      .join('line')
      .attr('stroke', 'var(--border-focus)')
      .attr('stroke-width', 2);
      
    const node = svg.append('g')
      .selectAll('circle')
      .data(MOCK_GRAPH.nodes)
      .join('circle')
      .attr('r', d => d.radius)
      .attr('fill', d => d.group === 1 ? 'var(--anomaly-red)' : d.group === 2 ? 'var(--warning-amber)' : 'var(--accent-blue)')
      .call(drag(simulation));
      
    const text = svg.append('g')
      .selectAll('text')
      .data(MOCK_GRAPH.nodes)
      .join('text')
      .text(d => d.id)
      .attr('font-size', '10px')
      .attr('fill', 'var(--text-primary)')
      .attr('dx', 15)
      .attr('dy', 4);

    simulation.on('tick', () => {
      link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      node.attr('cx', d => d.x).attr('cy', d => d.y);
      text.attr('x', d => d.x).attr('y', d => d.y);
    });

    function drag(sim) {
      return d3.drag()
        .on('start', e => { if (!e.active) sim.alphaTarget(0.3).restart(); e.subject.fx = e.subject.x; e.subject.fy = e.subject.y; })
        .on('drag', e => { e.subject.fx = e.x; e.subject.fy = e.y; })
        .on('end', e => { if (!e.active) sim.alphaTarget(0); e.subject.fx = null; e.subject.fy = null; });
    }
  }, [caseId]);

  return (
    <div className="card" style={{ height: 500 }}>
      <h3 style={{ marginBottom: 16 }}>Argument Graph</h3>
      <svg ref={svgRef} style={{ width: '100%', height: 'calc(100% - 40px)', background: 'var(--bg-dark)', borderRadius: 6 }} />
    </div>
  );
}
```
