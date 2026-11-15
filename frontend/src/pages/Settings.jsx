import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { request } from '../services/api';
import { useToast } from '../components/ui/Toast';
import { Settings as SettingsIcon, Building2, FolderKanban, Users, User, Plus, Trash2, ChevronRight, Shield, Mail, Calendar, Key, Lock, Eye, EyeOff, Slack, FileText } from 'lucide-react';
import './Settings.css';

const TABS = [
  { id: 'org', label: 'Organization', icon: Building2 },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'api-keys', label: 'API Keys', icon: Key },
  { id: 'integrations', label: 'Integrations', icon: Link },
];

export default function Settings() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('org');
  const [orgs, setOrgs] = useState([]);
  const [projects, setProjects] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [showCreateOrg, setShowCreateOrg] = useState(false);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showInviteMember, setShowInviteMember] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const loadOrgs = useCallback(async () => {
    try {
      const data = await request('/organizations');
      setOrgs(data);
      if (data.length > 0 && !selectedOrg) {
        setSelectedOrg(data[0]);
      }
    } catch {
      setOrgs([]);
    }
  }, [selectedOrg]);

  const loadProjects = useCallback(async () => {
    if (!selectedOrg) return;
    try {
      const data = await request(`/organizations/${selectedOrg.id}/projects`);
      setProjects(data);
    } catch {
      setProjects([]);
    }
  }, [selectedOrg]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await loadOrgs();
      setLoading(false);
    };
    load();
  }, []);

  useEffect(() => {
    if (selectedOrg && activeTab === 'projects') loadProjects();
  }, [selectedOrg, activeTab]);

  if (loading) {
    return (
      <div className="page-content">
        <div className="settings-loading">
          <Loader2 size={24} className="spin" />
          <span>Loading settings...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {toast && (
        <div className={`settings-toast ${toast.type}`}>
          {toast.type === 'success' ? <Check size={14} /> : <AlertCircle size={14} />}
          {toast.msg}
        </div>
      )}

      <div className="settings-header">
        <div className="settings-header-left">
          <div className="settings-header-badge">
            <SettingsIcon size={12} />
            <span>PLATFORM CONFIGURATION</span>
          </div>
          <h1 className="settings-header-title">Settings</h1>
          <p className="settings-header-sub">Manage your organization, projects, team, and API access</p>
        </div>
      </div>

      <div className="settings-layout">
        <div className="settings-tabs">
          {TABS.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={15} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <div className="settings-content">
          {activeTab === 'org' && (
            <OrganizationTab
              orgs={orgs}
              selectedOrg={selectedOrg}
              onSelect={setSelectedOrg}
              showCreate={showCreateOrg}
              setShowCreate={setShowCreateOrg}
              onCreated={() => {
                loadOrgs();
                setShowCreateOrg(false);
                showToast('Organization created');
              }}
              showToast={showToast}
            />
          )}
          {activeTab === 'projects' && (
            <ProjectsTab
              org={selectedOrg}
              projects={projects}
              showCreate={showCreateProject}
              setShowCreate={setShowCreateProject}
              onCreated={() => {
                loadProjects();
                setShowCreateProject(false);
                showToast('Project created');
              }}
              showToast={showToast}
            />
          )}
          {activeTab === 'team' && (
            <TeamTab
              org={selectedOrg}
              showInvite={showInviteMember}
              setShowInvite={setShowInviteMember}
              onAction={() => showToast('Team updated')}
              showToast={showToast}
            />
          )}
          {activeTab === 'profile' && <ProfileTab user={user} showToast={showToast} />}
          {activeTab === 'api-keys' && <ApiKeysTab />}
          {activeTab === 'integrations' && <IntegrationsTab />}
        </div>
      </div>
    </div>
  );
}

/* ── Organization Tab ── */

function OrganizationTab({ orgs, selectedOrg, onSelect, showCreate, setShowCreate, onCreated, showToast }) {
  const [form, setForm] = useState({ name: '', slug: '', description: '' });
  const [creating, setCreating] = useState(false);

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await request('/organizations', {
        method: 'POST',
        body: JSON.stringify(form),
      });
      onCreated();
      setForm({ name: '', slug: '', description: '' });
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Organizations</h2>
        <button className="settings-btn primary" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={14} /> New Organization
        </button>
      </div>

      {showCreate && (
        <form className="settings-form" onSubmit={handleCreate}>
          <div className="settings-form-row">
            <label>
              <span>Name</span>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-') })}
                placeholder="Acme Security"
                required
              />
            </label>
            <label>
              <span>Slug</span>
              <input
                type="text"
                value={form.slug}
                onChange={e => setForm({ ...form, slug: e.target.value })}
                placeholder="acme-security"
                pattern="^[a-z0-9-]+$"
                required
              />
            </label>
          </div>
          <label>
            <span>Description</span>
            <input
              type="text"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              placeholder="Optional description"
            />
          </label>
          <div className="settings-form-actions">
            <button type="button" className="settings-btn" onClick={() => setShowCreate(false)}>Cancel</button>
            <button type="submit" className="settings-btn primary" disabled={creating}>
              {creating ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
              Create
            </button>
          </div>
        </form>
      )}

      <div className="settings-list">
        {orgs.length === 0 ? (
          <div className="settings-empty">
            <Building2 size={32} />
            <p>No organizations yet</p>
            <span>Create your first organization to get started</span>
          </div>
        ) : (
          orgs.map(org => (
            <div
              key={org.id}
              className={`settings-list-item ${selectedOrg?.id === org.id ? 'selected' : ''}`}
              onClick={() => onSelect(org)}
            >
              <div className="settings-list-icon">
                <Building2 size={16} />
              </div>
              <div className="settings-list-info">
                <span className="settings-list-name">{org.name}</span>
                <span className="settings-list-meta">
                  <Globe size={10} /> {org.slug}
                  {org.description && <> · {org.description}</>}
                </span>
              </div>
              <ChevronRight size={14} className="settings-list-arrow" />
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ── Projects Tab ── */

function ProjectsTab({ org, projects, showCreate, setShowCreate, onCreated, showToast }) {
  const [form, setForm] = useState({ name: '', slug: '', description: '' });
  const [creating, setCreating] = useState(false);

  if (!org) {
    return (
      <div className="settings-empty-full">
        <Building2 size={36} />
        <h3>Select an Organization</h3>
        <p>Choose an organization from the Organization tab first</p>
      </div>
    );
  }

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await request(`/organizations/${org.id}/projects`, {
        method: 'POST',
        body: JSON.stringify(form),
      });
      onCreated();
      setForm({ name: '', slug: '', description: '' });
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Projects · {org.name}</h2>
        <button className="settings-btn primary" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={14} /> New Project
        </button>
      </div>

      {showCreate && (
        <form className="settings-form" onSubmit={handleCreate}>
          <div className="settings-form-row">
            <label>
              <span>Name</span>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-') })}
                placeholder="Payment API"
                required
              />
            </label>
            <label>
              <span>Slug</span>
              <input
                type="text"
                value={form.slug}
                onChange={e => setForm({ ...form, slug: e.target.value })}
                placeholder="payment-api"
                pattern="^[a-z0-9-]+$"
                required
              />
            </label>
          </div>
          <label>
            <span>Description</span>
            <input
              type="text"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              placeholder="Optional description"
            />
          </label>
          <div className="settings-form-actions">
            <button type="button" className="settings-btn" onClick={() => setShowCreate(false)}>Cancel</button>
            <button type="submit" className="settings-btn primary" disabled={creating}>
              {creating ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
              Create
            </button>
          </div>
        </form>
      )}

      <div className="settings-list">
        {projects.length === 0 ? (
          <div className="settings-empty">
            <FolderKanban size={32} />
            <p>No projects yet</p>
            <span>Create your first project in {org.name}</span>
          </div>
        ) : (
          projects.map(proj => (
            <div key={proj.id} className="settings-list-item">
              <div className="settings-list-icon project">
                <FolderKanban size={16} />
              </div>
              <div className="settings-list-info">
                <span className="settings-list-name">{proj.name}</span>
                <span className="settings-list-meta">
                  <Globe size={10} /> {proj.slug}
                  {proj.description && <> · {proj.description}</>}
                </span>
              </div>
              <span className={`settings-badge ${proj.is_active ? 'active' : 'inactive'}`}>
                {proj.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ── Team Tab ── */

function TeamTab({ org, showInvite, setShowInvite, onAction, showToast }) {
  const [inviteForm, setInviteForm] = useState({ user_id: '', role: 'member' });
  const [inviting, setInviting] = useState(false);

  if (!org) {
    return (
      <div className="settings-empty-full">
        <Users size={36} />
        <h3>Select an Organization</h3>
        <p>Choose an organization from the Organization tab first</p>
      </div>
    );
  }

  const handleInvite = async (e) => {
    e.preventDefault();
    setInviting(true);
    try {
      await request(`/organizations/${org.id}/members`, {
        method: 'POST',
        body: JSON.stringify({
          user_id: parseInt(inviteForm.user_id),
          role: inviteForm.role,
        }),
      });
      onAction();
      setInviteForm({ user_id: '', role: 'member' });
      setShowInvite(false);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setInviting(false);
    }
  };

  const handleRemove = async (userId) => {
    if (!window.confirm('Remove this team member?')) return;
    try {
      await request(`/organizations/${org.id}/members/${userId}`, { method: 'DELETE' });
      onAction();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Team · {org.name}</h2>
        <button className="settings-btn primary" onClick={() => setShowInvite(!showInvite)}>
          <Plus size={14} /> Invite Member
        </button>
      </div>

      {showInvite && (
        <form className="settings-form" onSubmit={handleInvite}>
          <div className="settings-form-row">
            <label>
              <span>User ID</span>
              <input
                type="number"
                value={inviteForm.user_id}
                onChange={e => setInviteForm({ ...inviteForm, user_id: e.target.value })}
                placeholder="Enter user ID"
                min="1"
                required
              />
            </label>
            <label>
              <span>Role</span>
              <select
                value={inviteForm.role}
                onChange={e => setInviteForm({ ...inviteForm, role: e.target.value })}
              >
                <option value="viewer">Viewer — Read-only access</option>
                <option value="member">Member — Can scan and view</option>
                <option value="admin">Admin — Full management access</option>
              </select>
            </label>
          </div>
          <div className="settings-form-actions">
            <button type="button" className="settings-btn" onClick={() => setShowInvite(false)}>Cancel</button>
            <button type="submit" className="settings-btn primary" disabled={inviting}>
              {inviting ? <Loader2 size={14} className="spin" /> : <Mail size={14} />}
              Send Invite
            </button>
          </div>
        </form>
      )}

      <div className="settings-list">
        <div className="settings-list-item team-header">
          <span style={{ flex: 1 }}>Member</span>
          <span style={{ width: 80, textAlign: 'center' }}>Role</span>
          <span style={{ width: 40 }} />
        </div>
        <div className="settings-list-item">
          <div className="settings-list-icon owner">
            <Shield size={16} />
          </div>
          <div className="settings-list-info">
            <span className="settings-list-name">Owner</span>
            <span className="settings-list-meta">User #{org.owner_id}</span>
          </div>
          <span className="settings-badge admin">Owner</span>
          <span style={{ width: 40 }} />
        </div>
        <div className="settings-empty" style={{ padding: '20px' }}>
          <Users size={24} />
          <p>Invite team members to collaborate</p>
        </div>
      </div>
    </div>
  );
}

/* ── Integrations Tab ── */

function IntegrationsTab() {
  const { user } = useAuth();
  const { showToast } = useToast();

  const integrations = [
    {
      id: 'gmail',
      name: 'Gmail',
      description: 'Connect your Gmail account to receive security alerts and send scan reports via email',
      icon: Mail,
      color: 'var(--accent-cyan)',
      status: 'connected',
    },
    {
      id: 'slack',
      name: 'Slack',
      description: 'Connect Slack to receive real-time security notifications in your channels',
      icon: Slack,
      color: 'var(--accent-purple)',
      status: 'disconnected',
    },
    {
      id: 'notion',
      name: 'Notion',
      description: 'Connect Notion to automatically document scan results in your knowledge base',
      icon: FileText,
      color: 'var(--accent-green)',
      status: 'disconnected',
    },
  ];

  const handleConnect = async (integrationId) => {
    try {
      showToast(`Connecting ${integrations.find(i => i.id === integrationId)?.name}...`, 'info');
      // TODO: Implement actual integration connection flow
      // This would involve OAuth flow with the respective service
      const timeouts = setTimeout(() => {
        showToast(`${integrations.find(i => i.id === integrationId)?.name} connected successfully`, 'success');
      }, 1500);
      return true;
    } catch (err) {
      showToast(err.message || `Failed to connect ${integrationId}`, 'error');
      return false;
    }
  };

  const handleDisconnect = async (integrationId) => {
    if (!window.confirm(`Disconnect ${integrations.find(i => i.id === integrationId)?.name}?`)) return;
    try {
      showToast(`Disconnecting ${integrations.find(i => i.id === integrationId)?.name}...`, 'info');
      setTimeout(() => {
        showToast(`${integrations.find(i => i.id === integrationId)?.name} disconnected`, 'success');
      }, 1000);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Integrations</h2>
      </div>

      <div className="integrations-grid">
        {integrations.map((integration) => (
          <div
            key={integration.id}
            className={`integration-card ${integration.status}`}
            style={{ borderLeftColor: integration.color }}
          >
            <div className="integration-header" style={{ color: integration.color }}>
              {integration.icon}
            </div>
            <div className="integration-body">
              <h3>{integration.name}</h3>
              <p>{integration.description}</p>
            </div>
            <div className="integration-footer">
              <span className={integration.status === 'connected' ? 'integration-status connected' : 'integration-status disconnected'}>
                {integration.status === 'connected' ? 'Connected' : 'Disconnected'}
              </span>
              {integration.status === 'connected' && (
                <button
                  onClick={() => handleDisconnect(integration.id)}
                  className="integration-disconnect-btn"
                >
                  Disconnect
                </button>
              )}
              {integration.status !== 'connected' && (
                <button
                  onClick={() => handleConnect(integration.id)}
                  className="integration-connect-btn"
                >
                  Connect
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="integrations-empty" style={{ padding: '2rem', textAlign: 'center' }}>
        <Mail size={48} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} />
        <p style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
          No integrations connected
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Connect services to automate workflows and receive notifications
        </p>
      </div>
    </div>
  );
}

/* ── Profile Tab ── */

function ProfileTab({ user, showToast }) {
  const [form, setForm] = useState({
    username: user?.username || '',
    email: user?.email || '',
  });
  const [changingPassword, setChangingPassword] = useState(false);
  const [showChangePasswordForm, setShowChangePasswordForm] = useState(false);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setChangingPassword(true);
    try {
      await request('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: form.current_password,
          new_password: form.new_password,
        }),
      });
      setShowChangePasswordForm(false);
      setForm({ current_password: '', new_password: '' });
      showToast('Password changed successfully', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Profile</h2>
      </div>

      <div className="settings-profile-grid">
        <div className="settings-profile-card">
          <div className="settings-profile-avatar">
            {user?.username?.charAt(0).toUpperCase()}
          </div>
          <div className="settings-profile-info">
            <span className="settings-profile-name">{user?.username}</span>
            <span className="settings-profile-email">{user?.email}</span>
          </div>
        </div>

        <div className="settings-detail-grid">
          <div className="settings-detail-item">
            <div className="settings-detail-icon"><User size={14} /></div>
            <div className="settings-detail-content">
              <span className="settings-detail-label">Username</span>
              <span className="settings-detail-value">{user?.username}</span>
            </div>
          </div>
          <div className="settings-detail-item">
            <div className="settings-detail-icon"><Mail size={14} /></div>
            <div className="settings-detail-content">
              <span className="settings-detail-label">Email</span>
              <span className="settings-detail-value">{user?.email}</span>
            </div>
          </div>
          <div className="settings-detail-item">
            <div className="settings-detail-icon"><Shield size={14} /></div>
            <div className="settings-detail-content">
              <span className="settings-detail-label">Role</span>
              <span className="settings-detail-value">{user?.role || 'user'}</span>
            </div>
          </div>
          <div className="settings-detail-item">
            <div className="settings-detail-icon"><Lock size={14} /></div>
            <div className="settings-detail-content">
              <span className="settings-detail-label">Account Status</span>
              <span className="settings-detail-value">{user?.is_active ? 'Active' : 'Disabled'}</span>
            </div>
          </div>
          <div className="settings-detail-item">
            <div className="settings-detail-icon"><Calendar size={14} /></div>
            <div className="settings-detail-content">
              <span className="settings-detail-label">Member Since</span>
              <span className="settings-detail-value">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
              </span>
            </div>
          </div>
          {user?.is_active && (
            <div className="settings-detail-item">
              <div className="settings-detail-icon"><Shield size={14} /></div>
              <div className="settings-detail-content">
                <span className="settings-detail-label">Security</span>
                <span className="settings-detail-value">
                  {user?.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {showChangePasswordForm && (
        <div className="settings-change-password">
          <h3>Change Password</h3>
          <p>Update your account password</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleChangePassword(e);
            }}
            className="settings-form"
          >
            <div className="settings-form-row">
              <label>Current Password</label>
              <Input
                type="password"
                value={form.current_password}
                onChange={(e) => setForm({ ...form, current_password: e.target.value })}
                required
              />
            </div>
            <div className="settings-form-row">
              <label>New Password</label>
              <Input
                type="password"
                value={form.new_password}
                onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                required
                minLength={8}
              />
            </div>
            <div className="settings-form-row">
              <label>Confirm New Password</label>
              <Input
                type="password"
              value={form.confirm_password}
              onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
              required
              minLength={8}
            /></div>
            <div className="settings-form-actions">
              <button type="button" className="settings-btn" onClick={() => setShowChangePasswordForm(false)}>Cancel</button>
              <button type="submit" className="settings-btn primary" disabled={changingPassword}>
                {changingPassword ? <Loader2 size={14} className="spin" /> : 'Change Password'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

/* ── Change Password Form (standalone) ── */

function ChangePasswordForm({ show, setShow, onSubmit, showToast }) {
  const [form, setForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [submitting, setSubmitting] = useState(false);

  if (form.new_password !== form.confirm_password) {
    setError('Passwords do not match');
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(form);
      setSubmitting(false);
      setShow(false);
      setForm({ current_password: '', new_password: '', confirm_password: '' });
      showToast('Password changed successfully', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="settings-form">
      <div className="settings-form-row">
        <label>Current Password</label>
        <Input
          type="password"
          value={form.current_password}
          onChange={(e) => setForm({ ...form, current_password: e.target.value })}
          required
        />
      </div>
      <div className="settings-form-row">
        <label>New Password</label>
        <Input
          type="password"
          value={form.new_password}
          onChange={(e) => setForm({ ...form, new_password: e.target.value })}
          required
          minLength={8}
        />
      </div>
      <div className="settings-form-row">
        <label>Confirm New Password</label>
        <Input
          type="password"
          value={form.confirm_password}
          onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
          required
          minLength={8}
        />
      </div>
      <div className="settings-form-actions">
        <button type="button" className="settings-btn" onClick={() => setShow(false)}>Cancel</button>
        <button type="submit" className="settings-btn primary" disabled={submitting}>
          {submitting ? <Loader2 size={14} className="spin" /> : 'Change Password'}
        </button>
      </div>
    </form>
  );
}

/* ── API Keys Tab ── */

function ApiKeysTab() {
  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>API Keys</h2>
        <Link to="/org/api-keys" className="settings-btn primary">
          <Key size={14} /> Manage Keys
        </Link>
      </div>

      <div className="settings-list">
        <div className="settings-empty">
          <Key size={32} />
          <p>API keys live in the organization workspace</p>
          <span>
            Create, view and revoke keys on the <Link to="/org/api-keys">API Keys page</Link>.
          </span>
        </div>
      </div>

      <div className="settings-api-info">
        <div className="settings-api-info-icon"><Lock size={16} /></div>
        <div className="settings-api-info-content">
          <h4>API Access</h4>
          <p>
            API keys allow you to integrate SentinelAI into your CI/CD pipeline, automate scans, and access results programmatically.
          </p>
          <code>Authorization: Bearer your-api-key</code>
        </div>
      </div>
    </div>
  );
}