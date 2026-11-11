import { useState, useEffect } from 'react';
import { Shield, RefreshCw, AlertTriangle, Building2 } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';
import { useOrg } from '../context/OrgContext';
import { enterprise } from '../services/enterprise';

const CATEGORY_COLORS = {
  security: { bg: 'rgba(0,255,170,0.08)', color: 'var(--accent-cyan)', border: 'rgba(0,255,170,0.2)' },
  regulatory: { bg: 'rgba(0,212,255,0.08)', color: 'var(--accent-blue)', border: 'rgba(0,212,255,0.2)' },
  industry: { bg: 'rgba(170,102,255,0.08)', color: 'var(--accent-purple)', border: 'rgba(170,102,255,0.2)' },
  privacy: { bg: 'rgba(255,136,0,0.08)', color: 'var(--accent-orange)', border: 'rgba(255,136,0,0.2)' },
};

export default function Compliance() {
  const { currentOrg } = useOrg();
  const [frameworks, setFrameworks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!currentOrg?.id) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    enterprise.compliance(currentOrg.id)
      .then((data) => {
        if (!cancelled) setFrameworks(data?.frameworks || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [currentOrg?.id, reloadKey]);

  if (loading) return <div className="page-content"><SkeletonTable rows={5} cols={4} /></div>;

  const getScoreColor = (score) => {
    if (score >= 80) return 'var(--accent-green)';
    if (score >= 60) return 'var(--accent-yellow)';
    if (score >= 40) return 'var(--accent-orange)';
    return 'var(--accent-red)';
  };

  const header = (
    <div className="dash-hero">
      <div>
        <h1 className="dash-hero-title">Compliance Center</h1>
        <p className="dash-hero-sub">Track compliance across security frameworks and standards</p>
      </div>
      <button className="btn-outline btn-sm" onClick={() => setReloadKey((k) => k + 1)} disabled={!currentOrg?.id}>
        <RefreshCw size={14} /> Refresh
      </button>
    </div>
  );

  if (!currentOrg?.id) {
    return (
      <div className="page-content">
        {header}
        <div className="empty-state" style={{ marginTop: 20 }}>
          <div className="empty-state-icon"><Building2 size={24} /></div>
          <div className="empty-state-title">No Organization Selected</div>
          <div className="empty-state-desc">Compliance data is scoped to an organization. Create or select one to continue.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {header}

      {error && (
        <div className="error-banner" style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {!error && frameworks.length === 0 && (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <div className="empty-state-icon"><Shield size={24} /></div>
          <div className="empty-state-title">No Compliance Frameworks</div>
          <div className="empty-state-desc">Run a scan in {currentOrg.name} to start mapping findings to frameworks such as OWASP ASVS, ISO 27001 and SOC 2.</div>
        </div>
      )}

      {frameworks.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16, marginTop: 20 }}>
          {frameworks.map((fw) => {
            const cat = CATEGORY_COLORS[fw.category] || CATEGORY_COLORS.security;
            return (
              <div key={fw.id || fw.slug} style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: 24,
                position: 'relative',
                overflow: 'hidden',
                transition: 'all 0.2s ease',
              }}>
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: cat.color, opacity: 0.4 }} />
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 8, background: cat.bg, border: `1px solid ${cat.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: cat.color }}>
                      <Shield size={16} />
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{fw.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>v{fw.version || '1.0'}</div>
                    </div>
                  </div>
                  <div style={{ width: 48, height: 48, borderRadius: '50%', border: `3px solid ${getScoreColor(fw.score ?? 0)}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: 14, fontWeight: 800, color: getScoreColor(fw.score ?? 0), fontFamily: 'var(--font-mono)' }}>{Math.round(fw.score ?? 0)}</span>
                  </div>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.5 }}>{fw.description}</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {fw.controls_count ?? 0} controls
                  </span>
                  <span style={{
                    padding: '2px 8px', borderRadius: 4, fontSize: 9, fontWeight: 700,
                    letterSpacing: '0.5px', textTransform: 'uppercase', fontFamily: 'var(--font-mono)',
                    background: cat.bg, color: cat.color, border: `1px solid ${cat.border}`,
                  }}>
                    {fw.category}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
