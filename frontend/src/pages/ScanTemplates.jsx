import { useState, useEffect } from 'react';
import { FileText, Plus, Settings, Copy, Trash2, Star } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';

const API = '/api';

export default function ScanTemplates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadTemplates(); }, []);

  const loadTemplates = async () => {
    try {
      const res = await fetch(`${API}/orgs/1/templates`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      setTemplates(data.items || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  if (loading) return <div className="page-content"><SkeletonTable rows={3} cols={4} /></div>;

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Scan Templates</h1>
          <p className="dash-hero-sub">Reusable scan configurations for consistent security analysis</p>
        </div>
        <button className="btn-primary"><Plus size={14} /> New Template</button>
      </div>

      {templates.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><FileText size={24} /></div>
          <div className="empty-state-title">No Scan Templates</div>
          <div className="empty-state-desc">Create templates to standardize scan configurations across your organization.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16, marginTop: 20 }}>
          {templates.map(t => (
            <div key={t.id} style={{
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)', padding: 20, transition: 'all 0.2s ease',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-blue)' }}>
                    <Settings size={14} />
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{t.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>{t.scan_type}</div>
                  </div>
                </div>
                {t.is_default && <Star size={14} style={{ color: 'var(--accent-yellow)' }} />}
              </div>
              {t.description && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>{t.description}</p>}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Used {t.use_count} times</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t.compliance_frameworks?.length || 0} frameworks</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
