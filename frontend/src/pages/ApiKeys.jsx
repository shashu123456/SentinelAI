import { useState, useEffect } from 'react';
import { useOrg } from '../context/OrgContext';
import { apiKeys } from '../services/api';
import { Key, Plus, Trash2, X, Copy, CheckCircle } from 'lucide-react';
import './Dashboard.css';

export default function ApiKeys() {
  const { currentOrg } = useOrg();
  const [keyList, setKeyList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState(null); // Shown once at creation
  const [form, setForm] = useState({ name: '', scopes: '', expires_days: '' });
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (currentOrg) loadData();
  }, [currentOrg]);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await apiKeys.list(currentOrg.id);
      setKeyList(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const scopes = form.scapes ? form.scopes.split(',').map(s => s.trim()).filter(Boolean) : null;
      const data = await apiKeys.create(currentOrg.id, {
        name: form.name,
        scopes,
        expires_days: form.expires_days ? Number(form.expires_days) : null,
      });
      setNewKey(data);
      setForm({ name: '', scopes: '', expires_days: '' });
      setShowCreate(false);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRevoke = async (keyId) => {
    if (!window.confirm('Revoke this API key? This cannot be undone.')) return;
    try {
      await apiKeys.revoke(currentOrg.id, keyId);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!currentOrg) {
    return (
      <div className="page-content">
        <div className="dash-empty-onboard">
          <div className="dash-empty-icon"><Key size={32} /></div>
          <h4>No Organization Selected</h4>
          <p>Select an organization from the sidebar to manage API keys.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-badge"><Key size={12} /><span>ENTERPRISE API KEYS</span></div>
          <h1 className="dash-hero-title">API Keys</h1>
          <p className="dash-hero-sub">Manage programmatic access to {currentOrg.name}</p>
        </div>
        <div className="dash-hero-right">
          <button className="dash-scan-btn" onClick={() => setShowCreate(true)}>
            <Plus size={14} />
            <span>Create API Key</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="dash-panel" style={{ borderColor: 'var(--accent-red)', padding: '16px', marginBottom: '16px' }}>
          <p style={{ color: 'var(--accent-red)', margin: 0, fontSize: 13 }}>{error}</p>
          <button onClick={() => setError('')} style={{ marginTop: 8, fontSize: 12, color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}>Dismiss</button>
        </div>
      )}

      {/* New Key Display */}
      {newKey && (
        <div className="dash-panel" style={{ marginBottom: 16, borderColor: 'var(--accent-green)' }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" style={{ background: 'var(--accent-green)' }} />
            <span className="dash-panel-title">API KEY CREATED</span>
            <button onClick={() => setNewKey(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}><X size={16} /></button>
          </div>
          <div style={{ padding: '0 16px 16px' }}>
            <p style={{ color: 'var(--accent-yellow)', fontSize: 12, marginBottom: 12 }}>
              ⚠️ Copy this key now. It will not be shown again.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <code style={{
                flex: 1,
                padding: '10px 14px',
                borderRadius: 6,
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--accent-green)',
                fontSize: 12,
                wordBreak: 'break-all',
                fontFamily: 'monospace',
              }}>
                {newKey.raw_key}
              </code>
              <button
                onClick={() => copyToClipboard(newKey.raw_key)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: '1px solid var(--accent-green)',
                  background: 'rgba(0,255,170,0.08)',
                  color: 'var(--accent-green)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 12,
                }}
              >
                {copied ? <CheckCircle size={14} /> : <Copy size={14} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="dash-panel" style={{ marginBottom: 16, borderColor: 'var(--accent-green)' }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">CREATE API KEY</span>
            <button onClick={() => setShowCreate(false)} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}><X size={16} /></button>
          </div>
          <form onSubmit={handleCreate} style={{ padding: '0 16px 16px', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Key name (e.g. CI/CD Pipeline)"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              required
              style={{ flex: 2, minWidth: 200, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <input
              type="text"
              placeholder="Scans, read (comma-separated)"
              value={form.scopes}
              onChange={e => setForm({ ...form, scopes: e.target.value })}
              style={{ flex: 1, minWidth: 180, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <input
              type="number"
              placeholder="Expires in days (optional)"
              value={form.expires_days}
              onChange={e => setForm({ ...form, expires_days: e.target.value })}
              min={1}
              max={365}
              style={{ flex: 1, minWidth: 120, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <button type="submit" className="dash-scan-btn">
              <Plus size={14} />
              <span>Create</span>
            </button>
          </form>
        </div>
      )}

      <div className="dash-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">API KEYS ({keyList.length})</span>
        </div>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading...</div>
        ) : keyList.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <Key size={32} style={{ color: 'var(--text-tertiary)', marginBottom: 12 }} />
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>No API Keys</h4>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Create an API key to enable programmatic access.</p>
          </div>
        ) : (
          <div className="dash-scan-list">
            {keyList.map((key, idx) => (
              <div key={key.id} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div className="dash-scan-idx">{String(idx + 1).padStart(2, '0')}</div>
                  <div className="dash-scan-info">
                    <span className="dash-scan-name">{key.name}</span>
                    <div className="dash-scan-meta">
                      <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{key.key_prefix}...</span>
                      <span style={{ color: key.is_active ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {key.is_active ? 'Active' : 'Revoked'}
                      </span>
                      {key.last_used_at && <span>Last used {new Date(key.last_used_at).toLocaleDateString()}</span>}
                      {key.expires_at && <span>Expires {new Date(key.expires_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                </div>
                <div className="dash-scan-right">
                  {key.is_active && (
                    <button
                      onClick={() => handleRevoke(key.id)}
                      style={{ background: 'none', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: 4 }}
                      title="Revoke API key"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
