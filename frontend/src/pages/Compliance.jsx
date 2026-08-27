import { useState, useEffect } from 'react';
import { Shield, CheckCircle, XCircle, AlertTriangle, ExternalLink, ChevronRight, RefreshCw } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';

const API = '/api';

const CATEGORY_COLORS = {
  security: { bg: 'rgba(0,255,170,0.08)', color: 'var(--accent-cyan)', border: 'rgba(0,255,170,0.2)' },
  regulatory: { bg: 'rgba(0,212,255,0.08)', color: 'var(--accent-blue)', border: 'rgba(0,212,255,0.2)' },
  industry: { bg: 'rgba(170,102,255,0.08)', color: 'var(--accent-purple)', border: 'rgba(170,102,255,0.2)' },
  privacy: { bg: 'rgba(255,136,0,0.08)', color: 'var(--accent-orange)', border: 'rgba(255,136,0,0.2)' },
};

export default function Compliance() {
  const [frameworks, setFrameworks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadFrameworks(); }, []);

  const loadFrameworks = async () => {
    try {
      const res = await fetch(`${API}/orgs/1/compliance`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      setFrameworks(data.frameworks || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  if (loading) return <div className="page-content"><SkeletonTable rows={5} cols={4} /></div>;

  const getScoreColor = (score) => {
    if (score >= 80) return 'var(--accent-green)';
    if (score >= 60) return 'var(--accent-yellow)';
    if (score >= 40) return 'var(--accent-orange)';
    return 'var(--accent-red)';
  };

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Compliance Center</h1>
          <p className="dash-hero-sub">Track compliance across security frameworks and standards</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16, marginTop: 20 }}>
        {frameworks.map(fw => {
          const cat = CATEGORY_COLORS[fw.category] || CATEGORY_COLORS.security;
          return (
            <div key={fw.id} style={{
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
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>v{fw.version}</div>
                  </div>
                </div>
                <div style={{ width: 48, height: 48, borderRadius: '50%', border: `3px solid ${getScoreColor(fw.score)}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span style={{ fontSize: 14, fontWeight: 800, color: getScoreColor(fw.score), fontFamily: 'var(--font-mono)' }}>{Math.round(fw.score)}</span>
                </div>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.5 }}>{fw.description}</p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {fw.controls_count} controls
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
    </div>
  );
}
