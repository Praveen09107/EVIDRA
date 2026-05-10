'use client';
export default function ConfidenceBar({ value, label, color, compact = false }) {
  const pct = Math.round((value || 0) * 100);
  const barColor = color || (pct >= 70 ? 'var(--success-green)' : pct >= 40 ? 'var(--warning-amber)' : 'var(--anomaly-red)');
  const h = compact ? 4 : 6;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
      <div style={{ flex: 1, height: h, background: 'rgba(255,255,255,0.06)', borderRadius: h/2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: barColor, borderRadius: h/2, transition: 'width 0.5s ease' }} />
      </div>
      {label && <span style={{ fontSize: '0.7rem', color: 'var(--text-faint)', whiteSpace: 'nowrap' }}>{label}</span>}
    </div>
  );
}
