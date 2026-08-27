import { useState, useEffect } from 'react';
import { request } from '../services/api';
import {
  Shield, AlertTriangle, Lock, Eye, Globe, Activity,
  Clock, User, Monitor, RefreshCw, Server
} from 'lucide-react';
import './Dashboard.css';

export default function SecurityEvents() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState({ severity: '', category: '' });

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await request('/security-events/dashboard');
      setDashboard(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (loading && !dashboard) {
    return (
      <div className="page-content">
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>
          Loading security dashboard...
        </div>
      </div>
    );
  }

  const stats = dashboard?.stats || {};
  const events = (dashboard?.recent_events || []).filter(e => {
    if (filter.severity && e.severity !== filter.severity) return false;
    if (filter.category && e.category !== filter.category) return false;
    return true;
  });
  const sessions = dashboard?.active_sessions || [];

  return (
    <div className="page-content">
      {/* Header */}
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-badge">
            <Shield size={12} />
            <span>SECURITY OPERATIONS CENTER</span>
          </div>
          <h1 className="dash-hero-title">Security Events</h1>
          <p className="dash-hero-sub">
            Real-time threat detection, session monitoring, and security event tracking
          </p>
        </div>
        <div className="dash-hero-right">
          <button className="dash-scan-btn" onClick={loadDashboard}>
            <RefreshCw size={14} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="dash-panel" style={{ borderColor: 'var(--accent-red)', padding: 16, marginBottom: 16 }}>
          <p style={{ color: 'var(--accent-red)', margin: 0, fontSize: 13 }}>{error}</p>
        </div>
      )}

      {/* Stats Row */}
      <div className="dash-core-row">
        <div className="dash-core-card">
          <div className="dash-core-icon cyan"><Activity size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{stats.total_events || 0}</span>
            <span className="dash-core-label">Total Events</span>
          </div>
        </div>

        <div className="dash-core-card danger">
          <div className="dash-core-icon red"><AlertTriangle size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{stats.events_last_hour || 0}</span>
            <span className="dash-core-label">Events (1h)</span>
          </div>
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon orange"><Lock size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{stats.blocked_ips || 0}</span>
            <span className="dash-core-label">Blocked IPs</span>
          </div>
        </div>

        <div className="dash-core-card">
          <div className="dash-core-icon blue"><Monitor size={18} /></div>
          <div className="dash-core-data">
            <span className="dash-core-num">{stats.active_sessions || 0}</span>
            <span className="dash-core-label">Active Sessions</span>
          </div>
        </div>
      </div>

      {/* Severity Distribution */}
      <div className="dash-charts-row">
        <div className="dash-panel">
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SEVERITY DISTRIBUTION</span>
          </div>
          <div style={{ padding: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {['critical', 'high', 'medium', 'low', 'info'].map(sev => (
              <div key={sev} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 14px', borderRadius: 8,
                background: 'var(--bg-tertiary)',
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: sev === 'critical' ? '#ff2244' : sev === 'high' ? '#ff6622' : sev === 'medium' ? '#ffaa00' : sev === 'low' ? '#00d4ff' : '#666',
                }} />
                <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{sev}</span>
                <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                  {stats.severity_distribution?.[sev] || 0}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="dash-panel">
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">CATEGORIES</span>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(stats.category_distribution || {}).map(([cat, count]) => (
              <div key={cat} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '6px 10px', borderRadius: 6,
                background: 'var(--bg-tertiary)', fontSize: 12,
              }}>
                <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                  {cat.replace(/_/g, ' ')}
                </span>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{count}</span>
              </div>
            ))}
            {Object.keys(stats.category_distribution || {}).length === 0 && (
              <div style={{ padding: 12, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>
                No events yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filters + Events List */}
      <div className="dash-panel" style={{ marginBottom: 16 }}>
        <div className="dash-panel-header">
          <span className="dash-panel-dot" style={{ background: 'var(--accent-red)' }} />
          <span className="dash-panel-title">SECURITY EVENTS ({events.length})</span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <select
              value={filter.severity}
              onChange={e => setFilter({ ...filter, severity: e.target.value })}
              style={{
                padding: '4px 8px', borderRadius: 4, fontSize: 11,
                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            <select
              value={filter.category}
              onChange={e => setFilter({ ...filter, category: e.target.value })}
              style={{
                padding: '4px 8px', borderRadius: 4, fontSize: 11,
                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="">All Categories</option>
              <option value="brute_force">Brute Force</option>
              <option value="session">Session</option>
              <option value="auth">Authentication</option>
              <option value="rate_limit">Rate Limit</option>
            </select>
          </div>
        </div>

        {events.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <Shield size={32} style={{ color: 'var(--accent-green)', marginBottom: 12 }} />
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>All Clear</h4>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No security events detected. System is operating normally.</p>
          </div>
        ) : (
          <div style={{ maxHeight: 500, overflowY: 'auto' }}>
            {events.map((event, idx) => (
              <div key={idx} style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                padding: '12px 16px', borderBottom: '1px solid var(--border)',
                fontSize: 13,
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                  background: event.severity === 'critical' ? '#ff2244' :
                    event.severity === 'high' ? '#ff6622' :
                    event.severity === 'medium' ? '#ffaa00' :
                    event.severity === 'low' ? '#00d4ff' : '#666',
                }} />
                <div style={{ flex: 1 }}>
                  <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{event.title}</div>
                  <div style={{ color: 'var(--text-tertiary)', fontSize: 11, marginTop: 2, display: 'flex', gap: 12 }}>
                    <span style={{ textTransform: 'capitalize' }}>{event.category?.replace(/_/g, ' ')}</span>
                    <span>{new Date(event.timestamp).toLocaleString()}</span>
                    <span style={{ textTransform: 'capitalize' }}>{event.severity}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Active Sessions */}
      <div className="dash-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" style={{ background: 'var(--accent-blue)' }} />
          <span className="dash-panel-title">ACTIVE SESSIONS ({sessions.length})</span>
        </div>
        {sessions.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
            No active sessions
          </div>
        ) : (
          <div className="dash-scan-list">
            {sessions.map((session, idx) => (
              <div key={idx} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div className="dash-scan-idx">{String(idx + 1).padStart(2, '0')}</div>
                  <div className="dash-scan-info">
                    <span className="dash-scan-name" style={{ fontFamily: 'monospace', fontSize: 12 }}>
                      {session.token_prefix}...
                    </span>
                    <div className="dash-scan-meta">
                      <span><Globe size={11} /> {session.ip || 'Unknown'}</span>
                      <span><Monitor size={11} /> {session.user_agent?.substring(0, 50) || 'Unknown'}</span>
                      <span><Clock size={11} /> {new Date(session.created_at * 1000).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
