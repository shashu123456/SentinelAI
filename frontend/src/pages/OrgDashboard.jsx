import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useOrg } from '../context/OrgContext';
import { organizations } from '../services/api';
import {
  Shield, AlertTriangle, Users, FolderOpen, BarChart3,
  Activity, Target, Zap, Layers, ShieldAlert, Crosshair,
  ChevronRight, Scan, Clock
} from 'lucide-react';
import { SeverityDonut } from '../components/Charts';
import { DashboardSkeleton } from '../components/Skeleton';
import './Dashboard.css';

export default function OrgDashboard() {
  const { currentOrg } = useOrg();
  const [dashboard, setDashboard] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!currentOrg) {
      setLoading(false);
      return;
    }
    loadData();
  }, [currentOrg]);

  const loadData = async () => {
    if (!currentOrg) return;
    try {
      setLoading(true);
      const [dashData, analyticsData] = await Promise.all([
        organizations.dashboard(currentOrg.id),
        organizations.analytics(currentOrg.id).catch(() => null),
      ]);
      setDashboard(dashData);
      setAnalytics(analyticsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const dist = useMemo(() => dashboard?.severity_distribution || {}, [dashboard]);
  const totalFindings = useMemo(() => Object.values(dist).reduce((a, b) => a + b, 0), [dist]);
  const critHigh = (dist.Critical || 0) + (dist.High || 0);

  if (!currentOrg) {
    return (
      <div className="page-content">
        <div className="dash-empty-onboard">
          <div className="dash-empty-icon"><Shield size={32} /></div>
          <h4>No Organization Selected</h4>
          <p>Create or select an organization from the sidebar to view the organization dashboard.</p>
        </div>
      </div>
    );
  }

  if (loading) return (
    <div className="page-content"><DashboardSkeleton /></div>
  );

  if (error) return (
    <div className="page-content">
      <div className="dash-error-card">
        <ShieldAlert size={28} />
        <h3>Failed to Load Dashboard</h3>
        <p>{error}</p>
        <button className="btn-primary" onClick={loadData}>Retry</button>
      </div>
    </div>
  );

  return (
    <div className="page-content">
      {/* Header */}
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-badge">
            <Crosshair size={12} />
            <span>ORGANIZATION INTELLIGENCE</span>
          </div>
          <h1 className="dash-hero-title">{currentOrg.name}</h1>
          <p className="dash-hero-sub">
            Aggregate security posture across <strong>{dashboard?.total_projects || 0}</strong> projects
            and <strong>{dashboard?.total_members || 0}</strong> team members
          </p>
        </div>
      </div>

      {/* Core Metrics */}
      <div className="dash-core-row">
        <div className="dash-core-card">
          <div className="dash-core-icon cyan"><Scan size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{dashboard?.total_scans || 0}</span>
            <span className="dash-core-label">Total Scans</span>
          </div>
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon orange"><AlertTriangle size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{totalFindings}</span>
            <span className="dash-core-label">Total Findings</span>
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
          <div className="dash-core-icon blue"><Layers size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{dashboard?.average_risk_score || 0}/100</span>
            <span className="dash-core-label">Avg Risk Score</span>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="dash-core-row">
        <div className="dash-core-card">
          <div className="dash-core-icon cyan"><FolderOpen size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{dashboard?.total_projects || 0}</span>
            <span className="dash-core-label">Projects</span>
          </div>
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon purple"><Users size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{dashboard?.total_members || 0}</span>
            <span className="dash-core-label">Members</span>
          </div>
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon green"><Activity size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{dashboard?.total_teams || 0}</span>
            <span className="dash-core-label">Teams</span>
          </div>
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon orange"><Target size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{dashboard?.completed_scans || 0}</span>
            <span className="dash-core-label">Completed Scans</span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="dash-charts-row">
        <div className="dash-panel">
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SEVERITY DISTRIBUTION</span>
          </div>
          <SeverityDonut distribution={dist} />
        </div>

        <div className="dash-panel">
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SCANS PER PROJECT</span>
          </div>
          <div className="dash-scan-list">
            {(dashboard?.scans_per_project || []).map((item, i) => (
              <div key={i} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div className="dash-scan-idx">{String(i + 1).padStart(2, '0')}</div>
                  <div className="dash-scan-info">
                    <span className="dash-scan-name">{item.project}</span>
                  </div>
                </div>
                <div className="dash-scan-right">
                  <span className="dash-scan-score">{item.scans} scans</span>
                </div>
              </div>
            ))}
            {(!dashboard?.scans_per_project || dashboard.scans_per_project.length === 0) && (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '13px' }}>
                No scan data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Scans */}
      <div className="dash-panel dash-scans-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">RECENT ORGANIZATION SCANS</span>
        </div>
        {!dashboard?.recent_scans?.length ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '13px' }}>
            No scans in this organization yet
          </div>
        ) : (
          <div className="dash-scan-list">
            {dashboard.recent_scans.map((scan, idx) => (
              <div key={scan.id} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div className="dash-scan-idx">{String(idx + 1).padStart(2, '0')}</div>
                  <div className="dash-scan-info">
                    <Link to={`/scan/${scan.id}`} className="dash-scan-name">
                      {scan.api_name}
                    </Link>
                    <div className="dash-scan-meta">
                      <span><AlertTriangle size={11} /> {scan.total_vulnerabilities} findings</span>
                      <span><Clock size={11} /> {new Date(scan.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <div className="dash-scan-right">
                  <span className={`dash-scan-score ${getRiskClass(scan.risk_score)}`}>{scan.risk_score}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="dash-panel dash-actions-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">QUICK ACTIONS</span>
        </div>
        <div className="dash-actions-grid">
          <Link to="/org/teams" className="dash-action-card">
            <div className="dash-action-icon blue"><Users size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">Manage Teams</span>
              <span className="dash-action-desc">Create and manage teams</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
          <Link to="/org/invitations" className="dash-action-card">
            <div className="dash-action-icon green"><Target size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">Invite Members</span>
              <span className="dash-action-desc">Grow your organization</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
          <Link to="/org/api-keys" className="dash-action-card">
            <div className="dash-action-icon purple"><Zap size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">API Keys</span>
              <span className="dash-action-desc">Manage programmatic access</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
          <Link to="/org/settings" className="dash-action-card">
            <div className="dash-action-icon orange"><Shield size={20} /></div>
            <div className="dash-action-text">
              <span className="dash-action-name">Org Settings</span>
              <span className="dash-action-desc">Configure your organization</span>
            </div>
            <ChevronRight size={14} className="dash-action-arrow" />
          </Link>
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
