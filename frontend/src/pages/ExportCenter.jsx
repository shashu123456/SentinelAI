import { useState, useEffect } from 'react';
import { Download, FileText, FileJson, File, Shield, Plus, Clock, CheckCircle, AlertTriangle, Loader } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';

const API = '/api';
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
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadExports(); }, []);

  const loadExports = async () => {
    try {
      const res = await fetch(`${API}/orgs/1/exports`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      setExports(data.items || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  if (loading) return <div className="page-content"><SkeletonTable rows={3} cols={4} /></div>;

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Export Center</h1>
          <p className="dash-hero-sub">Export scan results and reports in multiple formats</p>
        </div>
        <button className="btn-primary"><Plus size={14} /> New Export</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 20 }}>
        {Object.entries(FORMAT_INFO).map(([fmt, info]) => {
          const Icon = info.icon;
          return (
            <div key={fmt} style={{
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)', padding: 20, textAlign: 'center',
              cursor: 'pointer', transition: 'all 0.2s ease',
            }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: `${info.color}11`, border: `1px solid ${info.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: info.color, margin: '0 auto 10px' }}>
                <Icon size={18} />
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{info.label}</div>
            </div>
          );
        })}
      </div>

      {exports.length > 0 && (
        <div className="dash-panel" style={{ marginTop: 20 }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">RECENT EXPORTS</span>
          </div>
          <div>
            {exports.map(exp => {
              const fmt = FORMAT_INFO[exp.format] || FORMAT_INFO.json;
              const StatusIcon = STATUS_ICONS[exp.status] || Clock;
              return (
                <div key={exp.id} className="dash-scan-item">
                  <div className="dash-scan-left">
                    <div style={{ width: 36, height: 36, borderRadius: 8, background: `${fmt.color}11`, border: `1px solid ${fmt.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: fmt.color, flexShrink: 0 }}>
                      <fmt.icon size={16} />
                    </div>
                    <div>
                      <div className="dash-scan-name">{exp.export_type}</div>
                      <div className="dash-scan-meta">
                        <span>{exp.format.toUpperCase()}</span>
                        <span>{new Date(exp.created_at).toLocaleDateString()}</span>
                        {exp.file_size && <span>{(exp.file_size / 1024).toFixed(1)} KB</span>}
                      </div>
                    </div>
                  </div>
                  <div className="dash-scan-right">
                    <span className={`sev-badge ${STATUS_COLORS[exp.status]}`}>
                      <StatusIcon size={10} /> {exp.status}
                    </span>
                    {exp.status === 'completed' && (
                      <button className="btn-sm btn-outline" style={{ padding: '4px 10px' }}>
                        <Download size={12} /> Download
                      </button>
                    )}
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
