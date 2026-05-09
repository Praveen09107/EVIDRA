# PLAN 13 — Frontend Pages Core (Login & Lobby)
**Owner:** Dev B | **Hour:** 2:00–4:00 | **Priority:** CRITICAL

---

## 1. Objective
Implement the root layout (Sidebar), the Login/Registration page, and the Case Lobby (Case grid and creation modal).

---

## 2. Root Layout & Sidebar

**File: `frontend/app/layout.js`**

```jsx
import './globals.css';
import TopHeader from '@/components/layout/TopHeader';
import Sidebar from '@/components/layout/Sidebar';

export const metadata = { title: 'AIVENTRA' };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
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

**File: `frontend/components/layout/Sidebar.js`**

```jsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/cases', label: 'Cases' },
  { href: '/command', label: 'Command Center' },
  { href: '/agents', label: 'Agent Directory' },
  { href: '/xai', label: 'XAI Studio' },
  { href: '/reports', label: 'Reports' },
  { href: '/audit', label: 'Audit Log' },
];

export default function Sidebar() {
  const path = usePathname();
  if (path === '/login') return null; // Hide on login page
  
  return (
    <aside className="sidebar">
      <div style={{padding: '24px', borderBottom: '1px solid var(--border-subtle)'}}>
        <h1 style={{fontFamily: 'var(--font-display)', color: 'var(--accent-cyan)', fontSize: '1.5rem'}}>AIVENTRA</h1>
        <p style={{fontSize: '0.7rem', color: 'var(--text-faint)'}}>FORENSIC INTELLIGENCE</p>
      </div>
      <nav style={{padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px'}}>
        {NAV.map(item => {
          const active = path.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} 
                  style={{
                    padding: '10px 16px', 
                    borderRadius: '6px',
                    color: active ? '#fff' : 'var(--text-muted)',
                    background: active ? 'rgba(34, 199, 213, 0.1)' : 'transparent',
                    borderLeft: active ? '3px solid var(--accent-cyan)' : '3px solid transparent'
                  }}>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

---

## 3. Login Page

**File: `frontend/app/login/page.js`**

```jsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function Login() {
  const [email, setEmail] = useState('admin@aiventra.gov');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await api.login(email, password);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('role', res.role);
      router.push('/cases');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{display:'flex', height:'100vh', width:'100vw', alignItems:'center', justifyContent:'center', position:'fixed', top:0, left:0, background:'var(--bg-dark)', zIndex:100}}>
      <div className="card-glass animate-in" style={{width: 400, padding: 40}}>
        <h2 style={{fontFamily:'var(--font-display)', color:'var(--accent-cyan)', textAlign:'center', marginBottom:32}}>AIVENTRA</h2>
        <form onSubmit={handleLogin} style={{display:'flex', flexDirection:'column', gap:16}}>
          <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email" required />
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" required />
          {error && <p style={{color:'var(--anomaly-red)', fontSize:'0.85rem'}}>{error}</p>}
          <button type="submit" className="btn btn-primary" style={{marginTop:16}}>Secure Login</button>
        </form>
      </div>
    </div>
  );
}
```

---

## 4. Case Lobby

**File: `frontend/app/cases/page.js`**

```jsx
'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import StatusBadge from '@/components/shared/StatusBadge';

export default function CasesLobby() {
  const [cases, setCases] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const router = useRouter();

  useEffect(() => {
    api.getCases().then(setCases).catch(console.error);
  }, []);

  return (
    <div className="animate-in">
      <div className="flex-between" style={{marginBottom: 24}}>
        <h1 style={{fontFamily:'var(--font-display)', fontSize:'2rem'}}>Active Cases</h1>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ New Case</button>
      </div>

      <div className="grid-3">
        {cases.map(c => (
          <div key={c.case_id} className="card" style={{cursor:'pointer'}} onClick={() => router.push(`/cases/${c.case_id}`)}>
            <div className="flex-between" style={{marginBottom: 12}}>
              <span style={{fontFamily:'var(--font-mono)', fontSize:'0.85rem', color:'var(--text-faint)'}}>{c.case_number}</span>
              <StatusBadge status={c.status} />
            </div>
            <h3 style={{marginBottom: 8}}>{c.title}</h3>
            <p style={{fontSize:'0.85rem', color:'var(--text-muted)'}}>{c.location}</p>
          </div>
        ))}
      </div>

      {showModal && <CreateCaseModal onClose={() => setShowModal(false)} onCreated={(c) => { setCases([c,...cases]); setShowModal(false); }} />}
    </div>
  );
}

function CreateCaseModal({ onClose, onCreated }) {
  const [title, setTitle] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    await api.createCase({ title, description: '', location: '' });
    window.location.reload(); // Simple refresh for MVP
  };
  return (
    <div style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.8)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:50}}>
      <div className="card" style={{width: 400}}>
        <h3 style={{marginBottom:20}}>Create New Case</h3>
        <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:16}}>
          <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Case Title" autoFocus required />
          <div className="flex-between">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

## Acceptance Criteria
- [ ] Next.js app renders layout with Sidebar.
- [ ] Login page successfully receives JWT and redirects to `/cases`.
- [ ] `/cases` lists grid of cases fetched from DB.
- [ ] Create case modal successfully posts to backend.
