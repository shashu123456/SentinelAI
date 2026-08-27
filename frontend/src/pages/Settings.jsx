import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { request } from '../services/api';
import {
  Settings as SettingsIcon, Building2, FolderKanban, Users, User,
  Plus, Trash2, ChevronRight, Shield, Mail, Calendar, Key,
  AlertCircle, Check, X, Loader2, Globe, Lock
} from 'lucide-react';
import './Settings.css';

const TABS = [
  { id: 'org', label: 'Organization', icon: Building2 },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'api-keys', label: 'API Keys', icon: Key },
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
              onCreated={() => { loadOrgs(); setShowCreateOrg(false); showToast('Organization created'); }}
              showToast={showToast}
            />
          )}
          {activeTab === 'projects' && (
            <ProjectsTab
              org={selectedOrg}
              projects={projects}
              showCreate={showCreateProject}
              setShowCreate={setShowCreateProject}
              onCreated={() => { loadProjects(); setShowCreateProject(false); showToast('Project created'); }}
              showToast={showToast}
            />
          )}
          {activeTab === 'team' && (
            <TeamTab
              org={selectedOrg}
              showInvite={showInviteMember}
              setShowInvite={setShowInviteMember}
              onAction={() => { showToast('Team updated'); }}
              showToast={showToast}
            />
          )}
          {activeTab === 'profile' && <ProfileTab user={user} showToast={showToast} />}
          {activeTab === 'api-keys' && <ApiKeysTab showToast={showToast} />}
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

/* ── Profile Tab ── */
function ProfileTab({ user, showToast }) {
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
        </div>
      </div>
    </div>
  );
}

/* ── API Keys Tab ── */
function ApiKeysTab({ showToast }) {
  const [keys, setKeys] = useState([]);

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>API Keys</h2>
        <button className="settings-btn primary" onClick={() => showToast('API key creation coming soon')}>
          <Plus size={14} /> Generate Key
        </button>
      </div>

      <div className="settings-list">
        {keys.length === 0 ? (
          <div className="settings-empty">
            <Key size={32} />
            <p>No API keys</p>
            <span>Generate an API key to access SentinelAI programmatically</span>
          </div>
        ) : null}
      </div>

      <div className="settings-api-info">
        <div className="settings-api-info-icon"><Lock size={16} /></div>
        <div className="settings-api-info-content">
          <h4>API Access</h4>
          <p>API keys allow you to integrate SentinelAI into your CI/CD pipeline, automate scans, and access results programmatically.</p>
          <code>Authorization: Bearer &lt;your-api-key&gt;</code>
        </div>
      </div>
    </div>
  );
}
