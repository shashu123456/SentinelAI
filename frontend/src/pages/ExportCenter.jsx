import { useState, useEffect } from 'react';
import { Download, FileText, FileJson, File, Shield, Clock, CheckCircle, AlertTriangle, Loader, RefreshCw, Building2 } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';
import { useOrg } from '../context/OrgContext';
import { enterprise } from '../services/enterprise';

const FORMAT_INFO = {
  pdf: { icon: FileText, color: 'var(--accent-red)', label: 'PDF Report' },
  csv: { icon: File, color: 'var(--accent-green)', label: 'CSV Export' },
  json: { icon: FileJson, color: 'var(--accent-blue)', label: 'JSON Data' },
  sarif: { icon: Shield, color: 'var(--accent-purple)', label: 'SARIF Format' },
};
const STATUS_ICONS = {
  pending: Loader, processing: Loader, completed: CheckCircle, failed: AlertTriangle,
};
const STATUS_COLORS = {
  pending: 'info', processing: 'medium', completed: 'low', failed: 'critical',
};

export default function ExportCenter() {
  const { currentOrg } = useOrg();
  const [exports, setExports] = useState([]);
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
    enterprise.exports(currentOrg.id)
      .then((data) => {
        if (!cancelled) setExports(data?.items || []);
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

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Export Center</h1>
          <p className="dash-hero-sub">Export scan results and reports in multiple formats</p>
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

      {!currentOrg?.id && !error && (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <div className="empty-state-icon"><Building2 size={24} /></div>
          <div className="empty-state-title">No Organization Selected</div>
          <div className="empty-state-desc">Exports are scoped to an organization. Create or select one to continue.</div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginTop: 20 }}>
        {Object.entries(FORMAT_INFO).map(([fmt, info]) => {
          const Icon = info.icon;
          return (
            <div key={fmt} style={{
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)', padding: 20, textAlign: 'center',
            }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: `${info.color}11`, border: `1px solid ${info.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: info.color, margin: '0 auto 10px' }}>
                <Icon size={18} />
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{info.label}</div>
            </div>
          );
        })}
      </div>

      {!error && currentOrg?.id && exports.length === 0 && (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <div className="empty-state-icon"><Download size={24} /></div>
          <div className="empty-state-title">No Exports Yet</div>
          <div className="empty-state-desc">Generated exports for {currentOrg.name} will be listed here with their format and status.</div>
        </div>
      )}

      {!error && exports.length > 0 && (
        <div className="dash-panel" style={{ marginTop: 20 }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">RECENT EXPORTS</span>
          </div>
          <div>
            {exports.map((exp) => {
              const fmt = FORMAT_INFO[exp.format] || FORMAT_INFO.json;
              const Icon = fmt.icon;
              const StatusIcon = STATUS_ICONS[exp.status] || Clock;
              return (
                <div key={exp.id} className="dash-scan-item">
                  <div className="dash-scan-left">
                    <div style={{ width: 36, height: 36, borderRadius: 8, background: `${fmt.color}11`, border: `1px solid ${fmt.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: fmt.color, flexShrink: 0 }}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <div className="dash-scan-name">{exp.export_type}</div>
                      <div className="dash-scan-meta">
                        <span>{(exp.format || '').toUpperCase()}</span>
                        <span>{new Date(exp.created_at).toLocaleDateString()}</span>
                        {exp.file_size ? <span>{(exp.file_size / 1024).toFixed(1)} KB</span> : null}
                      </div>
                    </div>
                  </div>
                  <div className="dash-scan-right">
                    <span className={`sev-badge ${STATUS_COLORS[exp.status] || 'info'}`}>
                      <StatusIcon size={10} /> {exp.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
