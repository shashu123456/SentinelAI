import { useState, useEffect } from 'react';
import { Webhook, AlertTriangle, Bell, Globe, Mail, MessageSquare, Building2, RefreshCw } from 'lucide-react';
import { SkeletonTable } from '../components/Skeleton';
import { useOrg } from '../context/OrgContext';
import { enterprise } from '../services/enterprise';

const TYPE_ICONS = { slack: MessageSquare, teams: Globe, discord: MessageSquare, email: Mail, custom: Webhook };
const TYPE_COLORS = { slack: 'var(--accent-green)', teams: 'var(--accent-blue)', discord: 'var(--accent-purple)', email: 'var(--accent-orange)', custom: 'var(--accent-cyan)' };

export default function WebhooksPage() {
  const { currentOrg } = useOrg();
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!currentOrg?.id) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    enterprise.webhooks(currentOrg.id)
      .then((data) => {
        if (!cancelled) setWebhooks(data?.items || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [currentOrg?.id, reloadKey]);

  if (loading) return <div className="page-content"><SkeletonTable rows={3} cols={4} /></div>;

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Webhooks</h1>
          <p className="dash-hero-sub">Send security notifications to Slack, Teams, Discord, Email, and more</p>
        </div>
        <button className="btn-outline btn-sm" onClick={() => setReloadKey((k) => k + 1)} disabled={!currentOrg?.id}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner" style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {!error && !currentOrg?.id && (
        <div className="empty-state">
          <div className="empty-state-icon"><Building2 size={24} /></div>
          <div className="empty-state-title">No Organization Selected</div>
          <div className="empty-state-desc">Webhooks are scoped to an organization.</div>
        </div>
      )}

      {!error && currentOrg?.id && webhooks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><Bell size={24} /></div>
          <div className="empty-state-title">No Webhooks Configured</div>
          <div className="empty-state-desc">Connect your security notifications to the tools your team uses every day.</div>
        </div>
      ) : (
        <div className="dash-panel" style={{ marginTop: 20 }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">WEBHOOKS</span>
          </div>
          <div>
            {webhooks.map(wh => {
              const Icon = TYPE_ICONS[wh.webhook_type] || Webhook;
              const color = TYPE_COLORS[wh.webhook_type] || 'var(--accent-cyan)';
              return (
                <div key={wh.id} className="dash-scan-item">
                  <div className="dash-scan-left">
                    <div style={{ width: 36, height: 36, borderRadius: 8, background: `${color}11`, border: `1px solid ${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color, flexShrink: 0 }}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <div className="dash-scan-name">{wh.name}</div>
                      <div className="dash-scan-meta">
                        <span style={{ textTransform: 'capitalize' }}>{wh.webhook_type}</span>
                        <span>{wh.events?.length || 0} events</span>
                        <span>{wh.delivery_count} deliveries</span>
                      </div>
                    </div>
                  </div>
                  <div className="dash-scan-right">
                    <span className={`sev-badge ${wh.is_active ? 'low' : 'info'}`}>{wh.is_active ? 'Active' : 'Disabled'}</span>
                    {wh.failure_count > 0 && (
                      <span className="sev-badge medium">{wh.failure_count} failures</span>
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
