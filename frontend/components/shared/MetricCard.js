'use client';
export default function MetricCard({ label, value, sub, color = 'var(--accent-cyan)', icon: Icon }) {
  return (
    <div className="card" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
            {label}
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color, fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
            {value}
          </div>
          {sub && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>{sub}</div>}
        </div>
        {Icon && (
          <div style={{ width: 40, height: 40, borderRadius: 10, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon size={20} color={color} />
          </div>
        )}
      </div>
    </div>
  );
}
