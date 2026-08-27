import { useState, useEffect } from 'react';
import { useOrg } from '../context/OrgContext';
import { invitations } from '../services/api';
import { UserPlus, Send, X, Clock, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import './Dashboard.css';

export default function Invitations() {
  const { currentOrg } = useOrg();
  const [inviteList, setInviteList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSend, setShowSend] = useState(false);
  const [form, setForm] = useState({ email: '', role: 'developer' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (currentOrg) loadData();
  }, [currentOrg]);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await invitations.list(currentOrg.id);
      setInviteList(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await invitations.send(currentOrg.id, form);
      setForm({ email: '', role: 'developer' });
      setShowSend(false);
      setSuccess('Invitation sent successfully');
      loadData();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRevoke = async (inviteId) => {
    if (!window.confirm('Revoke this invitation?')) return;
    try {
      await invitations.revoke(currentOrg.id, inviteId);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCleanup = async () => {
    try {
      const result = await invitations.cleanup(currentOrg.id);
      loadData();
      setSuccess(`Cleaned up ${result.expired_count || 0} expired invitations`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    }
  };

  if (!currentOrg) {
    return (
      <div className="page-content">
        <div className="dash-empty-onboard">
          <div className="dash-empty-icon"><UserPlus size={32} /></div>
          <h4>No Organization Selected</h4>
          <p>Select an organization from the sidebar to manage invitations.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-badge"><UserPlus size={12} /><span>ENTERPRISE INVITATIONS</span></div>
          <h1 className="dash-hero-title">Invitations</h1>
          <p className="dash-hero-sub">Invite new members to {currentOrg.name}</p>
        </div>
        <div className="dash-hero-right">
          <button className="dash-scan-btn" onClick={() => setShowSend(true)}>
            <Send size={14} />
            <span>Send Invitation</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="dash-panel" style={{ borderColor: 'var(--accent-red)', padding: '16px', marginBottom: '16px' }}>
          <p style={{ color: 'var(--accent-red)', margin: 0, fontSize: 13 }}>{error}</p>
          <button onClick={() => setError('')} style={{ marginTop: 8, fontSize: 12, color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}>Dismiss</button>
        </div>
      )}

      {success && (
        <div className="dash-panel" style={{ borderColor: 'var(--accent-green)', padding: '16px', marginBottom: '16px' }}>
          <p style={{ color: 'var(--accent-green)', margin: 0, fontSize: 13 }}>{success}</p>
        </div>
      )}

      {showSend && (
        <div className="dash-panel" style={{ marginBottom: 16, borderColor: 'var(--accent-green)' }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">SEND INVITATION</span>
            <button onClick={() => setShowSend(false)} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}><X size={16} /></button>
          </div>
          <form onSubmit={handleSend} style={{ padding: '0 16px 16px', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input
              type="email"
              placeholder="Email address"
              value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              required
              style={{ flex: 2, minWidth: 200, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <select
              value={form.role}
              onChange={e => setForm({ ...form, role: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            >
              <option value="viewer">Viewer</option>
              <option value="developer">Developer</option>
              <option value="security_engineer">Security Engineer</option>
              <option value="admin">Admin</option>
            </select>
            <button type="submit" className="dash-scan-btn">
              <Send size={14} />
              <span>Send</span>
            </button>
          </form>
        </div>
      )}

      <div className="dash-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">INVITATIONS ({inviteList.length})</span>
          <button
            onClick={handleCleanup}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', fontSize: 11 }}
          >
            Cleanup Expired
          </button>
        </div>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading...</div>
        ) : inviteList.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <Send size={32} style={{ color: 'var(--text-tertiary)', marginBottom: 12 }} />
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>No Invitations</h4>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Send your first invitation to grow your team.</p>
          </div>
        ) : (
          <div className="dash-scan-list">
            {inviteList.map((inv, idx) => (
              <div key={inv.id} className="dash-scan-item">
                <div className="dash-scan-left">
                  <div className="dash-scan-idx">{String(idx + 1).padStart(2, '0')}</div>
                  <div className="dash-scan-info">
                    <span className="dash-scan-name">{inv.email}</span>
                    <div className="dash-scan-meta">
                      <span style={{ textTransform: 'capitalize' }}>{inv.role.replace('_', ' ')}</span>
                      <span>
                        {inv.status === 'pending' && <Clock size={11} />}
                        {inv.status === 'accepted' && <CheckCircle size={11} />}
                        {inv.status === 'revoked' && <XCircle size={11} />}
                        {' '}{inv.status}
                      </span>
                      <span>Expires {new Date(inv.expires_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <div className="dash-scan-right">
                  {inv.status === 'pending' && (
                    <button
                      onClick={() => handleRevoke(inv.id)}
                      style={{ background: 'none', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: 4 }}
                      title="Revoke invitation"
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
