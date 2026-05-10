'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, Mail, Lock, ArrowRight, Activity } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState('arjun.sharma@cbi.gov.in');
  const [password, setPassword] = useState('demo1234');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await api.login(email, password);
      login(result.access_token, { email, name: result.name || email.split('@')[0] }, result.role);
      router.push('/cases');
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      {/* Ambient glow effects */}
      <div style={styles.glowTop} />
      <div style={styles.glowBottom} />

      <div style={styles.container}>
        {/* Left column — Branding */}
        <div style={styles.leftCol}>
          <div style={styles.brandWrap}>
            <div style={styles.brandIcon}>
              <Activity size={28} color="var(--accent-cyan)" />
            </div>
            <h1 style={styles.brandTitle}>ForensIQ</h1>
            <p style={styles.brandTagline}>
              Multi-Agent Forensic Intelligence Platform
            </p>
            <div style={styles.featureList}>
              {[
                '17 Specialized AI Agents',
                'Bayesian Hypothesis Engine',
                'Court-Ready Reports with XAI',
                'Cryptographic Reasoning Chain',
              ].map((f, i) => (
                <div key={i} style={styles.featureItem}>
                  <div style={styles.featureDot} />
                  <span>{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right column — Login form */}
        <div style={styles.rightCol}>
          <div style={styles.formCard}>
            <div style={styles.formHeader}>
              <Shield size={24} color="var(--accent-cyan)" />
              <h2 style={styles.formTitle}>Secure Sign In</h2>
              <p style={styles.formSub}>
                Access restricted to authorized personnel only.
              </p>
            </div>

            <form onSubmit={handleSubmit} style={styles.form}>
              <div style={styles.inputGroup}>
                <label style={styles.label}>Official Email</label>
                <div style={styles.inputWrap}>
                  <Mail size={16} color="var(--text-faint)" style={{ flexShrink: 0 }} />
                  <input
                    type="email" value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@agency.gov.in"
                    style={styles.inputInner}
                    required
                  />
                </div>
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label}>Password</label>
                <div style={styles.inputWrap}>
                  <Lock size={16} color="var(--text-faint)" style={{ flexShrink: 0 }} />
                  <input
                    type="password" value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    style={styles.inputInner}
                    required
                  />
                </div>
              </div>

              {error && (
                <div style={styles.errorBox}>⚠ {error}</div>
              )}

              <button
                type="submit"
                className="btn btn-primary btn-lg"
                style={{ width: '100%', marginTop: '8px' }}
                disabled={loading}
              >
                {loading ? 'Authenticating...' : 'Sign In'}
                {!loading && <ArrowRight size={16} />}
              </button>
            </form>

            <div style={styles.secNote}>
              <Lock size={12} />
              <span>MFA required • All sessions audited • RBAC enforced</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'var(--bg-base)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 200, overflow: 'hidden',
  },
  glowTop: {
    position: 'absolute', top: '-30%', right: '-10%',
    width: '600px', height: '600px', borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(34,199,213,0.06) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  glowBottom: {
    position: 'absolute', bottom: '-20%', left: '-10%',
    width: '500px', height: '500px', borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(99,102,241,0.05) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  container: {
    display: 'flex', maxWidth: '900px', width: '100%',
    margin: '0 24px', gap: '48px', alignItems: 'center',
    position: 'relative', zIndex: 1,
  },
  leftCol: { flex: 1, display: 'flex', justifyContent: 'center' },
  brandWrap: { maxWidth: '340px' },
  brandIcon: {
    width: 52, height: 52, borderRadius: 14,
    background: 'rgba(34,199,213,0.1)', display: 'flex',
    alignItems: 'center', justifyContent: 'center', marginBottom: '20px',
  },
  brandTitle: {
    fontFamily: 'var(--font-display)', fontSize: '2.5rem',
    color: 'var(--text-primary)', marginBottom: '8px',
  },
  brandTagline: {
    fontSize: '0.95rem', color: 'var(--text-muted)',
    lineHeight: 1.6, marginBottom: '32px',
  },
  featureList: { display: 'flex', flexDirection: 'column', gap: '14px' },
  featureItem: {
    display: 'flex', alignItems: 'center', gap: '12px',
    fontSize: '0.85rem', color: 'var(--text-secondary)',
  },
  featureDot: {
    width: 6, height: 6, borderRadius: '50%',
    background: 'var(--accent-cyan)', flexShrink: 0,
  },
  rightCol: { flex: 1 },
  formCard: {
    background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
    borderRadius: '16px', padding: '36px', maxWidth: '400px',
  },
  formHeader: {
    textAlign: 'center', marginBottom: '28px',
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px',
  },
  formTitle: {
    fontSize: '1.25rem', fontWeight: 600,
    color: 'var(--text-primary)',
  },
  formSub: { fontSize: '0.8rem', color: 'var(--text-muted)' },
  form: { display: 'flex', flexDirection: 'column', gap: '18px' },
  inputGroup: { display: 'flex', flexDirection: 'column', gap: '6px' },
  label: {
    fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-muted)',
    textTransform: 'uppercase', letterSpacing: '0.04em',
  },
  inputWrap: {
    display: 'flex', alignItems: 'center', gap: '10px',
    background: 'var(--bg-base)', border: '1px solid var(--border-subtle)',
    borderRadius: '8px', padding: '10px 14px',
  },
  inputInner: {
    background: 'transparent', border: 'none', outline: 'none',
    color: 'var(--text-primary)', fontSize: '0.9rem', width: '100%',
    fontFamily: 'var(--font-body)',
  },
  errorBox: {
    background: 'var(--anomaly-red-muted)', color: 'var(--anomaly-red)',
    padding: '10px 14px', borderRadius: '8px', fontSize: '0.8rem',
    border: '1px solid rgba(249,115,115,0.2)',
  },
  secNote: {
    display: 'flex', alignItems: 'center', gap: '6px',
    justifyContent: 'center', marginTop: '20px',
    fontSize: '0.7rem', color: 'var(--text-faint)',
  },
};
