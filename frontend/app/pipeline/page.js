'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import StatusBadge from '@/components/shared/StatusBadge';
import { api } from '@/lib/api';

import { Play, RotateCcw } from 'lucide-react';

const TIER_LABELS = ['Ingestion','Normalization','Domain Analysis','Temporal Intelligence','Fusion','Reasoning','Guidance','Audit'];

export default function PipelineExplorerPage() {
  const [agents, setAgents] = useState([]);
  const [selected, setSelected] = useState(null);
  useEffect(() => { api.getAgents().then(setAgents); }, []);

  const tiers = {};
  agents.forEach(a => { if (!tiers[a.tier]) tiers[a.tier] = []; tiers[a.tier].push(a); });

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title="Pipeline Explorer" />
        <div className="scroll-area">
          <div className="flex-between" style={{ marginBottom: 20 }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem' }}>8-Tier Agent DAG</h2>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary btn-sm"><Play size={12} /> Replay Animation</button>
              <button className="btn btn-secondary btn-sm"><RotateCcw size={12} /> Reset</button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 320px' : '1fr', gap: 20 }}>
            <div>
              {Object.entries(tiers).sort(([a],[b]) => a - b).map(([tier, tierAgents]) => (
                <div key={tier} style={{ marginBottom: 20 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <span style={{ fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--text-faint)', textTransform: 'uppercase', minWidth: 50 }}>Tier {tier}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{TIER_LABELS[tier] || ''}</span>
                    <div style={{ flex: 1, height: 1, background: 'var(--border-subtle)' }} />
                  </div>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', paddingLeft: 62 }}>
                    {tierAgents.map(a => (
                      <div key={a.id} className="card card-interactive" onClick={() => setSelected(a)}
                        style={{ padding: '12px 16px', cursor: 'pointer', minWidth: 140,
                          borderColor: selected?.id === a.id ? 'var(--accent-cyan)' : undefined,
                          boxShadow: selected?.id === a.id ? 'var(--shadow-glow-cyan)' : undefined }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success-green)' }} />
                          <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{a.name}</span>
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)' }}>{a.category} • {a.model?.split(' ')[0]}</div>
                      </div>
                    ))}
                  </div>
                  {Number(tier) < 7 && (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0' }}>
                      <div style={{ width: 2, height: 20, background: 'var(--border-subtle)' }} />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {selected && (
              <div className="card animate-in" style={{ padding: 20, alignSelf: 'start', position: 'sticky', top: 0 }}>
                <div className="flex-between" style={{ marginBottom: 12 }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>{selected.name}</h3>
                  <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✕</button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: '0.8rem' }}>
                  <div className="flex-between"><span style={{ color: 'var(--text-muted)' }}>Agent ID</span><span style={{ fontFamily: 'var(--font-mono)' }}>{selected.id}</span></div>
                  <div className="flex-between"><span style={{ color: 'var(--text-muted)' }}>Tier</span><span>{selected.tier}</span></div>
                  <div className="flex-between"><span style={{ color: 'var(--text-muted)' }}>Category</span><StatusBadge status={selected.category} size="sm" /></div>
                  <div className="flex-between"><span style={{ color: 'var(--text-muted)' }}>Model</span><span>{selected.model}</span></div>
                  <div className="flex-between"><span style={{ color: 'var(--text-muted)' }}>Port</span><span style={{ fontFamily: 'var(--font-mono)' }}>{selected.port}</span></div>
                  <div className="flex-between"><span style={{ color: 'var(--text-muted)' }}>Status</span><StatusBadge status="DONE" size="sm" /></div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
