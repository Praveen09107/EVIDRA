'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, MapPin, Clock, FileText, AlertTriangle } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import StatusBadge from '@/components/shared/StatusBadge';
import { api } from '@/lib/api';

const HYPO_COLORS = {
  HOMICIDE: '#F87171', SUICIDE: '#FBBF24', ACCIDENT: '#34D399', NATURAL: '#60A5FA',
};

export default function CaseLobbyPage() {
  const router = useRouter();
  const [cases, setCases] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [newCase, setNewCase] = useState({ title: '', location: '', description: '' });

  useEffect(() => { api.getCases().then(setCases); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    await api.createCase(newCase);
    setShowModal(false);
    setNewCase({ title: '', location: '', description: '' });
    api.getCases().then(setCases);
  };

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title="Active Cases" />
        <div className="scroll-area">
          {/* Header row */}
          <div className="flex-between" style={{ marginBottom: '24px' }}>
            <div>
              <h2 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-display)' }}>
                Case Lobby
              </h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                {cases.length} active investigation{cases.length !== 1 ? 's' : ''}
              </p>
            </div>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              <Plus size={16} /> New Case
            </button>
          </div>

          {/* Case grid */}
          <div className="grid-3">
            {cases.map((c, i) => (
              <div
                key={c.case_id}
                className="card card-interactive"
                style={{ cursor: 'pointer', animationDelay: `${i * 80}ms` }}
                className="card card-interactive animate-in"
                onClick={() => router.push(`/cases/${c.case_id}`)}
              >
                {/* Case header */}
                <div className="flex-between" style={{ marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-faint)' }}>
                    {c.case_number}
                  </span>
                  <StatusBadge status={c.status} size="sm" />
                </div>

                {/* Title */}
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '8px', lineHeight: 1.3 }}>
                  {c.title}
                </h3>

                {/* Meta row */}
                <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <MapPin size={12} /> {c.location}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FileText size={12} /> {c.evidence_count} files
                  </span>
                </div>

                {/* Hypothesis pills */}
                {c.hypothesis && (
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
                    {c.hypothesis.slice(0, 3).map((h) => (
                      <span key={h.key} style={{
                        fontSize: '0.65rem', padding: '2px 8px', borderRadius: '9999px',
                        background: `${HYPO_COLORS[h.key]}15`, color: HYPO_COLORS[h.key],
                        border: `1px solid ${HYPO_COLORS[h.key]}30`, fontWeight: 600,
                      }}>
                        {h.key} {Math.round(h.probability * 100)}%
                      </span>
                    ))}
                  </div>
                )}

                {/* Agent progress */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.round(((c.agents_completed || 0) / (c.agents_total || 17)) * 100)}%`,
                      height: '100%',
                      background: c.pipeline_status === 'COMPLETE' ? 'var(--success-green)' : 'var(--accent-cyan)',
                      borderRadius: 2,
                      transition: 'width 0.5s ease',
                    }} />
                  </div>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                    {c.agents_completed || 0}/{c.agents_total || 17}
                  </span>
                </div>

                {/* Risk level footer */}
                {c.risk_level === 'HIGH' || c.risk_level === 'CRITICAL' ? (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '6px', marginTop: '12px',
                    fontSize: '0.7rem', color: 'var(--anomaly-red)',
                  }}>
                    <AlertTriangle size={12} /> {c.risk_level} Risk
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          {/* Create Case Modal */}
          {showModal && (
            <div className="modal-overlay" onClick={() => setShowModal(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '20px' }}>
                  Create New Case
                </h3>
                <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      Case Title
                    </label>
                    <input
                      value={newCase.title}
                      onChange={(e) => setNewCase({ ...newCase, title: e.target.value })}
                      placeholder="e.g. Victim Name Death Investigation"
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      Location
                    </label>
                    <input
                      value={newCase.location}
                      onChange={(e) => setNewCase({ ...newCase, location: e.target.value })}
                      placeholder="e.g. Pitampura, New Delhi"
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      Description
                    </label>
                    <textarea
                      value={newCase.description}
                      onChange={(e) => setNewCase({ ...newCase, description: e.target.value })}
                      placeholder="Brief case summary..."
                      rows={3}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '8px' }}>
                    <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary">
                      <Plus size={14} /> Create Case
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
