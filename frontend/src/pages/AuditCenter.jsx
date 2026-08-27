import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ClipboardList, Search, Filter, User, Shield, Upload, FileText,
  LogIn, LogOut, Key, Settings, Clock, AlertCircle, CheckCircle2,
  X, Download, ChevronLeft, ChevronRight, RefreshCw, Bot,
  AlertTriangle, Eye, Activity, Database,
} from 'lucide-react';
import { audit } from '../services/api';
import './AuditCenter.css';

/* ── Action configuration ─────────────────────────────────────────── */
const ACTION_CONFIG = {
  'auth.register': { icon: User, color: '#00ff88', label: 'Account Created', risk: 'medium' },
  'auth.login': { icon: LogIn, color: '#00d4ff', label: 'Login', risk: 'medium' },
  'auth.login_failed': { icon: AlertTriangle, color: '#ff3355', label: 'Failed Login', risk: 'high' },
  'auth.logout': { icon: LogOut, color: '#7a9a8e', label: 'Logout', risk: 'info' },
  'auth.logout_all': { icon: LogOut, color: '#ff8800', label: 'Logout All Sessions', risk: 'medium' },
  'auth.password_reset': { icon: Key, color: '#ffaa00', label: 'Password Reset', risk: 'high' },
  'auth.password_change': { icon: Key, color: '#ffaa00', label: 'Password Changed', risk: 'high' },
  'auth.account_locked': { icon: AlertTriangle, color: '#ff3355', label: 'Account Locked', risk: 'high' },
  'auth.account_unlocked': { icon: CheckCircle2, color: '#00ff88', label: 'Account Unlocked', risk: 'high' },
  'scan.started': { icon: Upload, color: '#00ffaa', label: 'Scan Started', risk: 'info' },
  'scan.completed': { icon: CheckCircle2, color: '#00ff88', label: 'Scan Completed', risk: 'medium' },
  'scan.failed': { icon: AlertCircle, color: '#ff3355', label: 'Scan Failed', risk: 'high' },
  'scan.deleted': { icon: AlertCircle, color: '#ff3355', label: 'Scan Deleted', risk: 'high' },
  'report.exported.pdf': { icon: FileText, color: '#aa66ff', label: 'PDF Report Exported', risk: 'medium' },
  'report.exported.json': { icon: FileText, color: '#aa66ff', label: 'JSON Report Exported', risk: 'medium' },
  'org.created': { icon: Shield, color: '#00d4ff', label: 'Organization Created', risk: 'medium' },
  'org.member_added': { icon: User, color: '#00ff88', label: 'Member Added', risk: 'medium' },
  'org.member_removed': { icon: User, color: '#ff3355', label: 'Member Removed', risk: 'high' },
  'settings.updated': { icon: Settings, color: '#7a9a8e', label: 'Settings Updated', risk: 'info' },
  'copilot.chat': { icon: Bot, color: '#aa66ff', label: 'AI Copilot Chat', risk: 'info' },
};

const RISK_COLORS = {
  high: { bg: '#ff335515', border: '#ff335540', text: '#ff5577', dot: '#ff3355' },
  medium: { bg: '#ffaa0015', border: '#ffaa0040', text: '#ffcc44', dot: '#ffaa00' },
  low: { bg: '#00d4ff15', border: '#00d4ff40', text: '#00d4ff', dot: '#00d4ff' },
  info: { bg: '#7a9a8e15', border: '#7a9a8e40', text: '#7a9a8e', dot: '#7a9a8e' },
};

const MODULE_ICONS = {
  authentication: LogIn,
  scanning: Upload,
  organization: Shield,
  reporting: FileText,
  ai_copilot: Bot,
  settings: Settings,
  user_management: User,
  api_keys: Key,
};

const PAGE_SIZE = 50;

/* ── Helpers ──────────────────────────────────────────────────────── */
function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
}

function formatFullTime(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function getActionConfig(action) {
  if (ACTION_CONFIG[action]) return ACTION_CONFIG[action];
  const prefix = action?.split('.')[0];
  if (prefix && MODULE_ICONS[prefix]) {
    return { icon: MODULE_ICONS[prefix] || Clock, color: '#7a9a8e', label: action, risk: 'info' };
  }
  return { icon: Clock, color: '#7a9a8e', label: action, risk: 'info' };
}

/* ── Event Details Drawer ─────────────────────────────────────────── */
function EventDrawer({ event, onClose }) {
  if (!event) return null;
  const config = getActionConfig(event.action);
  const Icon = config.icon;
  const riskStyle = RISK_COLORS[event.risk_level] || RISK_COLORS.info;

  return (
    <div className="audit-drawer-overlay" onClick={onClose}>
      <div className="audit-drawer" onClick={e => e.stopPropagation()}>
        <div className="audit-drawer-header">
          <div className="audit-drawer-title-row">
            <div className="audit-drawer-icon" style={{ color: config.color, background: `${config.color}15`, borderColor: `${config.color}30` }}>
              <Icon size={18} />
            </div>
            <div>
              <h3 className="audit-drawer-title">{config.label}</h3>
              <span className="audit-drawer-time">{formatFullTime(event.created_at)}</span>
            </div>
          </div>
          <button className="audit-drawer-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="audit-drawer-body">
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Event ID</span>
            <span className="audit-drawer-value mono">#{event.id}</span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Action</span>
            <span className="audit-drawer-value mono">{event.action}</span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Module</span>
            <span className="audit-drawer-value">{event.module || '—'}</span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Risk Level</span>
            <span className="audit-drawer-risk" style={{ background: riskStyle.bg, color: riskStyle.text, borderColor: riskStyle.border }}>
              {event.risk_level?.toUpperCase()}
            </span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Status</span>
            <span className={`audit-drawer-status ${event.status === 'failure' ? 'failure' : 'success'}`}>
              {event.status}
            </span>
          </div>

          <div className="audit-drawer-divider" />

          <div className="audit-drawer-field">
            <span className="audit-drawer-label">User</span>
            <span className="audit-drawer-value">{event.username || `User #${event.user_id}`}</span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">IP Address</span>
            <span className="audit-drawer-value mono">{event.ip_address || '—'}</span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">User Agent</span>
            <span className="audit-drawer-value mono small">{event.user_agent || '—'}</span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Request ID</span>
            <span className="audit-drawer-value mono small">{event.request_id || '—'}</span>
          </div>

          <div className="audit-drawer-divider" />

          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Entity</span>
            <span className="audit-drawer-value">
              {event.entity_type && <span className="audit-drawer-entity-badge">{event.entity_type}</span>}
              {event.entity_id && <span className="audit-drawer-entity-id">#{event.entity_id}</span>}
              {!event.entity_type && '—'}
            </span>
          </div>
          <div className="audit-drawer-field">
            <span className="audit-drawer-label">Resource</span>
            <span className="audit-drawer-value">{event.resource || '—'}</span>
          </div>

          {event.detail && Object.keys(event.detail).length > 0 && (
            <>
              <div className="audit-drawer-divider" />
              <div className="audit-drawer-field">
                <span className="audit-drawer-label">Detail</span>
                <pre className="audit-drawer-json">{JSON.stringify(event.detail, null, 2)}</pre>
              </div>
            </>
          )}

          {event.old_value && (
            <div className="audit-drawer-field">
              <span className="audit-drawer-label">Old Value</span>
              <pre className="audit-drawer-json old">{JSON.stringify(event.old_value, null, 2)}</pre>
            </div>
          )}
          {event.new_value && (
            <div className="audit-drawer-field">
              <span className="audit-drawer-label">New Value</span>
              <pre className="audit-drawer-json new">{JSON.stringify(event.new_value, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Main Audit Center ────────────────────────────────────────────── */
export default function AuditCenter() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Filters
  const [search, setSearch] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Drawer
  const [selectedEvent, setSelectedEvent] = useState(null);

  // Available filter values
  const [modules, setModules] = useState([]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (search) params.search = search;
      if (moduleFilter) params.module = moduleFilter;
      if (riskFilter) params.risk_level = riskFilter;
      if (actionFilter) params.action_prefix = actionFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const data = await audit.list(params);
      setEvents(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, moduleFilter, riskFilter, actionFilter, dateFrom, dateTo]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  useEffect(() => {
    audit.modules().then(setModules).catch(() => {});
  }, []);

  // Reset to page 1 when filters change
  useEffect(() => { setPage(1); }, [search, moduleFilter, riskFilter, actionFilter, dateFrom, dateTo]);

  const clearFilters = () => {
    setSearch('');
    setModuleFilter('');
    setRiskFilter('');
    setActionFilter('');
    setDateFrom('');
    setDateTo('');
  };

  const hasFilters = search || moduleFilter || riskFilter || actionFilter || dateFrom || dateTo;

  const handleExport = () => {
    const params = {};
    if (moduleFilter) params.module = moduleFilter;
    if (riskFilter) params.risk_level = riskFilter;
    if (actionFilter) params.action_prefix = actionFilter;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    audit.exportCsv(params);
  };

  // Group events by date
  const groupedEvents = useMemo(() => {
    const groups = {};
    events.forEach(event => {
      const date = event.created_at ? new Date(event.created_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }) : 'Unknown';
      if (!groups[date]) groups[date] = [];
      groups[date].push(event);
    });
    return groups;
  }, [events]);

  return (
    <div className="audit-page">
      {/* Header */}
      <div className="audit-header">
        <div className="audit-header-badge"><ClipboardList size={12} /> ENTERPRISE AUDIT CENTER</div>
        <h1 className="audit-header-title">Security Event Log</h1>
        <p className="audit-header-sub">
          {total > 0 ? `${total.toLocaleString()} events recorded — append-only, immutable` : 'Every action in the platform is logged and auditable'}
        </p>
      </div>

      {/* Toolbar */}
      <div className="audit-toolbar">
        <div className="audit-search-wrap">
          <Search size={15} />
          <input
            className="audit-search"
            placeholder="Search events, users, actions..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && <button className="audit-search-clear" onClick={() => setSearch('')}><X size={14} /></button>}
        </div>

        <button className={`audit-filter-toggle ${showFilters ? 'active' : ''}`} onClick={() => setShowFilters(!showFilters)}>
          <Filter size={14} /> Filters {hasFilters && <span className="audit-filter-count">{[moduleFilter, riskFilter, actionFilter, dateFrom, dateTo].filter(Boolean).length}</span>}
        </button>

        <button className="audit-export-btn" onClick={handleExport} title="Export CSV">
          <Download size={14} /> Export
        </button>

        <button className="audit-refresh-btn" onClick={fetchLogs} title="Refresh">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Advanced Filters */}
      {showFilters && (
        <div className="audit-advanced-filters">
          <div className="audit-filter-row">
            <div className="audit-filter-group">
              <label className="audit-filter-label">Module</label>
              <select className="audit-filter-select" value={moduleFilter} onChange={e => setModuleFilter(e.target.value)}>
                <option value="">All Modules</option>
                {modules.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="audit-filter-group">
              <label className="audit-filter-label">Risk Level</label>
              <select className="audit-filter-select" value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
                <option value="">All Levels</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
              </select>
            </div>
            <div className="audit-filter-group">
              <label className="audit-filter-label">From</label>
              <input type="date" className="audit-filter-date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
            </div>
            <div className="audit-filter-group">
              <label className="audit-filter-label">To</label>
              <input type="date" className="audit-filter-date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
            </div>
          </div>
          {hasFilters && (
            <button className="audit-clear-filters" onClick={clearFilters}>
              <X size={13} /> Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="audit-loading">
          <div className="page-loader-spinner" />
          <p>Loading audit logs...</p>
        </div>
      ) : events.length === 0 ? (
        <div className="audit-empty">
          <ClipboardList size={40} />
          <h3>No audit events{hasFilters ? ' match your filters' : ''}</h3>
          <p>{hasFilters ? 'Try adjusting your filters.' : 'Events will appear here as users interact with the platform.'}</p>
          {hasFilters && <button className="audit-clear-filters" onClick={clearFilters}>Clear filters</button>}
        </div>
      ) : (
        <>
          {/* Event timeline grouped by date */}
          {Object.entries(groupedEvents).map(([date, dayEvents]) => (
            <div key={date} className="audit-date-group">
              <div className="audit-date-header">
                <span className="audit-date-label">{date}</span>
                <span className="audit-date-count">{dayEvents.length} event{dayEvents.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="audit-timeline">
                {dayEvents.map(event => {
                  const config = getActionConfig(event.action);
                  const Icon = config.icon;
                  const riskStyle = RISK_COLORS[event.risk_level] || RISK_COLORS.info;
                  return (
                    <div key={event.id} className="audit-event" onClick={() => setSelectedEvent(event)}>
                      <div className="audit-event-line">
                        <div className="audit-event-dot" style={{ background: riskStyle.dot, boxShadow: `0 0 8px ${riskStyle.dot}40` }} />
                      </div>
                      <div className="audit-event-content">
                        <div className="audit-event-header">
                          <div className="audit-event-icon" style={{ color: config.color, background: `${config.color}10`, borderColor: `${config.color}20` }}>
                            <Icon size={14} />
                          </div>
                          <div className="audit-event-info">
                            <div className="audit-event-title-row">
                              <span className="audit-event-label">{config.label}</span>
                              <span className="audit-event-risk-dot" style={{ background: riskStyle.dot }} title={event.risk_level} />
                            </div>
                            <div className="audit-event-meta">
                              {event.username && <span className="audit-event-user">{event.username}</span>}
                              {event.module && <span className="audit-event-module">{event.module}</span>}
                              <span className="audit-event-time" title={formatFullTime(event.created_at)}>{formatTime(event.created_at)}</span>
                            </div>
                          </div>
                          <Eye size={14} className="audit-event-view-icon" />
                        </div>
                        <div className="audit-event-footer">
                          {event.entity_type && (
                            <span className="audit-event-entity">{event.entity_type}{event.entity_id ? ` #${event.entity_id}` : ''}</span>
                          )}
                          {event.ip_address && (
                            <span className="audit-event-ip">{event.ip_address}</span>
                          )}
                          {event.status === 'failure' && (
                            <span className="audit-event-status-failure">FAILED</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="audit-pagination">
              <button className="audit-page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                <ChevronLeft size={14} /> Previous
              </button>
              <span className="audit-page-info">Page {page} of {totalPages} ({total.toLocaleString()} events)</span>
              <button className="audit-page-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                Next <ChevronRight size={14} />
              </button>
            </div>
          )}
        </>
      )}

      {/* Event Detail Drawer */}
      {selectedEvent && <EventDrawer event={selectedEvent} onClose={() => setSelectedEvent(null)} />}
    </div>
  );
}
