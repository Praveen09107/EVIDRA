'use client';
const STATUS_CONFIG = {
  OPEN: { bg: 'rgba(34,199,213,0.12)', color: '#22C7D5', border: 'rgba(34,199,213,0.3)' },
  IN_ANALYSIS: { bg: 'rgba(251,191,36,0.12)', color: '#FBBF24', border: 'rgba(251,191,36,0.3)' },
  REVIEW: { bg: 'rgba(99,102,241,0.12)', color: '#6366F1', border: 'rgba(99,102,241,0.3)' },
  CLOSED: { bg: 'rgba(107,114,128,0.12)', color: '#9CA3AF', border: 'rgba(107,114,128,0.3)' },
  COMPLETE: { bg: 'rgba(34,197,94,0.12)', color: '#22C55E', border: 'rgba(34,197,94,0.3)' },
  DONE: { bg: 'rgba(34,197,94,0.12)', color: '#22C55E', border: 'rgba(34,197,94,0.3)' },
  RUNNING: { bg: 'rgba(251,191,36,0.12)', color: '#FBBF24', border: 'rgba(251,191,36,0.3)' },
  PENDING: { bg: 'rgba(107,114,128,0.12)', color: '#6B7280', border: 'rgba(107,114,128,0.3)' },
  FAILED: { bg: 'rgba(239,68,68,0.12)', color: '#EF4444', border: 'rgba(239,68,68,0.3)' },
  CRITICAL: { bg: 'rgba(239,68,68,0.12)', color: '#EF4444', border: 'rgba(239,68,68,0.3)' },
  HIGH: { bg: 'rgba(249,115,115,0.12)', color: '#F97373', border: 'rgba(249,115,115,0.3)' },
  MEDIUM: { bg: 'rgba(251,191,36,0.12)', color: '#FBBF24', border: 'rgba(251,191,36,0.3)' },
  LOW: { bg: 'rgba(96,165,250,0.12)', color: '#60A5FA', border: 'rgba(96,165,250,0.3)' },
};

export default function StatusBadge({ status, size = 'default' }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING;
  const padding = size === 'sm' ? '2px 8px' : '3px 10px';
  const fontSize = size === 'sm' ? '0.65rem' : '0.7rem';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      padding, borderRadius: '9999px', fontSize, fontWeight: 600,
      textTransform: 'uppercase', letterSpacing: '0.04em',
      background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`,
    }}>
      {status?.replace(/_/g, ' ')}
    </span>
  );
}
