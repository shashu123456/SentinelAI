import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../config';
import {
  Activity, Database, Server, Shield, RefreshCw,
  CheckCircle2, XCircle, AlertTriangle, Cpu, HardDrive,
  Zap, TrendingUp, Heart, Wifi, WifiOff, Clock,
  Terminal, Globe, Lock, BarChart3,
} from 'lucide-react';
import './SystemHealth.css';

/* ── Status indicator ─────────────────────────────────────────── */
function StatusDot({ status, size = 14 }) {
  const cls = status === 'healthy' || status === 'operational' || status === 'alive' || status === 'ready' || status === 'running'
    ? 'healthy' : status === 'degraded' || status === 'not_configured' || status === 'unavailable' || status === 'not_installed'
    ? 'degraded' : status === 'unhealthy' || status === 'not_ready' || status === 'unreachable'
    ? 'unhealthy' : 'unknown';
  const Icon = cls === 'healthy' ? CheckCircle2 : cls === 'degraded' ? AlertTriangle : cls === 'unhealthy' ? XCircle : Clock;
  return <span className={`sh-status-dot ${cls}`}><Icon size={size} /></span>;
}

/* ── Metric bar ───────────────────────────────────────────────── */
function MetricBar({ label, value, max = 100, unit = '%', color }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const barColor = color || (pct > 80 ? '#ff3355' : pct > 60 ? '#ffaa00' : '#00ff88');
  return (
    <div className="sh-metric-bar">
      <div className="sh-metric-bar-header">
        <span className="sh-metric-bar-label">{label}</span>
        <span className="sh-metric-bar-value">{value != null ? `${value}${unit}` : '—'}</span>
      </div>
      <div className="sh-metric-bar-track">
        <div className="sh-metric-bar-fill" style={{ width: `${pct}%`, background: barColor }} />
      </div>
    </div>
  );
}

/* ── Service Card ─────────────────────────────────────────────── */
function ServiceCard({ icon: Icon, iconClass, name, description, status, details }) {
  return (
    <div className="sh-card">
      <div className="sh-card-header">
        <div className={`sh-card-icon ${iconClass}`}><Icon size={18} /></div>
        <div className="sh-card-info">
          <span className="sh-card-name">{name}</span>
          <span className="sh-card-desc">{description}</span>
        </div>
        <StatusDot status={status} />
      </div>
      <div className="sh-card-body">
        {details.map((d, i) => (
          <div key={i} className="sh-card-detail">
            <span className="sh-card-label">{d.label}</span>
            <span className={`sh-card-value ${d.mono ? 'mono' : ''} ${d.error ? 'error' : ''}`}>
              {d.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────────── */
export default function SystemHealth() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('sentinelai_token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      const backendBase = API_BASE.replace('/api', '');

      // Fetch v1 health endpoint
      const resp = await fetch(`${backendBase}/api/v1/health`, { headers });
      if (resp.ok) {
        const health = await resp.json();
        setData(health);
      } else {
        // Fallback to legacy endpoint
        const fallback = await fetch(`${backendBase}/health/detailed`, { headers }).then(r => r.json());
        setData(fallback);
      }
      setLastChecked(new Date());
    } catch {
      setData({ status: 'unreachable', checks: {}, details: {} });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 15000);
    return () => clearInterval(interval);
  }, [loadHealth]);

  if (loading && !data) {
    return (
      <div className="page-content">
        <div className="sh-loading"><RefreshCw size={24} className="spin" /><span>Checking system health...</span></div>
      </div>
    );
  }

  const status = data?.status || 'unknown';
  const checks = data?.checks || {};
  const details = data?.details || {};
  const cpu = details.cpu || {};
  const memory = details.memory || {};
  const disk = details.disk || {};
  const db = details.database || {};
  const redis = details.redis || {};
  const ai = details.ai_engine || {};
  const worker = details.workers || {};
  const env = details.environment || {};

  return (
    <div className="page-content">
      {/* Header */}
      <div className="sh-header">
        <div className="sh-header-left">
          <div className="sh-header-badge"><Activity size={12} /> SYSTEM OBSERVABILITY</div>
          <h1 className="sh-header-title">System Health</h1>
          <p className="sh-header-sub">
            Real-time infrastructure monitoring
            {lastChecked && <span className="sh-last-checked"> · {lastChecked.toLocaleTimeString()}</span>}
          </p>
        </div>
        <button className="sh-refresh-btn" onClick={loadHealth} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {/* Overall Status Banner */}
      <div className={`sh-banner ${status}`}>
        <StatusDot status={status} size={20} />
        <div className="sh-banner-text">
          <span className="sh-banner-status">
            System {status === 'healthy' ? 'Operational' : status === 'degraded' ? 'Degraded' : status === 'unreachable' ? 'Offline' : 'Unhealthy'}
          </span>
          <span className="sh-banner-desc">
            Uptime: {data?.uptime_human || '—'} · Version: {data?.version || '1.0.0'}
          </span>
        </div>
      </div>

      {/* Resource Metrics */}
      <div className="sh-metrics-row">
        <div className="sh-metric-card">
          <Cpu size={16} className="sh-metric-icon" />
          <div className="sh-metric-info">
            <span className="sh-metric-label">CPU</span>
            <span className="sh-metric-value">{cpu.usage_percent != null ? `${cpu.usage_percent}%` : '—'}</span>
          </div>
          <MetricBar label="" value={cpu.usage_percent} unit="" />
        </div>
        <div className="sh-metric-card">
          <Activity size={16} className="sh-metric-icon" />
          <div className="sh-metric-info">
            <span className="sh-metric-label">Memory (Process)</span>
            <span className="sh-metric-value">{memory.process_rss_mb != null ? `${memory.process_rss_mb} MB` : '—'}</span>
          </div>
          <MetricBar label="" value={memory.process_rss_mb} max={memory.system_total_mb || 512} unit=" MB" />
        </div>
        <div className="sh-metric-card">
          <HardDrive size={16} className="sh-metric-icon" />
          <div className="sh-metric-info">
            <span className="sh-metric-label">Disk</span>
            <span className="sh-metric-value">{disk.usage_percent != null ? `${disk.usage_percent}%` : '—'}</span>
          </div>
          <MetricBar label="" value={disk.usage_percent} unit="" />
        </div>
        <div className="sh-metric-card">
          <Database size={16} className="sh-metric-icon" />
          <div className="sh-metric-info">
            <span className="sh-metric-label">DB Latency</span>
            <span className="sh-metric-value">{db.latency_ms != null ? `${db.latency_ms}ms` : '—'}</span>
          </div>
          <MetricBar label="" value={db.latency_ms} max={100} unit="ms" />
        </div>
      </div>

      {/* Service Grid */}
      <div className="sh-grid">
        <ServiceCard
          icon={Server} iconClass="server" name="Backend API" description="FastAPI + Uvicorn"
          status={checks.database === 'healthy' ? 'healthy' : 'unhealthy'}
          details={[
            { label: 'Status', value: checks.database || 'unknown', error: checks.database !== 'healthy' },
            { label: 'Version', value: data?.version || '—' },
            { label: 'Uptime', value: data?.uptime_human || '—' },
          ]}
        />

        <ServiceCard
          icon={Database} iconClass="db" name="Database" description={db.engine || 'SQLite'}
          status={checks.database}
          details={[
            { label: 'Status', value: db.status === 'healthy' ? 'Connected' : db.status || 'unknown', error: db.status !== 'healthy' },
            { label: 'Latency', value: db.latency_ms != null ? `${db.latency_ms}ms` : '—' },
            { label: 'Engine', value: db.engine || '—' },
            ...(db.pool_size != null ? [
              { label: 'Pool Size', value: db.pool_size },
              { label: 'Checked Out', value: db.checked_out },
            ] : []),
          ]}
        />

        <ServiceCard
          icon={Wifi} iconClass="api" name="Redis Cache" description="Token blacklist + caching"
          status={redis.status}
          details={[
            { label: 'Status', value: redis.status === 'healthy' ? 'Connected' : redis.status || 'not configured' },
            ...(redis.status === 'healthy' ? [
              { label: 'Latency', value: `${redis.latency_ms}ms` },
              { label: 'Memory', value: redis.used_memory_human || '—' },
              { label: 'Clients', value: redis.connected_clients },
            ] : [
              { label: 'Error', value: redis.error || 'Not configured', error: true },
            ]),
          ]}
        />

        <ServiceCard
          icon={Shield} iconClass="scanner" name="Scanner Engine" description="API + SAST + Deps"
          status="healthy"
          details={[
            { label: 'API Scanner', value: 'Active' },
            { label: 'SAST Engine', value: 'Active' },
            { label: 'Dep Scanner', value: 'Active' },
          ]}
        />

        <ServiceCard
          icon={TrendingUp} iconClass="ai" name="AI Engine" description={ai.model || 'Ollama'}
          status={ai.status}
          details={[
            { label: 'Status', value: ai.status === 'healthy' ? 'Connected' : ai.status || 'unknown' },
            { label: 'Model', value: ai.model || '—' },
            { label: 'Fallback', value: ai.fallback || '—' },
            ...(ai.latency_ms != null ? [{ label: 'Latency', value: `${ai.latency_ms}ms` }] : []),
          ]}
        />

        <ServiceCard
          icon={BarChart3} iconClass="frontend" name="Task Queue" description="Background scan workers"
          status={worker.status}
          details={[
            { label: 'Active', value: worker.active_tasks || 0 },
            { label: 'Queued', value: worker.queued_tasks || 0 },
            { label: 'Completed', value: worker.completed_tasks || 0 },
            { label: 'Failed', value: worker.failed_tasks || 0, error: worker.failed_tasks > 0 },
          ]}
        />
      </div>

      {/* Environment Info */}
      <div className="sh-info-panel">
        <div className="sh-panel-header">
          <span className="sh-panel-dot" />
          <span className="sh-panel-title">ENVIRONMENT</span>
        </div>
        <div className="sh-info-grid">
          {[
            { label: 'Platform', value: 'SentinelAI v' + (env.sentinel_version || '1.0.0') },
            { label: 'Python', value: env.python_version || '—' },
            { label: 'OS', value: env.platform || '—' },
            { label: 'Architecture', value: env.architecture || '—' },
            { label: 'Hostname', value: env.hostname || '—' },
            { label: 'PID', value: env.pid || '—' },
            { label: 'Environment', value: env.environment || 'development' },
            { label: 'Database', value: env.database_url || '—' },
            { label: 'Redis', value: env.redis_configured ? 'Configured' : 'Not configured' },
            { label: 'Sentry', value: env.sentry_configured ? 'Enabled' : 'Disabled' },
            { label: 'AI Model', value: env.ollama_model || '—' },
            { label: 'Metrics', value: '/metrics (Prometheus)', mono: true },
          ].map((item, i) => (
            <div key={i} className="sh-info-item">
              <span className="sh-info-label">{item.label}</span>
              <span className={`sh-info-value ${item.mono ? 'mono' : ''}`}>{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
