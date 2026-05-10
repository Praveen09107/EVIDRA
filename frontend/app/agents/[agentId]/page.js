'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import StatusBadge from '@/components/shared/StatusBadge';
import MetricCard from '@/components/shared/MetricCard';
import { api } from '@/lib/api';
import { FlaskConical, Play, Clock, Zap } from 'lucide-react';

export default function AgentLabPage() {
  const { agentId } = useParams();
  const [agent, setAgent] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  useEffect(() => { api.getAgent(agentId).then(setAgent); }, [agentId]);

  const runTest = async () => {
    setTesting(true);
    const r = await api.testAgent(agentId, { sample: true });
    setTestResult(r);
    setTesting(false);
  };

  if (!agent) return <div className="app-layout"><Sidebar /><div className="main-content"><TopHeader title="Loading..." /></div></div>;

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title={`Agent Lab — ${agent.name}`} />
        <div className="scroll-area">
          <div className="card" style={{ padding: 24, marginBottom: 20, borderTop: '3px solid var(--accent-cyan)' }}>
            <div className="flex-between">
              <div>
                <h2 style={{ fontSize: '1.3rem', fontWeight: 600 }}>{agent.name}</h2>
                <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span>Tier {agent.tier}</span>
                  <StatusBadge status={agent.category} size="sm" />
                  <span>Model: {agent.model}</span>
                  <span>Port: {agent.port}</span>
                </div>
              </div>
              <button className="btn btn-primary" onClick={runTest} disabled={testing}>
                {testing ? 'Running...' : <><Play size={14} /> Run Test</>}
              </button>
            </div>
          </div>

          <div className="grid-3" style={{ marginBottom: 20 }}>
            <MetricCard label="Avg Duration" value="2.4s" icon={Clock} color="var(--accent-cyan)" />
            <MetricCard label="LLM Tokens/Run" value="3,200" icon={Zap} color="var(--warning-amber)" />
            <MetricCard label="Success Rate" value="98.5%" icon={FlaskConical} color="var(--success-green)" />
          </div>

          {testResult && (
            <div className="card animate-in" style={{ padding: 20 }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 12 }}>Test Result</h3>
              <div className="flex-between" style={{ marginBottom: 8 }}>
                <StatusBadge status={testResult.status || 'DONE'} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-faint)' }}>
                  {testResult.duration_ms}ms
                </span>
              </div>
              <pre style={{ background: 'var(--bg-base)', padding: 16, borderRadius: 8, fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', overflow: 'auto', maxHeight: 300 }}>
                {JSON.stringify(testResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
