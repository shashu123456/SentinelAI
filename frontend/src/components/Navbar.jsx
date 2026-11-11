import { useState, useEffect, useCallback } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useOrg } from '../context/OrgContext';
import {
  Shield, LayoutDashboard, Upload, FileCode, Package,
  Bot, AlertTriangle, ClipboardList, FileText, Settings,
  LogOut, Sun, Moon, Search, Key, Activity, Heart, BookOpen,
  Bell, Users, Globe, Lock, Cpu, HardDrive, Menu, X,
  Building2, FolderOpen, ChevronDown, UserPlus, Fingerprint,
  ShieldAlert, Clock, Copy, GitCompare, Download,
} from 'lucide-react';
import '../components/CommandPalette.css';

const NAV_SECTIONS = [
  {
    id: 'mission',
    label: 'Mission Control',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { path: '/org/dashboard', label: 'Org Dashboard', icon: Building2 },
    ],
  },
  {
    id: 'scanning',
    label: 'Scanning',
    items: [
      { path: '/new-scan', label: 'API Scanner', icon: Upload },
      { path: '/sast', label: 'SAST Analysis', icon: FileCode },
      { path: '/deps', label: 'Dependencies', icon: Package },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      { path: '/vulnerabilities', label: 'Vulnerabilities', icon: AlertTriangle },
      { path: '/copilot', label: 'AI Copilot', icon: Bot },
    ],
  },
  {
    id: 'operations',
    label: 'Operations',
    items: [
      { path: '/reports', label: 'Reports', icon: FileText },
      { path: '/audit', label: 'Audit Center', icon: ClipboardList },
      { path: '/health', label: 'System Health', icon: Activity },
      { path: '/security-events', label: 'Security Events', icon: ShieldAlert },
    ],
  },
  {
    id: 'automation',
    label: 'Automation',
    items: [
      { path: '/scheduled-scans', label: 'Scheduled Scans', icon: Clock },
      { path: '/templates', label: 'Scan Templates', icon: Copy },
      { path: '/policies', label: 'Policy Engine', icon: ShieldAlert },
      { path: '/webhooks', label: 'Webhooks', icon: Bell },
    ],
  },
  {
    id: 'compliance',
    label: 'Compliance',
    items: [
      { path: '/compliance', label: 'Compliance Center', icon: Shield },
      { path: '/executive-report', label: 'Executive Report', icon: FileText },
      { path: '/compare', label: 'Version Compare', icon: GitCompare },
      { path: '/exports', label: 'Export Center', icon: Download },
    ],
  },
  {
    id: 'enterprise',
    label: 'Enterprise',
    items: [
      { path: '/org/teams', label: 'Teams', icon: Users },
      { path: '/org/invitations', label: 'Invitations', icon: UserPlus },
      { path: '/org/api-keys', label: 'API Keys', icon: Fingerprint },
      { path: '/org/settings', label: 'Org Settings', icon: Settings },
    ],
  },
];

const FUTURE_MODULES = [
  { label: 'Asset Inventory', icon: HardDrive, coming: true },
  { label: 'Integrations', icon: Globe, coming: true },
];

const SETTINGS_ITEM = { path: '/settings', label: 'Settings', icon: Settings };

export default function Navbar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { currentOrg, currentProject, orgs, projects, selectOrg, selectProject } = useOrg();
  const [orgDropdownOpen, setOrgDropdownOpen] = useState(false);
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const [cmdOpen, setCmdOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const toggleMobile = useCallback(() => setMobileOpen(prev => !prev), []);

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Listen for command palette open events
  useEffect(() => {
    const handler = () => setCmdOpen(true);
    window.addEventListener('open-cmd-palette', handler);
    return () => window.removeEventListener('open-cmd-palette', handler);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    if (path === '/dashboard') return location.pathname === '/' || location.pathname === '/dashboard';
    return location.pathname === path;
  };

  return (
    <>
    {/* Mobile hamburger button */}
    <button className="mobile-menu-btn" onClick={toggleMobile} aria-label="Toggle menu">
      {mobileOpen ? <X size={18} /> : <Menu size={18} />}
    </button>

    {/* Mobile overlay */}
    <div className={`sidebar-overlay ${mobileOpen ? 'visible' : ''}`} onClick={toggleMobile} />

    <aside className={`sidebar ${mobileOpen ? 'open' : ''}`} role="navigation" aria-label="Main navigation">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Shield size={18} />
        </div>
        <div className="sidebar-brand-text">
          <span className="sidebar-brand-name">SENTINEL</span>
          <span className="sidebar-brand-tag">SOC Platform</span>
        </div>
      </div>

      {/* Organization Switcher */}
      {orgs.length > 0 && (
        <div className="org-switcher">
          <button className="org-switcher-btn" onClick={() => setOrgDropdownOpen(!orgDropdownOpen)}>
            <Building2 size={14} />
            <span className="org-switcher-name">{currentOrg?.name || 'Select Organization'}</span>
            <ChevronDown size={12} />
          </button>
          {orgDropdownOpen && (
            <div className="org-dropdown">
              <div className="org-dropdown-label">Organizations</div>
              {orgs.map(org => (
                <button
                  key={org.id}
                  className={`org-dropdown-item ${currentOrg?.id === org.id ? 'active' : ''}`}
                  onClick={() => { selectOrg(org); setOrgDropdownOpen(false); }}
                >
                  {org.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Project Switcher */}
      {currentOrg && projects.length > 0 && (
        <div className="org-switcher">
          <button className="org-switcher-btn" onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}>
            <FolderOpen size={14} />
            <span className="org-switcher-name">{currentProject?.name || 'All Projects'}</span>
            <ChevronDown size={12} />
          </button>
          {projectDropdownOpen && (
            <div className="org-dropdown">
              <button className="org-dropdown-item" onClick={() => { selectProject(null); setProjectDropdownOpen(false); }}>
                All Projects
              </button>
              {projects.map(proj => (
                <button
                  key={proj.id}
                  className={`org-dropdown-item ${currentProject?.id === proj.id ? 'active' : ''}`}
                  onClick={() => { selectProject(proj); setProjectDropdownOpen(false); }}
                >
                  {proj.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Command Palette Trigger */}
      <button className="cmd-trigger" onClick={() => setCmdOpen(true)}>
        <Search size={14} />
        <span className="cmd-trigger-label">Search or jump to...</span>
        <kbd className="cmd-trigger-kbd">⌘K</kbd>
      </button>

      <nav className="sidebar-nav" aria-label="Sidebar navigation">
        {NAV_SECTIONS.map(section => (
          <div key={section.id} className="sidebar-section">
            <div className="sidebar-section-label">// {section.label}</div>
            {section.items.map(item => {
              const Icon = item.icon;
              return (
                <Link key={item.path} to={item.path} className={`sidebar-link ${isActive(item.path) ? 'active' : ''}`} aria-current={isActive(item.path) ? 'page' : undefined}>
                  <Icon size={16} /> {item.label}
                </Link>
              );
            })}
          </div>
        ))}

        <div className="sidebar-divider" />
        <div className="sidebar-section-label">// Coming Soon</div>
        {FUTURE_MODULES.map(mod => {
          const Icon = mod.icon;
          return (
            <div key={mod.label} className="sidebar-link sidebar-link-disabled">
              <Icon size={16} /> {mod.label}
              <span className="sidebar-coming-badge">Soon</span>
            </div>
          );
        })}

        <div className="sidebar-divider" />
        <Link to={SETTINGS_ITEM.path} className={`sidebar-link ${isActive(SETTINGS_ITEM.path) ? 'active' : ''}`}>
          <SETTINGS_ITEM.icon size={16} /> {SETTINGS_ITEM.label}
        </Link>
      </nav>

      <div className="sidebar-user">
        <div className="sidebar-avatar">{user?.username?.charAt(0).toUpperCase()}</div>
        <div className="sidebar-user-info">
          <div className="sidebar-username">{user?.username}</div>
          <div className="sidebar-userrole">SOC Analyst</div>
        </div>
        <button className="sidebar-theme-toggle" onClick={toggleTheme} title="Toggle theme" aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button className="sidebar-logout" onClick={handleLogout} title="Logout" aria-label="Log out of account">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
    </>
  );
}
