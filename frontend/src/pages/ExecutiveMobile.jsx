import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { analytics, scans } from '../services/api';
import {
  Shield, AlertTriangle, TrendingUp, Clock, ChevronRight,
  Wifi, WifiOff, RefreshCw,
} from 'lucide-react';
import './ExecutiveMobile.css';

/**
 * Executive Mobile Dashboard — optimized for phone screens.
 * Swipeable KPI cards, touch-friendly metrics, and real-time alerts.
 */
export default function ExecutiveMobile() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeCard, setActiveCard] = useState(0);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastRefresh, setLastRefresh] = useState(null);
  const touchStartX = useRef(0);
  const touchEndX = useRef(0);

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleOnline = () => { setIsOnline(true); fetchDashboard(); };
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  async function fetchDashboard() {
    try {
      const res = await analytics.getDashboard();
      setData(res);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Dashboard fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }

  // Swipe handling for KPI cards
  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchMove = (e) => {
    touchEndX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = () => {
    const diff = touchStartX.current - touchEndX.current;
    const kpiCount = 4;
    if (Math.abs(diff) > 50) {
      if (diff > 0 && activeCard < kpiCount - 1) {
        setActiveCard(prev => prev + 1);
      } else if (diff < 0 && activeCard > 0) {
        setActiveCard(prev => prev - 1);
      }
    }
  };

  const kpis = data ? [
    {
      label: 'Risk Score',
      value: data.risk_score ?? '—',
      icon: Shield,
      color: 'var(--accent-cyan)',
      suffix: '/100',
      trend: data.risk_trend,
    },
    {
      label: 'Critical Findings',
      value: data.critical_count ?? 0,
      icon: AlertTriangle,
      color: 'var(--accent-red)',
      suffix: '',
      trend: data.critical_trend,
    },
    {
      label: 'Scans Today',
      value: data.scans_today ?? 0,
      icon: TrendingUp,
      color: 'var(--accent-green)',
      suffix: '',
      trend: null,
    },
    {
      label: 'Avg Fix Time',
      value: data.avg_fix_time ?? '—',
      icon: Clock,
      color: 'var(--accent-yellow)',
      suffix: 'h',
      trend: data.fix_time_trend,
    },
  ] : [];

  if (loading) {
    return (
      <div className="exec-mobile-loading">
        <div className="spinner" />
        <span>Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="exec-mobile" role="main" aria-label="Executive Dashboard">
      {/* Header */}
      <header className="exec-mobile-header">
        <div>
          <h1 className="exec-mobile-title">Security Overview</h1>
          <p className="exec-mobile-subtitle">
            {user?.username ? `Welcome, ${user.username}` : 'Executive Summary'}
          </p>
        </div>
        <div className="exec-mobile-actions">
          <span className="exec-mobile-status" aria-label={isOnline ? 'Online' : 'Offline'}>
            {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
          </span>
          <button
            className="exec-mobile-refresh"
            onClick={fetchDashboard}
            aria-label="Refresh dashboard"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      {/* Swipeable KPI Cards */}
      <section
        className="exec-mobile-kpis"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        aria-label="Key performance indicators"
      >
        <div className="exec-mobile-kpi-track" style={{ transform: `translateX(-${activeCard * 100}%)` }}>
          {kpis.map((kpi, i) => {
            const Icon = kpi.icon;
            return (
              <div
                key={kpi.label}
                className="exec-mobile-kpi-card"
                style={{ '--card-accent': kpi.color }}
                role="article"
                aria-label={`${kpi.label}: ${kpi.value}${kpi.suffix}`}
              >
                <div className="exec-kpi-icon">
                  <Icon size={22} />
                </div>
                <div className="exec-kpi-content">
                  <span className="exec-kpi-value">
                    {kpi.value}<span className="exec-kpi-suffix">{kpi.suffix}</span>
                  </span>
                  <span className="exec-kpi-label">{kpi.label}</span>
                </div>
                {kpi.trend && (
                  <span className={`exec-kpi-trend ${kpi.trend > 0 ? 'up' : 'down'}`}>
                    {kpi.trend > 0 ? '↑' : '↓'} {Math.abs(kpi.trend)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Dot indicators */}
        <div className="exec-mobile-dots" role="tablist" aria-label="KPI pages">
          {kpis.map((_, i) => (
            <button
              key={i}
              className={`exec-mobile-dot ${i === activeCard ? 'active' : ''}`}
              onClick={() => setActiveCard(i)}
              aria-label={`Go to KPI ${i + 1}`}
              role="tab"
              aria-selected={i === activeCard}
            />
          ))}
        </div>
      </section>

      {/* Quick Actions */}
      <section className="exec-mobile-section" aria-label="Quick actions">
        <h2 className="exec-section-title">Quick Actions</h2>
        <div className="exec-mobile-actions-grid">
          <button className="exec-action-card" onClick={() => navigate('/new-scan')}>
            <Shield size={20} />
            <span>New Scan</span>
          </button>
          <button className="exec-action-card" onClick={() => navigate('/copilot')}>
            <span style={{ fontSize: 20 }}>🤖</span>
            <span>AI Copilot</span>
          </button>
          <button className="exec-action-card" onClick={() => navigate('/vulnerabilities')}>
            <AlertTriangle size={20} />
            <span>Findings</span>
          </button>
          <button className="exec-action-card" onClick={() => navigate('/reports')}>
            <TrendingUp size={20} />
            <span>Reports</span>
          </button>
        </div>
      </section>

      {/* Recent Alerts */}
      <section className="exec-mobile-section" aria-label="Recent alerts">
        <div className="exec-section-header">
          <h2 className="exec-section-title">Recent Alerts</h2>
          <button className="exec-section-link" onClick={() => navigate('/security-events')}>
            View all <ChevronRight size={14} />
          </button>
        </div>
        <div className="exec-mobile-alerts">
          {(data?.recent_alerts || []).slice(0, 5).map((alert, i) => (
            <div key={i} className="exec-alert-card" role="article">
              <div className={`exec-alert-severity sev-badge ${(alert.severity || 'info').toLowerCase()}`}>
                {alert.severity || 'Info'}
              </div>
              <div className="exec-alert-content">
                <span className="exec-alert-title">{alert.title || 'Security Event'}</span>
                <span className="exec-alert-time">{alert.time || 'Just now'}</span>
              </div>
            </div>
          ))}
          {(!data?.recent_alerts || data.recent_alerts.length === 0) && (
            <div className="exec-mobile-empty">
              <Shield size={32} />
              <span>No recent alerts — all clear</span>
            </div>
          )}
        </div>
      </section>

      {/* Last refreshed */}
      {lastRefresh && (
        <div className="exec-mobile-footer">
          Last updated: {lastRefresh.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
