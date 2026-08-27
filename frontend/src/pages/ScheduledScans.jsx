import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Calendar, Clock, Plus, Play, Pause, Trash2, Edit3,
  FileText, AlertTriangle, CheckCircle, ChevronRight,
  Settings, Zap, RefreshCw, Copy,
} from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';

const API = '/api';

export default function ScheduledScans() {
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => { loadScans(); }, []);

  const loadScans = async () => {
    try {
      const res = await fetch(`${API}/orgs/1/scheduled-scans`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      setScans(data.items || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  if (loading) return <div className="page-content"><SkeletonTable rows={4} cols={5} /></div>;

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Scheduled Scans</h1>
          <p className="dash-hero-sub">Automate recurring security scans on a schedule</p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={14} /> New Schedule
        </button>
      </div>

      {scans.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><Calendar size={24} /></div>
          <div className="empty-state-title">No Scheduled Scans</div>
          <div className="empty-state-desc">Set up recurring scans to continuously monitor your APIs and code for vulnerabilities.</div>
        </div>
      ) : (
        <div className="dash-panel" style={{ marginTop: 20 }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SCHEDULED SCANS</span>
          </div>
          <div>
            {scans.map(scan => (
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
