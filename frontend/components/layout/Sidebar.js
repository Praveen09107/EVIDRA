'use client';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  LayoutDashboard, FolderOpen, Terminal, Bot,
  GitBranch, Brain, FileText, Shield
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/cases', label: 'Cases', icon: FolderOpen },
  { href: '/command', label: 'Command Center', icon: Terminal },
  { href: '/agents', label: 'Agent Directory', icon: Bot },
  { href: '/pipeline', label: 'Pipeline Explorer', icon: GitBranch },
  { href: '/xai', label: 'XAI Studio', icon: Brain },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/audit', label: 'Audit Trail', icon: Shield },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar" style={styles.sidebar}>
      {/* Brand */}
      <div style={styles.brand}>
        <div style={styles.logoIcon}>
          <LayoutDashboard size={20} color="var(--accent-cyan)" />
        </div>
        <div>
          <div style={styles.logoText}>AIVENTRA</div>
          <div style={styles.logoSub}>Forensic Intelligence</div>
        </div>
      </div>

      {/* Divider */}
      <div style={styles.divider} />

      {/* Navigation */}
      <nav style={styles.nav}>
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link key={href} href={href} style={{
              ...styles.navItem,
              ...(isActive ? styles.navItemActive : {}),
            }}>
              {isActive && <div style={styles.activeIndicator} />}
              <Icon size={18} style={{ opacity: isActive ? 1 : 0.5 }} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.footerDot} />
        <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)' }}>
          System Online
        </span>
      </div>
    </aside>
  );
}

const styles = {
  sidebar: {
    display: 'flex', flexDirection: 'column', padding: '0',
  },
  brand: {
    display: 'flex', alignItems: 'center', gap: '12px',
    padding: '20px 20px 16px',
  },
  logoIcon: {
    width: 36, height: 36, borderRadius: 8,
    background: 'rgba(34,199,213,0.1)', display: 'flex',
    alignItems: 'center', justifyContent: 'center',
  },
  logoText: {
    fontFamily: 'var(--font-display)', fontSize: '1.25rem',
    color: 'var(--text-primary)', lineHeight: 1.1,
  },
  logoSub: {
    fontSize: '0.65rem', color: 'var(--text-faint)',
    textTransform: 'uppercase', letterSpacing: '0.08em',
  },
  divider: {
    height: 1, background: 'var(--border-subtle)',
    margin: '0 16px 8px',
  },
  nav: {
    flex: 1, display: 'flex', flexDirection: 'column',
    gap: '2px', padding: '0 8px',
  },
  navItem: {
    display: 'flex', alignItems: 'center', gap: '12px',
    padding: '10px 12px', borderRadius: '8px',
    color: 'var(--text-muted)', fontSize: '0.85rem',
    textDecoration: 'none', position: 'relative',
    transition: 'all 150ms ease',
  },
  navItemActive: {
    color: 'var(--text-primary)',
    background: 'rgba(34, 199, 213, 0.08)',
  },
  activeIndicator: {
    position: 'absolute', left: 0, top: '50%',
    transform: 'translateY(-50%)',
    width: 3, height: 20, borderRadius: 2,
    background: 'var(--accent-cyan)',
  },
  footer: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '16px 20px', borderTop: '1px solid var(--border-subtle)',
    marginTop: 'auto',
  },
  footerDot: {
    width: 8, height: 8, borderRadius: '50%',
    background: 'var(--success-green)',
    boxShadow: '0 0 6px rgba(34,197,94,0.4)',
  },
};
