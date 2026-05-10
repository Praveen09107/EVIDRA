'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import ConfidenceBar from '@/components/shared/ConfidenceBar';
import { api } from '@/lib/api';
import { Brain, Thermometer, AlertTriangle } from 'lucide-react';

const HYPO_COLORS = { HOMICIDE:'#F87171', SUICIDE:'#FBBF24', ACCIDENT:'#34D399', NATURAL:'#60A5FA', UNDETERMINED:'#9CA3AF' };
const TABS = ['Hypothesis', 'TOD Explainability', 'Anomaly Analysis'];

export default function XAIStudioPage() {
  const [tab, setTab] = useState(0);
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [hypothesis, setHypothesis] = useState(null);
  const [todResult, setTodResult] = useState(null);
  const [anomalies, setAnomalies] = useState([]);

  // Load case list, then auto-select first case
  useEffect(() => {
    api.getCases().then(c => {
      setCases(c);
      if (c.length > 0) setSelectedCase(c[0].case_id);
    });
  }, []);

  // Reload data when case selection changes
  useEffect(() => {
    if (!selectedCase) return;
    api.getHypothesis(selectedCase).then(setHypothesis);
    api.getTodResult(selectedCase).then(setTodResult);
    api.getAnomalies(selectedCase).then(setAnomalies);
  }, [selectedCase]);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title="XAI & Uncertainty Studio" />

        {/* Case Selector + Tab Bar */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16, borderBottom: '1px solid var(--border-subtle)' }}>
          <select
            value={selectedCase || ''}
            onChange={(e) => setSelectedCase(e.target.value)}
            style={{
              background: 'var(--bg-base)', border: '1px solid var(--border-subtle)',
              borderRadius: 6, padding: '6px 10px', color: 'var(--text-primary)',
              fontSize: '0.8rem', fontFamily: 'var(--font-mono)',
            }}
          >
            {cases.map(c => (
              <option key={c.case_id} value={c.case_id}>{c.case_number} — {c.title}</option>
            ))}
          </select>
          <div style={{ flex: 1 }} />
          <div className="tab-bar" style={{ border: 'none' }}>
            {TABS.map((t, i) => (
              <button key={t} className={`tab-btn${tab === i ? ' active' : ''}`} onClick={() => setTab(i)}>
                {[<Brain size={14} key="b"/>, <Thermometer size={14} key="t"/>, <AlertTriangle size={14} key="a"/>][i]}
                <span style={{ marginLeft: 6 }}>{t}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="scroll-area">
          {tab === 0 && hypothesis && <HypothesisXAI hypothesis={hypothesis} />}
          {tab === 1 && todResult && <TodXAI todResult={todResult} />}
          {tab === 2 && <AnomalyXAI anomalies={anomalies} />}
        </div>
      </div>
    </div>
  );
}

function HypothesisXAI({ hypothesis }) {
  return (<div className="animate-in">
    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', marginBottom: 20 }}>Bayesian Hypothesis Transparency</h3>
    <div className="grid-4" style={{ marginBottom: 24 }}>
      {Object.entries(hypothesis.posteriors).map(([k, v]) => (
        <div key={k} className="card" style={{ padding: 20, textAlign: 'center', borderTop: `3px solid ${HYPO_COLORS[k]}` }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', textTransform: 'uppercase', marginBottom: 8 }}>{k}</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: HYPO_COLORS[k] }}>{Math.round(v * 100)}%</div>
          <ConfidenceBar value={v} color={HYPO_COLORS[k]} />
        </div>
      ))}
    </div>
    <div className="card" style={{ padding: 20 }}>
      <h4 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 16 }}>Evidence Signal Contributions</h4>
      {hypothesis.signals.map((s, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
          <span style={{ flex: 1, fontSize: '0.85rem' }}>{s.signal.replace(/_/g, ' ')}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: 60 }}>{s.source}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', width: 60 }}>LR×{s.lr.toFixed(1)}</span>
          <span style={{ color: HYPO_COLORS[s.direction], fontWeight: 600, fontSize: '0.8rem', width: 80 }}>↑ {s.direction}</span>
          <div style={{ width: 100 }}><ConfidenceBar value={s.confidence} compact /></div>
        </div>
      ))}
    </div>
  </div>);
}

function TodXAI({ todResult }) {
  // Compute sensitivity dynamically from Henssge inputs
  const ambTemp = todResult?.henssgeInputs?.ambientTemp;
  const bodyWt = todResult?.henssgeInputs?.bodyWeight;
  return (<div className="animate-in">
    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', marginBottom: 20 }}>TOD Estimation Explainability</h3>
    <div className="card" style={{ padding: 20, marginBottom: 20 }}>
      <h4 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 16 }}>Component Weight Breakdown</h4>
      {todResult.componentContributions.map(c => (
        <div key={c.component} style={{ marginBottom: 14 }}>
          <div className="flex-between" style={{ marginBottom: 4 }}>
            <span style={{ fontSize: '0.85rem' }}>{c.component.replace(/_/g, ' ')}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>{Math.round(c.weight * 100)}%</span>
          </div>
          <ConfidenceBar value={c.weight} color="var(--accent-indigo)" />
          <div style={{ fontSize: '0.75rem', color: 'var(--text-faint)', marginTop: 4 }}>{c.description}</div>
        </div>
      ))}
    </div>
    <div className="card" style={{ padding: 20 }}>
      <h4 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 12 }}>Sensitivity Analysis</h4>
      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        {ambTemp != null
          ? `Ambient temperature recorded at ${ambTemp}°C. Varying by ±2°C shifts TOD estimate by ±45 minutes.`
          : 'Ambient temperature sensitivity data not available.'}
        {bodyWt != null
          ? ` Body weight recorded at ${bodyWt}kg. Variation of ±10kg shifts estimate by ±30 minutes.`
          : ''}
      </p>
    </div>
  </div>);
}

function AnomalyXAI({ anomalies }) {
  return (<div className="animate-in">
    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', marginBottom: 20 }}>Anomaly Detection Transparency</h3>
    {anomalies.map(a => (
      <div key={a.id} className="card" style={{ padding: 16, marginBottom: 12, borderLeft: `4px solid ${a.severity === 'CRITICAL' ? 'var(--anomaly-red)' : 'var(--warning-amber)'}` }}>
        <div className="flex-between" style={{ marginBottom: 8 }}>
          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{a.title}</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: a.score > 0.8 ? 'var(--anomaly-red)' : 'var(--warning-amber)' }}>{a.score.toFixed(2)}</span>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{a.detail}</p>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-faint)', marginTop: 8 }}>Rule: {a.rule}</div>
      </div>
    ))}
  </div>);
}
