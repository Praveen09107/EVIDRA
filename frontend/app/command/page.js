'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import MetricCard from '@/components/shared/MetricCard';
import StatusBadge from '@/components/shared/StatusBadge';
import { api } from '@/lib/api';

import { Activity, Bot, Cpu, Zap, Circle } from 'lucide-react';

export default function CommandCenterPage() {
  const [agents, setAgents] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  useEffect(() => {
    api.getAgents().then(setAgents);
    api.getSystemMetrics().then(setMetrics);
    api.getAuditLog('system').then(setActivityLog);
  }, []);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title="Command Center" />
        <div className="scroll-area">
          <div className="grid-4" style={{ marginBottom: 24 }}>
            <MetricCard label="Active Pipelines" value={metrics?.active_pipelines ?? 1} icon={Activity} color="var(--accent-cyan)" />
            <MetricCard label="Agents Online" value={agents.length} icon={Bot} color="var(--success-green)" />
            <MetricCard label="LLM Tokens Today" value={(metrics?.llm_tokens_today ?? 42350).toLocaleString()} icon={Zap} color="var(--warning-amber)" />
            <MetricCard label="System Health" value={metrics?.system_health ?? 'HEALTHY'} icon={Cpu} color="var(--success-green)" />
          </div>

          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 14 }}>Agent Fleet Status</h3>
          <div className="grid-4" style={{ marginBottom: 24 }}>
            {agents.map(a => (
              <div key={a.id} className="card" style={{ padding: 14 }}>
                <div className="flex-between" style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{a.name}</span>
                  <StatusBadge status="DONE" size="sm" />
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', display: 'flex', gap: 8 }}>
                  <span>T{a.tier}</span>
                  <span>{a.category}</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{a.model?.split(' ')[0]}</span>
                </div>
              </div>
            ))}
          </div>

          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 14 }}>Activity Stream</h3>
          <div className="card" style={{ padding: 0, maxHeight: 300, overflowY: 'auto' }}>
            {activityLog.map(e => (
              <div key={e.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.8rem' }}>
                <Circle size={6} fill={e.result === 'SUCCESS' ? 'var(--success-green)' : 'var(--anomaly-red)'} color="transparent" />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-faint)', minWidth: 70 }}>
                  {new Date(e.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>{e.user}</span>
                <StatusBadge status={e.action.split('_')[0]} size="sm" />
                <span>{e.resource}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
