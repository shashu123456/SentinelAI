import { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, Building2, RefreshCw } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';
import { useOrg } from '../context/OrgContext';
import { enterprise } from '../services/enterprise';

export default function PolicyEngine() {
  const { currentOrg } = useOrg();
  const [policies, setPolicies] = useState([]);
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
    enterprise.policies(currentOrg.id)
      .then((data) => {
        if (!cancelled) setPolicies(data?.items || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [currentOrg?.id, reloadKey]);

  if (loading) return <div className="page-content"><SkeletonTable rows={3} cols={4} /></div>;

  const severityColors = {
    critical: 'var(--severity-critical)', high: 'var(--severity-high)',
    medium: 'var(--severity-medium)', low: 'var(--severity-low)',
  };

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Policy Engine</h1>
          <p className="dash-hero-sub">Define custom security policies and automated gates for your pipeline</p>
        </div>
        <button className="btn-outline btn-sm" onClick={() => setReloadKey((k) => k + 1)} disabled={!currentOrg?.id}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner" style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {!error && !currentOrg?.id && (
        <div className="empty-state">
          <div className="empty-state-icon"><Building2 size={24} /></div>
          <div className="empty-state-title">No Organization Selected</div>
          <div className="empty-state-desc">Policies are scoped to an organization.</div>
        </div>
      )}

      {!error && currentOrg?.id && policies.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><ShieldAlert size={24} /></div>
          <div className="empty-state-title">No Custom Policies</div>
          <div className="empty-state-desc">Create policies to automatically enforce security standards and gate deployments.</div>
        </div>
      ) : (
        <div className="dash-panel" style={{ marginTop: 20 }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SECURITY POLICIES</span>
          </div>
          <div>
            {policies.map(p => (
              <div key={p.id} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: 'rgba(255,51,85,0.08)', border: '1px solid rgba(255,51,85,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: severityColors[p.severity] || 'var(--accent-red)', flexShrink: 0 }}>
                    <ShieldAlert size={16} />
                  </div>
                  <div>
                    <div className="dash-scan-name">{p.name}</div>
                    <div className="dash-scan-meta">
                      <span style={{ textTransform: 'capitalize' }}>{p.policy_type.replace('_', ' ')}</span>
                      <span>Evaluated {p.evaluation_count}x</span>
                      {p.violation_count > 0 && <span style={{ color: 'var(--accent-red)' }}>{p.violation_count} violations</span>}
                    </div>
                  </div>
                </div>
                <div className="dash-scan-right">
                  {p.enforce_on_scans && (
                    <span className="sev-badge high">Enforcing</span>
                  )}
                  <span className={`sev-badge ${p.is_active ? 'low' : 'info'}`}>
                    {p.is_active ? 'Active' : 'Disabled'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
