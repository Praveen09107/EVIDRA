# PLAN 19 — Frontend Shared Components
**Owner:** Dev B | **Hour:** 21:00–22:00 | **Priority:** MEDIUM

---

## 1. Objective
Extract reusable components to keep the main page files clean.

---

## 2. MetricCard

**File: `frontend/components/shared/MetricCard.js`**

```jsx
export default function MetricCard({ label, value, color = 'var(--accent-cyan)' }) {
  return (
    <div className="card-glass" style={{padding:24, textAlign:'center'}}>
      <p style={{fontSize:'2.5rem', fontWeight:700, color, lineHeight:1}}>{value}</p>
      <p style={{color:'var(--text-faint)', fontSize:'0.85rem', marginTop:8, textTransform:'uppercase', letterSpacing:1}}>{label}</p>
    </div>
  );
}
```

---

## 3. StatusBadge

**File: `frontend/components/shared/StatusBadge.js`**

```jsx
const STATUS_COLORS = {
  OPEN:        { bg: 'rgba(34,199,213,0.15)',  color: 'var(--accent-cyan)' },
  IN_ANALYSIS: { bg: 'rgba(251,191,36,0.15)',  color: 'var(--warning-amber)' },
  REVIEW:      { bg: 'rgba(56,189,248,0.15)',  color: 'var(--accent-blue)' },
  CLOSED:      { bg: 'rgba(107,114,128,0.15)', color: 'var(--text-faint)' },
  RUNNING:     { bg: 'rgba(34,199,213,0.15)',  color: 'var(--accent-cyan)' },
  COMPLETE:    { bg: 'rgba(34,197,94,0.15)',   color: 'var(--success-green)' },
  FAILED:      { bg: 'rgba(249,115,115,0.15)', color: 'var(--anomaly-red)' },
  PENDING:     { bg: 'rgba(107,114,128,0.15)', color: 'var(--text-faint)' },
};

export default function StatusBadge({ status }) {
  const s = STATUS_COLORS[status] || STATUS_COLORS.PENDING;
  return (
    <span style={{
      background: s.bg, color: s.color, padding: '4px 12px', 
      borderRadius: 12, fontSize: '0.75rem', fontWeight: 600,
      border: `1px solid ${s.color}40`
    }}>
      {status}
    </span>
  );
}
```

---

## 4. AgentPill

**File: `frontend/components/agents/AgentPill.js`**

```jsx
export default function AgentPill({ agentId, status }) {
  const isRunning = status === 'RUNNING';
  const isComplete = status === 'COMPLETE';
  const isFailed = status === 'FAILED';
  
  let color = 'var(--text-faint)';
  if (isRunning) color = 'var(--accent-cyan)';
  if (isComplete) color = 'var(--success-green)';
  if (isFailed) color = 'var(--anomaly-red)';

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '6px 12px', borderRadius: 16,
      border: `1px solid ${color}40`,
      background: `rgba(17,24,39,0.8)`,
      fontSize: '0.75rem', fontWeight: 500, color
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%', background: color,
        animation: isRunning ? 'pulse 1.5s infinite' : 'none'
      }} />
      {agentId.replace(/_/g, ' ')}
    </span>
  );
}
```
