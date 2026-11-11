import { useState, useEffect } from 'react';
import { Calendar, Clock, Zap, RefreshCw, AlertTriangle, Building2 } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';
import { useOrg } from '../context/OrgContext';
import { enterprise } from '../services/enterprise';

export default function ScheduledScans() {
  const { currentOrg } = useOrg();
  const [scans, setScans] = useState([]);
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
    enterprise.scheduledScans(currentOrg.id)
      .then((data) => {
        if (!cancelled) setScans(data?.items || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [currentOrg?.id, reloadKey]);

  if (loading) return <div className="page-content"><SkeletonTable rows={4} cols={5} /></div>;

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Scheduled Scans</h1>
          <p className="dash-hero-sub">Automate recurring security scans on a schedule</p>
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
          <div className="empty-state-desc">Scheduled scans belong to an organization. Create or select one to continue.</div>
        </div>
      )}

      {!error && currentOrg?.id && scans.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon"><Calendar size={24} /></div>
          <div className="empty-state-title">No Scheduled Scans</div>
          <div className="empty-state-desc">Recurring scans appear here once a schedule is configured for {currentOrg.name}. Scheduling is managed through the API (<code>POST /orgs/{currentOrg.id}/scheduled-scans</code>).</div>
        </div>
      )}

      {!error && scans.length > 0 && (
        <div className="dash-panel" style={{ marginTop: 20 }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SCHEDULED SCANS</span>
          </div>
          <div>
            {scans.map((scan) => (
              <div key={scan.id} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: 'rgba(0,255,170,0.08)', border: '1px solid rgba(0,255,170,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-cyan)', flexShrink: 0 }}>
                    <Calendar size={16} />
                  </div>
                  <div>
                    <div className="dash-scan-name">{scan.name}</div>
                    <div className="dash-scan-meta">
                      <span><Clock size={11} /> {scan.frequency}</span>
                      <span><Zap size={11} /> {scan.scan_type}</span>
                      <span>Run {scan.run_count}x</span>
                      {scan.failure_count > 0 && <span style={{ color: 'var(--accent-red)' }}>{scan.failure_count} failed</span>}
                    </div>
                  </div>
                </div>
                <div className="dash-scan-right">
                  <span className={`sev-badge ${scan.is_active ? 'low' : 'info'}`}>
                    {scan.is_active ? 'Active' : 'Paused'}
                  </span>
                  {scan.next_run_at && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Next: {new Date(scan.next_run_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
