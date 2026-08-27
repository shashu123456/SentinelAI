import { useState, useEffect } from 'react';
import { useOrg } from '../context/OrgContext';
import { organizations } from '../services/api';
import { Settings, Shield, Users, CreditCard, Save, CheckCircle } from 'lucide-react';
import './Dashboard.css';

export default function OrgSettings() {
  const { currentOrg, refreshOrgs } = useOrg();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    default_project_visibility: 'private',
    enforce_sso: false,
    allowed_email_domains: '',
  });

  useEffect(() => {
    if (currentOrg) loadSettings();
  }, [currentOrg]);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await organizations.getSettings(currentOrg.id);
      setSettings(data);
      setForm({
        default_project_visibility: data.default_project_visibility || 'private',
        enforce_sso: data.enforce_sso || false,
        allowed_email_domains: (data.allowed_email_domains || []).join(', '),
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const domains = form.allowed_email_domains
        ? form.allowed_email_domains.split(',').map(d => d.trim()).filter(Boolean)
        : [];
      await organizations.updateSettings(currentOrg.id, {
        default_project_visibility: form.default_project_visibility,
        enforce_sso: form.enforce_sso,
        allowed_email_domains: domains.length > 0 ? domains : null,
      });
      setSuccess('Settings saved successfully');
      refreshOrgs();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!currentOrg) {
    return (
      <div className="page-content">
        <div className="dash-empty-onboard">
          <div className="dash-empty-icon"><Settings size={32} /></div>
          <h4>No Organization Selected</h4>
          <p>Select an organization from the sidebar to manage settings.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-badge"><Settings size={12} /><span>ORGANIZATION SETTINGS</span></div>
          <h1 className="dash-hero-title">Organization Settings</h1>
          <p className="dash-hero-sub">Configure {currentOrg.name}</p>
        </div>
      </div>

      {error && (
        <div className="dash-panel" style={{ borderColor: 'var(--accent-red)', padding: '16px', marginBottom: '16px' }}>
          <p style={{ color: 'var(--accent-red)', margin: 0, fontSize: 13 }}>{error}</p>
        </div>
      )}

      {success && (
        <div className="dash-panel" style={{ borderColor: 'var(--accent-green)', padding: '16px', marginBottom: '16px' }}>
          <p style={{ color: 'var(--accent-green)', margin: 0, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle size={14} /> {success}
          </p>
        </div>
      )}

      {/* Subscription Info */}
      <div className="dash-panel" style={{ marginBottom: 16 }}>
        <div className="dash-panel-header">
          <span className="dash-panel-dot" style={{ background: 'var(--accent-blue)' }} />
          <span className="dash-panel-title">SUBSCRIPTION</span>
        </div>
        <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Tier</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent-blue)', textTransform: 'capitalize' }}>
              {currentOrg.subscription_tier}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Members</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
              {currentOrg.scans_used_this_month || 0} / {currentOrg.max_members}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Projects</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
              — / {currentOrg.max_projects}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Scans / Month</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
              {currentOrg.scans_used_this_month || 0} / {currentOrg.max_scans_per_month}
            </div>
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="dash-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">SECURITY SETTINGS</span>
        </div>
        <form onSubmit={handleSave} style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Default Project Visibility
            </label>
            <select
              value={form.default_project_visibility}
              onChange={e => setForm({ ...form, default_project_visibility: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13, width: 200 }}
            >
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={form.enforce_sso}
                onChange={e => setForm({ ...form, enforce_sso: e.target.checked })}
                style={{ width: 16, height: 16 }}
              />
              Enforce Single Sign-On (SSO)
            </label>
            <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
              When enabled, users can only log in through your organization's SSO provider.
            </p>
          </div>

          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Allowed Email Domains
            </label>
            <input
              type="text"
              placeholder="company.com, company.io"
              value={form.allowed_email_domains}
              onChange={e => setForm({ ...form, allowed_email_domains: e.target.value })}
              style={{ width: '100%', maxWidth: 400, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
              Comma-separated. Only users with these email domains can join.
            </p>
          </div>

          <div>
            <button
              type="submit"
              disabled={saving}
              className="dash-scan-btn"
              style={{ opacity: saving ? 0.6 : 1 }}
            >
              <Save size={14} />
              <span>{saving ? 'Saving...' : 'Save Settings'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
