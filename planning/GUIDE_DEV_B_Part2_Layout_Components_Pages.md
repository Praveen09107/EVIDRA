# DEV B EXECUTION GUIDE — PART 2: Layout Shell, Shared Components & Core Pages
**Owner:** Dev B | **Hours:** 2:00–6:00 | **Priority:** CRITICAL

---

## 1. PHASE 4 — LAYOUT SHELL (Hour 2:00–3:00)

### Step 1.1 — Root Layout (Final Version)

**File: `frontend/app/layout.js`**

```jsx
import './globals.css';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';

export const metadata = {
  title: 'AIVENTRA — Forensic Intelligence Platform',
  description: 'AI-powered multi-agent forensic triage and analysis system',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            <TopHeader />
            <div className="scroll-area">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
```

**Design decisions:**
- The `<Sidebar>` and `<TopHeader>` are rendered on EVERY page except login (the Sidebar component itself hides when `pathname === '/login'`).
- The `scroll-area` div is the ONLY scrollable container. The sidebar and topbar are fixed.
- We use the HTML `<head>` inside `layout.js` for Google Fonts because Next.js 14 App Router supports this pattern.

### Step 1.2 — Sidebar Navigation

**File: `frontend/components/layout/Sidebar.js`**

```jsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/cases',    label: 'Cases',            icon: '📁' },
  { href: '/command',  label: 'Command Center',   icon: '🎯' },
  { href: '/agents',   label: 'Agent Directory',  icon: '🤖' },
  { href: '/xai',      label: 'XAI Studio',       icon: '🧠' },
  { href: '/reports',  label: 'Reports',          icon: '📄' },
  { href: '/audit',    label: 'Audit Log',        icon: '🔒' },
];

export default function Sidebar() {
  const pathname = usePathname();

  // Hide sidebar on login page (login is full-screen)
  if (pathname === '/login') return null;

  return (
    <aside className="sidebar">
      {/* ── Brand ── */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.6rem',
          fontWeight: 800,
          background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          letterSpacing: '-0.5px',
        }}>
          AIVENTRA
        </h1>
        <p style={{
          fontSize: '0.65rem',
          color: 'var(--text-faint)',
          letterSpacing: '2px',
          textTransform: 'uppercase',
          marginTop: '4px',
        }}>
          Forensic Intelligence
        </p>
      </div>

      {/* ── Navigation ── */}
      <nav style={{
        padding: '16px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        flex: 1,
      }}>
        {NAV_ITEMS.map(item => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <Link key={item.href} href={item.href} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '10px 16px',
              borderRadius: '8px',
              fontSize: '0.88rem',
              fontWeight: isActive ? 600 : 400,
              color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
              background: isActive ? 'rgba(34, 199, 213, 0.08)' : 'transparent',
              borderLeft: isActive ? '3px solid var(--accent-cyan)' : '3px solid transparent',
              transition: 'all 0.15s ease',
              textDecoration: 'none',
            }}>
              <span style={{ fontSize: '1rem' }}>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* ── Footer ── */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '0.7rem',
        color: 'var(--text-faint)',
      }}>
        AIVENTRA v1.0.0 · Demo
      </div>
    </aside>
  );
}
```

**Why `'use client'`?** Because we use `usePathname()` which is a React hook that requires client-side rendering. Without this directive, Next.js treats the file as a Server Component and throws an error.

### Step 1.3 — Top Header Bar

**File: `frontend/components/layout/TopHeader.js`**

```jsx
'use client';
import { usePathname, useRouter } from 'next/navigation';

const PAGE_TITLES = {
  '/cases': 'Cases',
  '/command': 'Command Center',
  '/agents': 'Agent Directory',
  '/xai': 'XAI & Uncertainty Studio',
  '/reports': 'Report Builder',
  '/audit': 'Audit & Chain of Custody',
};

export default function TopHeader() {
  const pathname = usePathname();
  const router = useRouter();

  // Hide on login page
  if (pathname === '/login') return null;

  // Derive page title
  let title = PAGE_TITLES[pathname];
  if (!title && pathname.includes('/cases/')) title = 'Case Workspace';
  if (!title && pathname.includes('/agents/')) title = 'Agent Lab';
  if (!title && pathname.includes('/pipeline/')) title = 'Pipeline Explorer';
  if (!title) title = 'AIVENTRA';

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    router.push('/login');
  };

  const currentDate = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  return (
    <div className="topbar">
      <div style={{ flex: 1 }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>{title}</h2>
        <span style={{ color: 'var(--text-faint)', fontSize: '0.75rem' }}>
          {currentDate}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <span style={{
          color: 'var(--text-muted)',
          fontSize: '0.8rem',
          padding: '4px 10px',
          background: 'var(--bg-dark)',
          borderRadius: '6px',
        }}>
          {typeof window !== 'undefined' ? localStorage.getItem('role') || 'INVESTIGATOR' : ''}
        </span>
        <button className="btn btn-secondary" onClick={handleLogout}
                style={{ fontSize: '0.78rem', padding: '5px 14px' }}>
          Logout
        </button>
      </div>
    </div>
  );
}
```

### Step 1.4 — Root Page Redirect

**File: `frontend/app/page.js`**

```jsx
import { redirect } from 'next/navigation';
export default function Home() {
  redirect('/cases');
}
```

---

## 2. PHASE 5 — SHARED COMPONENTS (Hour 3:00–4:00)

These components are used across multiple pages. Build them FIRST so every page can import them.

### Step 2.1 — MetricCard

**File: `frontend/components/shared/MetricCard.js`**

```jsx
export default function MetricCard({ label, value, color = 'var(--accent-cyan)', subtitle, icon }) {
  return (
    <div className="card-glass" style={{ padding: '24px 16px', textAlign: 'center' }}>
      {icon && <span style={{ fontSize: '1.5rem', display: 'block', marginBottom: '6px' }}>{icon}</span>}
      <p style={{
        fontSize: '2.5rem',
        fontWeight: 700,
        color,
        lineHeight: 1,
        fontFamily: 'var(--font-display)',
      }}>
        {value}
      </p>
      <p style={{
        color: 'var(--text-faint)',
        fontSize: '0.78rem',
        marginTop: '10px',
        textTransform: 'uppercase',
        letterSpacing: '1px',
      }}>
        {label}
      </p>
      {subtitle && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginTop: '4px' }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}
```

### Step 2.2 — StatusBadge

**File: `frontend/components/shared/StatusBadge.js`**

```jsx
const STATUS_MAP = {
  OPEN:        { bg: 'rgba(34,199,213,0.12)',  color: '#22C7D5', border: 'rgba(34,199,213,0.3)' },
  IN_ANALYSIS: { bg: 'rgba(251,191,36,0.12)',  color: '#FBBF24', border: 'rgba(251,191,36,0.3)' },
  REVIEW:      { bg: 'rgba(56,189,248,0.12)',  color: '#38BDF8', border: 'rgba(56,189,248,0.3)' },
  CLOSED:      { bg: 'rgba(107,114,128,0.12)', color: '#6B7280', border: 'rgba(107,114,128,0.3)' },
  RUNNING:     { bg: 'rgba(34,199,213,0.12)',  color: '#22C7D5', border: 'rgba(34,199,213,0.3)' },
  COMPLETE:    { bg: 'rgba(34,197,94,0.12)',   color: '#22C55E', border: 'rgba(34,197,94,0.3)' },
  FAILED:      { bg: 'rgba(249,115,115,0.12)', color: '#F97373', border: 'rgba(249,115,115,0.3)' },
  PENDING:     { bg: 'rgba(107,114,128,0.08)', color: '#6B7280', border: 'rgba(107,114,128,0.2)' },
  DISPATCHED:  { bg: 'rgba(251,191,36,0.08)',  color: '#FBBF24', border: 'rgba(251,191,36,0.2)' },
  SKIPPED:     { bg: 'rgba(107,114,128,0.08)', color: '#4B5563', border: 'rgba(107,114,128,0.2)' },
};

export default function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || STATUS_MAP.PENDING;
  return (
    <span className="badge" style={{
      background: s.bg,
      color: s.color,
      border: `1px solid ${s.border}`,
    }}>
      {status === 'RUNNING' && <span style={{
        display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
        background: s.color, marginRight: 6, animation: 'pulse 1.5s infinite',
      }} />}
      {status}
    </span>
  );
}
```

### Step 2.3 — ConfidencePill

**File: `frontend/components/shared/ConfidencePill.js`**

```jsx
export default function ConfidencePill({ value, label }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 80 ? 'var(--success-green)' :
                pct >= 60 ? 'var(--warning-amber)' : 'var(--anomaly-red)';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '6px',
      padding: '4px 12px', borderRadius: '20px',
      background: `${color}15`, fontSize: '0.8rem',
    }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
      <span style={{ color, fontWeight: 600 }}>{pct}%</span>
      {label && <span style={{ color: 'var(--text-muted)' }}>{label}</span>}
    </span>
  );
}
```

### Step 2.4 — LoadingSpinner

**File: `frontend/components/shared/LoadingSpinner.js`**

```jsx
export default function LoadingSpinner({ size = 24, text }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: 'center', padding: '40px' }}>
      <div style={{
        width: size, height: size,
        border: '2px solid var(--border-subtle)',
        borderTopColor: 'var(--accent-cyan)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      {text && <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{text}</span>}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
```

### Step 2.5 — AgentPill

**File: `frontend/components/agents/AgentPill.js`**

```jsx
const AGENT_COLORS = {
  evidence_parser: '#6B7280', ocr: '#6B7280', format_normalizer: '#6B7280',
  autopsy_agent: '#A78BFA', cdr_analyzer: '#22C55E', financial_analyzer: '#22C55E',
  image_agent: '#38BDF8', tod_agent: '#FBBF24', timeline_anomaly: '#38BDF8',
  collision_agent: '#22C55E', hotspot_engine: '#F97373', claim_extractor: '#A78BFA',
  evidence_claim_mapper: '#A78BFA', hypothesis_manager: '#22C7D5',
  bias_uncertainty: '#F472B6', nbe_agent: '#FB923C', reasoning_replay: '#94A3B8',
};

export default function AgentPill({ agentId, status }) {
  const baseColor = AGENT_COLORS[agentId] || '#6B7280';
  const isRunning = status === 'RUNNING';
  const isComplete = status === 'COMPLETE';
  const isFailed = status === 'FAILED';

  let dotColor = baseColor;
  if (isRunning) dotColor = 'var(--accent-cyan)';
  if (isComplete) dotColor = 'var(--success-green)';
  if (isFailed) dotColor = 'var(--anomaly-red)';

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '6px',
      padding: '5px 12px', borderRadius: '16px',
      border: `1px solid ${dotColor}40`,
      background: 'rgba(17,24,39,0.8)',
      fontSize: '0.73rem', fontWeight: 500,
      color: isComplete ? 'var(--success-green)' : isFailed ? 'var(--anomaly-red)' : 'var(--text-secondary)',
      transition: 'all 0.3s ease',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: dotColor,
        animation: isRunning ? 'pulse 1.5s infinite' : 'none',
        boxShadow: isRunning ? `0 0 8px ${dotColor}` : 'none',
      }} />
      {agentId.replace(/_/g, ' ')}
    </span>
  );
}
```

---

## 3. PHASE 6 — LOGIN PAGE (Hour 4:00–4:30)

**File: `frontend/app/login/page.js`**

```jsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('admin@aiventra.gov');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.login(email, password);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('role', res.role);
      router.push('/cases');
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 500,
      background: 'linear-gradient(135deg, #0A0F1A 0%, #111827 50%, #0A0F1A 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      {/* Background grid effect */}
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.03,
        backgroundImage: 'linear-gradient(var(--accent-cyan) 1px, transparent 1px), linear-gradient(90deg, var(--accent-cyan) 1px, transparent 1px)',
        backgroundSize: '60px 60px',
      }} />

      <div className="card-glass animate-in" style={{
        width: '420px', padding: '48px 40px', position: 'relative',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h1 style={{
            fontFamily: 'var(--font-display)', fontSize: '2.2rem', fontWeight: 800,
            background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            AIVENTRA
          </h1>
          <p style={{ color: 'var(--text-faint)', fontSize: '0.75rem', letterSpacing: '3px', marginTop: '8px' }}>
            FORENSIC INTELLIGENCE PLATFORM
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
              Email Address
            </label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                   placeholder="investigator@police.gov" required
                   style={{ width: '100%' }} />
          </div>
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
              Password
            </label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                   placeholder="••••••••" required
                   style={{ width: '100%' }} />
          </div>

          {error && (
            <div style={{
              padding: '10px 14px', borderRadius: '6px',
              background: 'rgba(249,115,115,0.1)', border: '1px solid rgba(249,115,115,0.3)',
              color: 'var(--anomaly-red)', fontSize: '0.85rem',
            }}>
              {error}
            </div>
          )}

          <button type="submit" className="btn btn-primary"
                  disabled={loading}
                  style={{ marginTop: '8px', padding: '12px', fontSize: '0.95rem', width: '100%' }}>
            {loading ? 'Authenticating...' : 'Secure Login →'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.75rem', color: 'var(--text-faint)' }}>
          Authorized Personnel Only · All Access Logged
        </p>
      </div>
    </div>
  );
}
```

**How to test:** Navigate to `http://localhost:3000/login`. If Dev A's backend is running, clicking login should redirect to `/cases`. If backend isn't up yet, you'll see the error message — that's expected.

---

## 4. PHASE 7 — CASE LOBBY (Hour 4:30–6:00)

**File: `frontend/app/cases/page.js`**

```jsx
'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import StatusBadge from '@/components/shared/StatusBadge';

// Mock data for when backend isn't ready
const MOCK_CASES = [
  { case_id: 'mock-1', case_number: 'CASE-2026-001', title: 'Kumar Death Investigation',
    status: 'IN_ANALYSIS', location: 'Bengaluru, KA', created_at: new Date().toISOString() },
  { case_id: 'mock-2', case_number: 'CASE-2026-002', title: 'Highway 44 Incident',
    status: 'OPEN', location: 'Chennai, TN', created_at: new Date().toISOString() },
];

export default function CasesLobby() {
  const [cases, setCases] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    api.getCases()
      .then(data => { setCases(data); setLoading(false); })
      .catch(() => { setCases(MOCK_CASES); setLoading(false); });
  }, []);

  return (
    <div className="animate-in">
      <div className="flex-between" style={{ marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 700 }}>
            Active Cases
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
            {cases.length} case{cases.length !== 1 ? 's' : ''} in system
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + New Case
        </button>
      </div>

      {cases.length === 0 && !loading ? (
        <div className="empty-state">
          <h3>No cases yet</h3>
          <p>Create your first forensic case to begin investigation</p>
        </div>
      ) : (
        <div className="grid-3">
          {cases.map(c => (
            <div key={c.case_id} className="card" style={{ cursor: 'pointer' }}
                 onClick={() => router.push(`/cases/${c.case_id}`)}>
              <div className="flex-between" style={{ marginBottom: '12px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-faint)',
                }}>
                  {c.case_number}
                </span>
                <StatusBadge status={c.status} />
              </div>
              <h3 style={{ fontSize: '1rem', marginBottom: '8px', fontWeight: 600 }}>
                {c.title}
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                📍 {c.location || 'Location not set'}
              </p>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-faint)', marginTop: '12px' }}>
                Created {new Date(c.created_at).toLocaleDateString('en-IN')}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Create Case Modal */}
      {showModal && (
        <CreateCaseModal
          onClose={() => setShowModal(false)}
          onCreated={() => {
            setShowModal(false);
            api.getCases().then(setCases).catch(() => {});
          }}
        />
      )}
    </div>
  );
}

function CreateCaseModal({ onClose, onCreated }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.createCase({ title, description, location });
      onCreated();
    } catch (err) {
      alert('Failed to create case: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card animate-in" style={{ width: '480px', padding: '32px' }}
           onClick={e => e.stopPropagation()}>
        <h2 style={{ fontFamily: 'var(--font-display)', marginBottom: '24px' }}>
          Create New Case
        </h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Case Title *
            </label>
            <input value={title} onChange={e => setTitle(e.target.value)}
                   placeholder="e.g., Kumar Death Investigation" required autoFocus
                   style={{ width: '100%' }} />
          </div>
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Description
            </label>
            <textarea value={description} onChange={e => setDescription(e.target.value)}
                      placeholder="Brief description of the case..."
                      rows={3} style={{
                        width: '100%', background: 'var(--bg-dark)',
                        border: '1px solid var(--border-subtle)', color: 'var(--text-primary)',
                        padding: '8px 12px', borderRadius: '6px', fontFamily: 'var(--font-sans)',
                        resize: 'vertical',
                      }} />
          </div>
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Location
            </label>
            <input value={location} onChange={e => setLocation(e.target.value)}
                   placeholder="e.g., 45/A MG Road, Bengaluru"
                   style={{ width: '100%' }} />
          </div>
          <div className="flex-between" style={{ marginTop: '8px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Case →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

---

## 5. ACCEPTANCE CRITERIA FOR PART 2

- [ ] App shows Sidebar with gradient AIVENTRA branding on all pages
- [ ] Sidebar nav highlights the active page with cyan left border
- [ ] TopHeader shows dynamic page title and current date
- [ ] Sidebar hides on `/login` (full-screen login experience)
- [ ] Login form displays error messages on failure, shows loading state
- [ ] Login stores JWT in `localStorage` and redirects to `/cases`
- [ ] Cases lobby renders in 3-column grid with status badges
- [ ] Create Case modal opens, submits, and refreshes the list
- [ ] Empty state shown when no cases exist
- [ ] Cards have hover lift effect (translateY -2px + shadow)
- [ ] Mock data renders correctly when backend is unavailable
