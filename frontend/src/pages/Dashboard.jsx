import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { scans } from '../services/api';
import {
  Shield, AlertTriangle, Clock, ExternalLink, Trash2,
  Upload, Target, Zap, Activity, Eye, FileCode, Package,
  ChevronRight, Scan, Layers, ShieldAlert, Crosshair
} from 'lucide-react';
import './Dashboard.css';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await scans.dashboard();
      setStats(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this scan?')) return;
    try {
      await scans.delete(id);
      loadDashboard();
    } catch { alert('Failed to delete scan'); }
  };

  const dist = useMemo(() => stats?.severity_distribution || {}, [stats]);
  const totalFindings = useMemo(() => Object.values(dist).reduce((a, b) => a + b, 0), [dist]);
  const critHigh = (dist.Critical || 0) + (dist.High || 0);
  const avgScore = stats?.average_risk_score || 0;
  const riskLevel = getRiskLevel(avgScore);

  if (loading) return (
    <div className="page-content">
      <div className="dash-loading">
        <div className="dash-loading-ring">
          <svg viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(59,130,246,0.08)" strokeWidth="4" />
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--accent-blue)" strokeWidth="4"
              strokeDasharray="80 240" strokeLinecap="round" className="dash-loading-arc" />
          </svg>
        </div>
        <div className="dash-loading-text">
          <span className="dash-loading-label">INITIALIZING THREAT MATRIX</span>
          <span className="dash-loading-sub">Loading security telemetry...</span>
        </div>
      </div>
    </div>
  );

  if (error) return (
    <div className="page-content">
      <div className="dash-error-card">
        <ShieldAlert size={28} />
        <h3>System Offline</h3>
        <p>{error}</p>
        <button className="btn-primary" onClick={loadDashboard}>Retry Connection</button>
      </div>
    </div>
  );

  return (
    <div className="page-content">
      {/* === HEADER === */}
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-badge">
            <Crosshair size={14} />
            <span>SENTINEL COMMAND CENTER</span>
          </div>
          <h1 className="dash-hero-title">Threat Intelligence</h1>
          <p className="dash-hero-sub">Real-time security posture monitoring across <strong>{stats?.total_scans || 0}</strong> scanned API endpoints</p>
        </div>
        <div className="dash-hero-right">
          <Link to="/new-scan" className="dash-scan-btn">
            <Scan size={16} />
            <span>New Scan</span>
            <div className="dash-scan-btn-glow" />
          </Link>
        </div>
      </div>

      {/* === CORE METRICS ROW === */}
      <div className="dash-core-row">
        <div className="dash-core-card">
          <div className="dash-core-icon blue"><Shield size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{stats?.total_scans || 0}</span>
            <span className="dash-core-label">Scans Executed</span>
          </div>
          <div className="dash-core-trend up">
            <Activity size={12} />
          </div>
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon orange"><AlertTriangle size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{totalFindings}</span>
            <span className="dash-core-label">Total Findings</span>
          </div>
          <div className={`dash-core-trend ${critHigh > 0 ? 'down' : 'up'}`}>
            <Zap size={12} />
          </div>
        </div>

        <div className="dash-core-card danger">
          <div className="dash-core-icon red"><ShieldAlert size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{critHigh}</span>
            <span className="dash-core-label">Critical Alerts</span>
          </div>
          {critHigh > 0 && <span className="dash-core-badge">ACTION REQUIRED</span>}
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon cyan"><Layers size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{riskLevel}</span>
            <span className="dash-core-label">Risk Classification</span>
          </div>
          <span className="dash-core-score">{Math.round(avgScore)}/100</span>
        </div>
      </div>

      {/* === THREAT POSTURE + SEVERITY MATRIX === */}
      <div className="dash-dual-section">
        {/* Threat Gauge */}
        <div className="dash-panel dash-threat-panel">
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">THREAT GAUGE</span>
          </div>
          <div className="dash-threat-body">
            <div className="dash-gauge-visual">
              <svg viewBox="0 0 200 120" className="dash-gauge-svg">
                {/* Background arc */}
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="rgba(59,130,246,0.08)" strokeWidth="10" strokeLinecap="round" />
                {/* Filled arc segments */}
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#gaugeGradient)" strokeWidth="10" strokeLinecap="round"
                  strokeDasharray={`${(avgScore / 100) * 251.2} 251.2`} className="dash-gauge-arc" />
                <defs>
                  <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="var(--accent-blue)" />
                    <stop offset="50%" stopColor="var(--accent-purple)" />
                    <stop offset="100%" stopColor="var(--accent-red)" />
                  </linearGradient>
                </defs>
                {/* Tick marks */}
                {[0, 20, 40, 60, 80, 100].map((tick) => {
                  const angle = (tick / 100) * 180 - 180;
                  const rad = (angle * Math.PI) / 180;
                  const x1 = 100 + 72 * Math.cos(rad);
                  const y1 = 100 + 72 * Math.sin(rad);
                  const x2 = 100 + 82 * Math.cos(rad);
                  const y2 = 100 + 82 * Math.sin(rad);
                  return <line key={tick} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(59,130,246,0.2)" strokeWidth="1.5" />;
                })}
              </svg>
              <div className="dash-gauge-center">
                <span className="dash-gauge-value" style={{ color: getRiskColor(avgScore) }}>{Math.round(avgScore)}</span>
                <span className="dash-gauge-sub">/100</span>
              </div>
            </div>
            <div className="dash-gauge-labels">
              <span>LOW</span><span>MEDIUM</span><span>HIGH</span><span>CRITICAL</span>
            </div>
            <div className={`dash-threat-level ${getRiskClass(avgScore)}`}>
              <span className="dash-threat-dot" />
              {riskLevel} Threat Level
            </div>
          </div>
        </div>

        {/* Severity Matrix */}
        <div className="dash-panel dash-matrix-panel">
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SEVERITY MATRIX</span>
          </div>
          <div className="dash-matrix-body">
            {['Critical', 'High', 'Medium', 'Low', 'Info'].map(sev => {
              const count = dist[sev] || 0;
              const pct = totalFindings > 0 ? (count / totalFindings) * 100 : 0;
              return (
                <div key={sev} className="dash-matrix-row">
                  <div className="dash-matrix-label">
                    <span className={`dash-matrix-dot ${sev.toLowerCase()}`} />
                    <span className="dash-matrix-name">{sev}</span>
                  </div>
                  <div className="dash-matrix-bar-track">
                    <div className={`dash-matrix-bar-fill ${sev.toLowerCase()}`} style={{ width: `${Math.max(pct, count > 0 ? 4 : 0)}%` }} />
                  </div>
                  <span className="dash-matrix-count">{count}</span>
                </div>
              );
            })}
            {totalFindings > 0 && (
              <div className="dash-matrix-stack">
                {['Critical', 'High', 'Medium', 'Low', 'Info'].map(sev => (
                  dist[sev] > 0 ? (
                    <div key={sev} className={`dash-stack-seg ${sev.toLowerCase()}`} style={{ flex: dist[sev] }} title={`${sev}: ${dist[sev]}`} />
                  ) : null
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* === QUICK ACTIONS === */}
      <div className="dash-panel dash-actions-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">QUICK ACCESS</span>
        </div>
        <div className="dash-actions-grid">
          <Link to="/new-scan" className="dash-action-card">
            <div className="dash-action-icon blue"><FileCode size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">API Scanner</span>
              <span className="dash-action-desc">Upload OpenAPI spec</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
          <Link to="/sast" className="dash-action-card">
            <div className="dash-action-icon purple"><Eye size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">SAST Analysis</span>
              <span className="dash-action-desc">Static code analysis</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
          <Link to="/deps" className="dash-action-card">
            <div className="dash-action-icon orange"><Package size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">Dependency Scan</span>
              <span className="dash-action-desc">CVE detection</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
          <Link to="/copilot" className="dash-action-card">
            <div className="dash-action-icon green"><Target size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">AI Analyst</span>
              <span className="dash-action-desc">Ask security questions</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
        </div>
      </div>

      {/* === RECENT SCANS === */}
      <div className="dash-panel dash-scans-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">RECENT OPERATIONS</span>
        </div>
        {!stats?.recent_scans?.length ? (
          <div className="dash-empty-state">
            <div className="dash-empty-icon">
              <Shield size={36} />
            </div>
            <h4>No Operations Recorded</h4>
            <p>Execute your first security scan to begin threat analysis.</p>
            <Link to="/new-scan" className="btn-primary">
              <Upload size={14} /> Initiate Scan
            </Link>
          </div>
        ) : (
          <div className="dash-scan-list">
            {stats.recent_scans.map((scan, idx) => (
              <div key={scan.id} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div className="dash-scan-idx">{String(idx + 1).padStart(2, '0')}</div>
                  <div className="dash-scan-info">
                    <Link to={`/scan/${scan.id}`} className="dash-scan-name">
                      {scan.api_name} <ExternalLink size={11} />
                    </Link>
                    <div className="dash-scan-meta">
                      <span><Target size={11} /> {scan.total_endpoints} endpoints</span>
                      <span><AlertTriangle size={11} /> {scan.total_vulnerabilities} findings</span>
                      <span><Clock size={11} /> {new Date(scan.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <div className="dash-scan-right">
                  <span className={`dash-scan-score ${getRiskClass(scan.risk_score)}`}>{scan.risk_score}</span>
                  <div className="dash-scan-actions">
                    <Link to={`/scan/${scan.id}`} className="dash-scan-btn-sm">View</Link>
                    <button className="dash-scan-btn-sm danger" onClick={() => handleDelete(scan.id)}>
                      <Trash2 size={11} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* === SYSTEM STATUS BAR === */}
      <div className="dash-status-bar">
        <div className="dash-status-item">
          <span className="dash-status-dot online" />
          <span>Scanner Engine</span>
        </div>
        <div className="dash-status-item">
          <span className="dash-status-dot online" />
          <span>Threat Intelligence</span>
        </div>
        <div className="dash-status-item">
          <span className="dash-status-dot online" />
          <span>Database</span>
        </div>
        <div className="dash-status-item">
          <span className="dash-status-dot online" />
          <span>OWASP Rules</span>
        </div>
      </div>
    </div>
  );
}

function getRiskClass(s) {
  if (s >= 80) return 'critical';
  if (s >= 60) return 'high';
  if (s >= 30) return 'medium';
  return 'low';
}

function getRiskLevel(s) {
  if (s >= 80) return 'Critical';
  if (s >= 60) return 'High';
  if (s >= 30) return 'Medium';
  if (s > 0) return 'Low';
  return 'Clean';
}

function getRiskColor(s) {
  if (s >= 80) return '#ef4444';
  if (s >= 60) return '#f97316';
  if (s >= 30) return '#eab308';
  if (s > 0) return '#10b981';
  return '#3b82f6';
}
