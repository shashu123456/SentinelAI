import { useState, useEffect } from 'react';
import { Shield, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Target, BarChart3 } from 'lucide-react';
import { SkeletonCard } from '../components/Skeleton';

const API = '/api';

export default function ExecutiveReport() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadReport(); }, []);

  const loadReport = async () => {
    try {
      const res = await fetch(`${API}/orgs/1/executive-report`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      setReport(data);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  if (loading) return <div className="page-content"><SkeletonCard lines={5} /></div>;
  if (!report) return <div className="page-content"><div className="empty-state"><div className="empty-state-icon"><Shield size={24} /></div><div className="empty-state-title">No Data Available</div></div></div>;

  const trendIcon = report.risk?.trend === 'improving' ? TrendingDown : report.risk?.trend === 'worsening' ? TrendingUp : Target;
  const trendColor = report.risk?.trend === 'improving' ? 'var(--accent-green)' : report.risk?.trend === 'worsening' ? 'var(--accent-red)' : 'var(--text-muted)';

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Executive Security Report</h1>
          <p className="dash-hero-sub">Security posture overview for leadership and compliance teams</p>
        </div>
      </div>

      {/* KPI Row */}
      <div className="dash-core-row" style={{ marginTop: 20 }}>
        <div className="dash-core-card">
          <div className="dash-core-icon cyan"><BarChart3 size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{report.scans?.total_30d || 0}</span>
            <span className="dash-core-label">Scans (30d)</span>
          </div>
        </div>
        <div className="dash-core-card">
          <div className="dash-core-icon orange"><AlertTriangle size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{report.findings?.total_30d || 0}</span>
            <span className="dash-core-label">Findings (30d)</span>
          </div>
        </div>
        <div className="dash-core-card">
          <div className="dash-core-icon blue"><Target size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{report.risk?.average_score_30d || 0}</span>
            <span className="dash-core-label">Avg Risk Score</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: trendColor }}>
            {trendIcon && <trendIcon size={12} />}
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)' }}>{report.risk?.trend}</span>
          </div>
        </div>
        <div className="dash-core-card danger">
          <div className="dash-core-icon red"><Shield size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{report.findings?.critical_and_high || 0}</span>
            <span className="dash-core-label">Critical & High</span>
          </div>
        </div>
      </div>

      {/* Severity Breakdown */}
      <div className="dash-panel" style={{ marginTop: 16 }}>
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">SEVERITY DISTRIBUTION (30D)</span>
        </div>
        <div style={{ padding: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
            {Object.entries(report.findings?.severity_distribution || {}).map(([sev, count]) => (
              <div key={sev} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 800, fontFamily: 'var(--font-display)', color: `var(--severity-${sev.toLowerCase()})` }}>{count}</div>
                <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', letterSpacing: '0.5px' }}>{sev}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {report.recommendations?.length > 0 && (
        <div className="dash-panel" style={{ marginTop: 16 }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">RECOMMENDATIONS</span>
          </div>
          <div>
            {report.recommendations.map((rec, i) => (
              <div key={i} style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                <span className={`sev-badge ${rec.priority}`}>{rec.priority}</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{rec.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{rec.description}</div>
                  <div style={{ fontSize: 11, color: 'var(--accent-cyan)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>{rec.action}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
