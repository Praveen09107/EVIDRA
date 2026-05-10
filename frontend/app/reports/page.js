'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import StatusBadge from '@/components/shared/StatusBadge';
import { api } from '@/lib/api';
import { FileText, Download } from 'lucide-react';

export default function ReportsPage() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [report, setReport] = useState(null);

  // Load case list, auto-select first
  useEffect(() => {
    api.getCases().then(c => {
      setCases(c);
      if (c.length > 0) setSelectedCase(c[0].case_id);
    });
  }, []);

  // Reload report when case changes
  useEffect(() => {
    if (!selectedCase) return;
    setReport(null);
    api.getReport(selectedCase).then(setReport);
  }, [selectedCase]);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title="Report Builder" />
        <div className="scroll-area">
          {/* Case Selector */}
          <div className="flex-between" style={{ marginBottom: 20 }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem' }}>Forensic Report</h2>
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
          </div>

          {!report ? (
            <div style={{ color: 'var(--text-muted)' }}>Loading report...</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20 }}>
              <div>
                <div className="card" style={{ padding: 24, background: '#0c0d11' }}>
                  <div style={{ textAlign: 'center', marginBottom: 24 }}>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>CONFIDENTIAL</div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: 8 }}>AIVENTRA FORENSIC INTELLIGENCE REPORT</h3>
                  </div>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: 8 }}>Executive Summary</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 20 }}>{report.executiveSummary}</p>
                  {report.sections.map((s, i) => (
                    <div key={i} style={{ padding: '10px 0', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ color: 'var(--success-green)' }}>✓</span>
                      <span style={{ fontSize: '0.85rem' }}>{i + 1}. {s}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="card" style={{ padding: 20 }}>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 16 }}>Export Options</h4>
                  {['PDF (Court-format)', 'DOCX (Editable)', 'JSON (Machine-readable)'].map((f, i) => (
                    <label key={f} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', fontSize: '0.8rem', cursor: 'pointer' }}>
                      <input type="radio" name="fmt" defaultChecked={i === 0} /> {f}
                    </label>
                  ))}
                  <button className="btn btn-primary" style={{ width: '100%', marginTop: 16 }}>
                    <Download size={14} /> Download Report
                  </button>
                </div>
                <div className="card" style={{ padding: 16, marginTop: 12 }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-faint)' }}>
                    Generated: {new Date(report.generatedAt).toLocaleString('en-IN')}<br />
                    Chain: {report.chainValid ? '✓ Verified' : '⚠ Error'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
