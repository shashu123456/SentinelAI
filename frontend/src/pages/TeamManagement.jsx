import { useState, useEffect } from 'react';
import { useOrg } from '../context/OrgContext';
import { teams, organizations } from '../services/api';
import {
  Users, Plus, Trash2, UserPlus, Shield, X, ChevronRight
} from 'lucide-react';
import './Dashboard.css';

export default function TeamManagement() {
  const { currentOrg } = useOrg();
  const [teamList, setTeamList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [teamDetail, setTeamDetail] = useState(null);
  const [orgMembers, setOrgMembers] = useState([]);
  const [form, setForm] = useState({ name: '', slug: '', description: '' });
  const [addMemberForm, setAddMemberForm] = useState({ user_id: '', role: 'member' });
  const [error, setError] = useState('');

  useEffect(() => {
    if (currentOrg) loadData();
  }, [currentOrg]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [teamsData, membersData] = await Promise.all([
        teams.list(currentOrg.id),
        organizations.listMembers(currentOrg.id).catch(() => []),
      ]);
      setTeamList(teamsData || []);
      setOrgMembers(membersData || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTeamDetail = async (teamId) => {
    try {
      const data = await teams.get(currentOrg.id, teamId);
      setTeamDetail(data);
      setSelectedTeam(teamId);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await teams.create(currentOrg.id, form);
      setForm({ name: '', slug: '', description: '' });
      setShowCreate(false);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    try {
      await teams.addMember(currentOrg.id, selectedTeam, {
        user_id: Number(addMemberForm.user_id),
        role: addMemberForm.role,
      });
      setAddMemberForm({ user_id: '', role: 'member' });
      loadTeamDetail(selectedTeam);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRemoveMember = async (userId) => {
    if (!window.confirm('Remove this team member?')) return;
    try {
      await teams.removeMember(currentOrg.id, selectedTeam, userId);
      loadTeamDetail(selectedTeam);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteTeam = async (teamId) => {
    if (!window.confirm('Delete this team? This cannot be undone.')) return;
    try {
      await teams.delete(currentOrg.id, teamId);
      setSelectedTeam(null);
      setTeamDetail(null);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!currentOrg) {
    return (
      <div className="page-content">
        <div className="dash-empty-onboard">
          <div className="dash-empty-icon"><Users size={32} /></div>
          <h4>No Organization Selected</h4>
          <p>Select an organization from the sidebar to manage teams.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-badge"><Users size={12} /><span>ENTERPRISE TEAMS</span></div>
          <h1 className="dash-hero-title">Team Management</h1>
          <p className="dash-hero-sub">Organize members into teams for {currentOrg.name}</p>
        </div>
        <div className="dash-hero-right">
          <button className="dash-scan-btn" onClick={() => setShowCreate(true)}>
            <Plus size={14} />
            <span>Create Team</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="dash-panel" style={{ borderColor: 'var(--accent-red)', padding: '16px', marginBottom: '16px' }}>
          <p style={{ color: 'var(--accent-red)', margin: 0 }}>{error}</p>
          <button onClick={() => setError('')} style={{ marginTop: 8, fontSize: 12, color: 'var(--text-tertiary)' }}>Dismiss</button>
        </div>
      )}

      {/* Create Team Modal */}
      {showCreate && (
        <div className="dash-panel" style={{ marginBottom: 16, borderColor: 'var(--accent-green)' }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" />
            <span className="dash-panel-title">CREATE TEAM</span>
            <button onClick={() => setShowCreate(false)} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}>
              <X size={16} />
            </button>
          </div>
          <form onSubmit={handleCreate} style={{ padding: '0 16px 16px', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Team name"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              required
              style={{ flex: 1, minWidth: 150, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <input
              type="text"
              placeholder="team-slug"
              value={form.slug}
              onChange={e => setForm({ ...form, slug: e.target.value })}
              required
              pattern="^[a-z0-9-]+$"
              style={{ flex: 1, minWidth: 150, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              style={{ flex: 2, minWidth: 200, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            />
            <button type="submit" className="dash-scan-btn">
              <Plus size={14} />
              <span>Create</span>
            </button>
          </form>
        </div>
      )}

      {/* Teams List */}
      <div className="dash-panel">
        <div className="dash-panel-header">
          <span className="dash-panel-dot" />
          <span className="dash-panel-title">TEAMS ({teamList.length})</span>
        </div>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading teams...</div>
        ) : teamList.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <Users size={32} style={{ color: 'var(--text-tertiary)', marginBottom: 12 }} />
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>No Teams Yet</h4>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Create your first team to organize members by function.</p>
          </div>
        ) : (
          <div className="dash-scan-list">
            {teamList.map((team, idx) => (
              <div
                key={team.id}
                className={`dash-scan-item ${selectedTeam === team.id ? 'active' : ''}`}
                style={{ cursor: 'pointer' }}
                onClick={() => loadTeamDetail(team.id)}
              >
                <div className="dash-scan-left">
                  <div className="dash-scan-idx">{String(idx + 1).padStart(2, '0')}</div>
                  <div className="dash-scan-info">
                    <span className="dash-scan-name">{team.name}</span>
                    <div className="dash-scan-meta">
                      <span><Users size={11} /> {team.member_count} members</span>
                      {team.description && <span>{team.description}</span>}
                    </div>
                  </div>
                </div>
                <div className="dash-scan-right">
                  <ChevronRight size={14} className="dash-action-arrow" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Team Detail */}
      {teamDetail && (
        <div className="dash-panel" style={{ marginTop: 16, borderColor: 'var(--accent-green)' }}>
          <div className="dash-panel-header">
            <span className="dash-panel-dot" style={{ background: 'var(--accent-green)' }} />
            <span className="dash-panel-title">{teamDetail.name}</span>
            <button
              onClick={() => handleDeleteTeam(teamDetail.id)}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: 4 }}
              title="Delete team"
            >
              <Trash2 size={14} />
            </button>
          </div>

          {/* Add Member Form */}
          <form onSubmit={handleAddMember} style={{ padding: '0 16px 12px', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              value={addMemberForm.user_id}
              onChange={e => setAddMemberForm({ ...addMemberForm, user_id: e.target.value })}
              required
              style={{ flex: 1, minWidth: 180, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            >
              <option value="">Select member</option>
              {orgMembers
                .filter(m => !teamDetail.members?.some(tm => tm.user_id === m.user_id))
                .map(m => (
                  <option key={m.user_id} value={m.user_id}>{m.username} ({m.email})</option>
                ))}
            </select>
            <select
              value={addMemberForm.role}
              onChange={e => setAddMemberForm({ ...addMemberForm, role: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13 }}
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
            <button type="submit" className="dash-scan-btn" style={{ fontSize: 12 }}>
              <UserPlus size={14} />
              <span>Add</span>
            </button>
          </form>

          {/* Members List */}
          <div style={{ padding: '0 16px 16px' }}>
            {teamDetail.members?.length === 0 ? (
              <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No members yet</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {teamDetail.members?.map(m => (
                  <div key={m.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', borderRadius: 6, background: 'var(--bg-tertiary)', fontSize: 13 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#fff' }}>
                        {m.username?.charAt(0)?.toUpperCase()}
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{m.username}</div>
                        <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>{m.email}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: m.role === 'admin' ? 'rgba(0,153,102,0.15)' : 'var(--bg-secondary)', color: m.role === 'admin' ? 'var(--accent-green)' : 'var(--text-tertiary)' }}>{m.role}</span>
                      <button onClick={() => handleRemoveMember(m.user_id)} style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', padding: 2 }}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
