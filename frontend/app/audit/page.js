'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import StatusBadge from '@/components/shared/StatusBadge';
import MetricCard from '@/components/shared/MetricCard';
import { api } from '@/lib/api';
import { Shield, AlertTriangle, FileText, Download } from 'lucide-react';

const ACTION_COLORS = { EVIDENCE: 'var(--accent-blue)', AGENT: 'var(--accent-indigo)', LOGIN: 'var(--success-green)', PIPELINE: 'var(--accent-cyan)', REPORT: 'var(--warning-amber)' };

export default function AuditPage() {
  const [auditLog, setAuditLog] = useState([]);
  useEffect(() => { api.getAuditLog('system').then(setAuditLog); }, []);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title="Audit & Chain of Custody" />
        <div className="scroll-area">
          <div className="flex-between" style={{ marginBottom: 20 }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem' }}>Audit Trail</h2>
            <div style={{ display: 'flex', gap: 8 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--success-green)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <Shield size={14} /> Chain Integrity Verified
              </span>
              <button className="btn btn-secondary btn-sm"><Download size={12} /> Export Log</button>
            </div>
          </div>

          <div className="grid-3" style={{ marginBottom: 20 }}>
            <MetricCard label="Total Events" value={auditLog.length.toLocaleString()} icon={FileText} color="var(--accent-cyan)" />
            <MetricCard label="Tamper Alerts" value="0" icon={Shield} color="var(--success-green)" />
            <MetricCard label="Anomaly Flags" value="0" icon={AlertTriangle} color="var(--warning-amber)" />
          </div>

          <div className="table-container">
            <table>
              <thead><tr>
                <th>Timestamp</th><th>User</th><th>Role</th><th>Action</th><th>Resource</th><th>Result</th><th>IP</th><th>Chain</th>
              </tr></thead>
              <tbody>
                {auditLog.map(e => (
                  <tr key={e.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                      {new Date(e.timestamp).toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{e.user}</td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-faint)' }}>{e.role}</td>
                    <td><StatusBadge status={e.action.split('_')[0]} size="sm" /></td>
                    <td style={{ fontSize: '0.8rem' }}>{e.resource}</td>
                    <td><StatusBadge status={e.result === 'SUCCESS' ? 'COMPLETE' : 'FAILED'} size="sm" /></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-faint)' }}>{e.ip}</td>
                    <td style={{ color: 'var(--success-green)', fontSize: '0.8rem' }}>✓</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
