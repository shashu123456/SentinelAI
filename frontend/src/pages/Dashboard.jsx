import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { scans, analytics } from '../services/api';
import Timeline from '../components/Timeline';
import {
  Shield, AlertTriangle, Clock, ExternalLink, Trash2,
  Upload, Target, Zap, Activity, Eye, FileCode, Package,
  ChevronRight, Scan, Layers, ShieldAlert, Crosshair
} from 'lucide-react';
import { SeverityDonut, ScanActivityChart, RiskTrendChart, OwaspBarChart } from '../components/Charts';
import { DashboardSkeleton } from '../components/Skeleton';
import './Dashboard.css';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [executionSteps, setExecutionSteps] = useState([]);
  const [executionStatus, setExecutionStatus] = useState('idle');
  const [executionProgress, setExecutionProgress] = useState(0);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [dashData, analyticsRes] = await Promise.all([
        scans.dashboard(),
        analytics.getDashboard().catch(() => null),
      ]);
      setStats(dashData);
      setAnalyticsData(analyticsRes);
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
      <DashboardSkeleton />
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
      {/* === AI MISSION CONTROL === */}
      {executionSteps.length > 0 && (
        <div className="dash-panel timeline-panel">
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">AI MISSION CONTROL</span>
          </div>
          <Timeline
            aiAnalysis={null}
            executionSteps={executionSteps}
            executionStatus={executionStatus}
            executionProgress={executionProgress}
          />
        </div>
      )}
        {/* === HEADER === */}
        <div className="dash-hero">
          <div className="dash-hero-left">
            <div className="dash-hero-badge">
              <Crosshair size={12} />
              <span>SENTINEL THREAT CENTER</span>
            </div>
            <h1 className="dash-hero-title">Threat Intelligence</h1>
            <p className="dash-hero-sub">Real-time security posture across <strong>{stats?.total_scans || 0}</strong> scanned API endpoints</p>
          </div>
          <div className="dash-hero-right">
            <Link to="/new-scan" className="dash-scan-btn">
              <Scan size={14} />
              <span>New Scan</span>
              <div className="dash-scan-btn-glow" />
            </Link>
          </div>
        </div>

        {/* === CORE METRICS ROW === */}
        <div className="dash-core-row">
          <div className="dash-core-card">
            <div className="dash-core-icon cyan"><Shield size={18} /></div>
            <div className="dash-core-data">
              <span className="dash-core-num">{stats?.total_scans || 0}</span>
              <span className="dash-core-label">Scans Executed</span>
            </div>
            <div className="dash-core-trend up">
              <Activity size={12} />
            </div>
          </div>

          <div className="dash-core-card" aria-label={`${totalFindings} total findings`}>
            <div className="dash-core-icon orange"><AlertTriangle size={18} aria-hidden="true" /></div>
            <div className="dash-core-data">
              <span className="dash-core-num">{totalFindings}</span>
              <span className="dash-core-label">Total Findings</span>
            </div>
            <div className={`dash-core-trend ${critHigh > 0 ? 'down' : 'up'}`} aria-hidden="true">
              <Zap size={12} />
            </div>
          </div>

          <div className="dash-core-card danger" role="alert" aria-label={`${critHigh} critical alerts`}>
            <div className="dash-core-icon red"><ShieldAlert size={18} aria-hidden="true" /></div>
            <div className="dash-core-data">
              <span className="dash-core-num">{critHigh}</span>
              <span className="dash-core-label">Critical Alerts</span>
            </div>
            {critHigh > 0 && <span className="dash-core-badge">ACTION REQUIRED</span>}
          </div>

          <div className="dash-core-card">
            <div className="dash-core-icon blue"><Layers size={18} /></div>
            <div className="dash-core-data">
              <span className="dash-core-num">{riskLevel}</span>
              <span className="dash-core-label">Risk Classification</span>
            </div>
            <span className="dash-core-score">{Math.round(avgScore)}/100</span>
          </div>
        </div>

        {/* === CHARTS ROW === */}
        <div className="dash-charts-row">
          <div className="dash-panel" role="img" aria-label="Severity distribution chart">
            <div className="dash-panel-header">
              <span className="dash-panel-dot" />
              <span className="dash-panel-title">SEVERITY DISTRIBUTION</span>
            </div>
            <SeverityDonut distribution={dist} />
          </div>

          <div className="dash-panel" role="img" aria-label="Scan activity over 30 days chart">
            <div className="dash-panel-header">
              <span className="dash-panel-dot" />
              <span className="dash-panel-title">SCAN ACTIVITY (30D)</span>
            </div>
            <div className="dash-chart-body">
              <ScanActivityChart data={analyticsData?.scan_activity} />
            </div>
          </div>
        </div>

        <div className="dash-charts-row">
          <div className="dash-panel" role="img" aria-label="Risk trend chart">
            <div className="dash-panel-header">
              <span className="dash-panel-dot" />
              <span className="dash-panel-title">RISK TREND</span>
            </div>
            <div className="dash-chart-body">
              <RiskTrendChart data={analyticsData?.risk_trend} />
            </div>
          </div>

          <div className="dash-panel" role="img" aria-label="OWASP findings distribution chart">
            <div className="dash-panel-header">
              <span className="dash-panel-dot" />
              <span className="dash-panel-title">OWASP FINDINGS</span>
            </div>
            <div className="dash-chart-body">
              <OwaspBarChart data={analyticsData?.owasp_distribution} />
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
            <div className="dash-empty-onboard">
              <div className="dash-empty-icon">
                <Shield size={32} />
              </div>
              <h4>Welcome to SentinelAI</h4>
              <p>Start securing your applications by running your first scan.</p>
              <div className="dash-onboard-steps">
                <Link to="/new-scan" className="dash-onboard-step">
                  <div className="dash-onboard-num">1</div>
                  <div className="dash-onboard-text">
                    <span className="dash-onboard-title">Upload API Spec</span>
                    <span className="dash-onboard-desc">Scan your OpenAPI/Swagger file for vulnerabilities</span>
                  </div>
                  <Upload size={14} className="dash-onboard-arrow" />
                </Link>
                <Link to="/sast" className="dash-onboard-step">
                  <div className="dash-onboard-num">2</div>
                  <div className="dash-onboard-text">
                    <span className="dash-onboard-title">Run SAST Analysis</span>
                    <span className="dash-onboard-desc">Static code analysis for Python, JavaScript, Java</span>
                  </div>
                  <FileCode size={14} className="dash-onboard-arrow" />
                </Link>
                <Link to="/deps" className="dash-onboard-step">
                  <div className="dash-onboard-num">3</div>
                  <div className="dash-onboard-text">
                    <span className="dash-onboard-title">Scan Dependencies</span>
                    <span className="dash-onboard-desc">Detect known CVEs in your packages</span>
                  </div>
                  <Package size={14} className="dash-onboard-arrow" />
                </Link>
                <Link to="/copilot" className="dash-onboard-step">
                  <div className="dash-onboard-num">4</div>
                  <div className="dash-onboard-text">
                    <span className="dash-onboard-title">Ask AI Copilot</span>
                    <span className="dash-onboard-desc">Get AI-powered security recommendations</span>
                  </div>
                  <Target size={14} className="dash-onboard-arrow" />
                </Link>
              </div>
            </div>
          ) : (
            <div className="dash-scan-list" role="list" aria-label="Recent scans">
              {stats.recent_scans.map((scan, idx) => (
                <div key={scan.id} className="dash-scan-item" role="listitem">
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
          )}</div>

        {/* === SYSTEM STATUS BAR === */}
        <div className="dash-status-bar" role="status" aria-label="System status">
          <div className="dash-status-item">
            <span className="dash-status-dot online" /> <span>Scanner Engine</span>
          </div>
          <div className="dash-status-item">
            <span className="dash-status-dot online" /> <span>Threat Intel Feed</span>
          </div>
          <div className="dash-status-item">
            <span className="dash-status-dot online" /> <span>Database</span>
          </div>
          <div className="dash-status-item">
            <span className="dash-status-dot online" /> <span>OWASP Rules</span>
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
  if (s >= 80) return '#ff2244';
  if (s >= 60) return '#ff6622';
  if (s >= 30) return '#ffaa00';
  if (s > 0) return '#00ff88';
  return '#00d4ff';
}