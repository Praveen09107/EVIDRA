'use client';
import { Search, Bell, User } from 'lucide-react';
import { useAuthStore } from '@/lib/store';

export default function TopHeader({ title = 'Dashboard' }) {
  const user = useAuthStore((s) => s.user);
  return (
    <header className="topbar">
      <h1 style={{
        fontFamily: 'var(--font-display)', fontSize: '1.3rem',
        color: 'var(--text-primary)', fontWeight: 400,
      }}>
        {title}
      </h1>

      <div style={{ flex: 1 }} />

      {/* Search */}
      <div style={styles.searchBox}>
        <Search size={14} color="var(--text-faint)" />
        <input
          placeholder="Search cases, agents..."
          style={styles.searchInput}
        />
        <kbd style={styles.kbd}>⌘K</kbd>
      </div>

      {/* Notifications */}
      <button style={styles.iconBtn}>
        <Bell size={18} />
        <span style={styles.notifDot} />
      </button>

      {/* User */}
      <div style={styles.userPill}>
        <div style={styles.avatar}>
          <User size={14} />
        </div>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          {user?.name ? `${user.name.split(' ')[0]} ${user.name.split(' ').pop()?.[0] || ''}.` : 'User'}
        </span>
      </div>
    </header>
  );
}

const styles = {
  searchBox: {
    display: 'flex', alignItems: 'center', gap: '8px',
    background: 'var(--bg-base)', border: '1px solid var(--border-subtle)',
    borderRadius: '8px', padding: '6px 12px', maxWidth: '320px', width: '100%',
  },
  searchInput: {
    background: 'transparent', border: 'none', outline: 'none',
    color: 'var(--text-primary)', fontSize: '0.8rem',
    width: '100%', padding: 0,
  },
  kbd: {
    fontSize: '0.65rem', padding: '2px 6px', borderRadius: '4px',
    background: 'rgba(255,255,255,0.06)', color: 'var(--text-faint)',
    border: '1px solid var(--border-subtle)', fontFamily: 'var(--font-mono)',
  },
  iconBtn: {
    background: 'transparent', border: 'none', color: 'var(--text-muted)',
    padding: '8px', borderRadius: '8px', position: 'relative',
    cursor: 'pointer', display: 'flex', alignItems: 'center',
  },
  notifDot: {
    position: 'absolute', top: 6, right: 6, width: 6, height: 6,
    borderRadius: '50%', background: 'var(--anomaly-red)',
  },
  userPill: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '6px 12px 6px 6px', borderRadius: '20px',
    border: '1px solid var(--border-subtle)',
  },
  avatar: {
    width: 28, height: 28, borderRadius: '50%',
    background: 'var(--accent-cyan)', color: '#000',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
};
