'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import StatusBadge from '@/components/shared/StatusBadge';
import { api } from '@/lib/api';
import { Search, FlaskConical } from 'lucide-react';

const CAT_COLORS = { INGEST:'var(--accent-cyan)', NLP:'var(--accent-indigo)', TABULAR:'var(--accent-blue)', VISION:'#A78BFA', HYBRID:'var(--warning-amber)', ML:'#F472B6', FUSION:'#FB923C', REASONING:'var(--anomaly-red)', XAI:'var(--success-green)', GUIDANCE:'var(--accent-blue)', AUDIT:'var(--text-muted)' };

export default function AgentDirectoryPage() {
  const router = useRouter();
  const [agents, setAgents] = useState([]);
  const [filter, setFilter] = useState('ALL');
  useEffect(() => { api.getAgents().then(setAgents); }, []);

  const cats = ['ALL', ...new Set(agents.map(a => a.category))];
  const filtered = filter === 'ALL' ? agents : agents.filter(a => a.category === filter);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title="Agent Directory" />
        <div className="scroll-area">
          <div className="flex-between" style={{ marginBottom: 20 }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem' }}>17 Specialized Agents</h2>
            <div style={{ display: 'flex', gap: 6 }}>
              {cats.map(c => (
                <button key={c} className={`btn btn-sm ${filter === c ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFilter(c)}>
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div className="grid-3">
            {filtered.map((a, i) => (
              <div key={a.id} className="card card-interactive animate-in" style={{ cursor: 'pointer', animationDelay: `${i * 50}ms` }}
                onClick={() => router.push(`/agents/${a.id}`)}>
                <div className="flex-between" style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: CAT_COLORS[a.category] || 'var(--text-faint)' }} />
                    <span style={{ fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--text-faint)' }}>T{a.tier}</span>
                  </div>
                  <StatusBadge status={a.category} size="sm" />
                </div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 6 }}>{a.name}</h3>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 10 }}>Model: {a.model}</div>
                <button className="btn btn-ghost btn-sm" style={{ width: '100%' }}>
                  <FlaskConical size={12} /> Open Lab
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
