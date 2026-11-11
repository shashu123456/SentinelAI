import { useState, useEffect, useCallback } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useOrg } from '../context/OrgContext';
import {
  Shield,
  LayoutDashboard,
  Upload,
  FileCode,
  Package,
  Bot,
  AlertTriangle,
  ClipboardList,
  FileText,
  Settings,
  LogOut,
  Sun,
  Moon,
  Search,
  Key,
  Activity,
  Heart,
  BookOpen,
  Bell,
  Users,
  Globe,
  Lock,
  Cpu,
  HardDrive,
  Menu,
  X,
  Building2,
  FolderOpen,
  ChevronDown,
  UserPlus,
  Fingerprint,
  ShieldAlert,
  Clock,
  Copy,
  GitCompare,
  Download,
} from 'lucide-react';
import '../components/CommandPalette.css';

// Core nav sections that remain visible and functional
const CORE_NAV_SECTIONS = [
  {
    id: 'mission',
    label: 'Mission Control',
    coming: false,
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, coming: false },
      { path: '/org/dashboard', label: 'Org Dashboard', icon: Building2, coming: false },
    ],
  },
  {
    id: 'scanning',
    label: 'Scanning',
    coming: false,
    items: [
      { path: '/new-scan', label: 'API Scanner', icon: Upload, coming: false },
      { path: '/sast', label: 'SAST Analysis', icon: FileCode, coming: false },
      { path: '/deps', label: 'Dependencies', icon: Package, coming: false },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    coming: false,
    items: [
      { path: '/vulnerabilities', label: 'Vulnerabilities', icon: AlertTriangle, coming: false },
      { path: '/copilot', label: 'AI Copilot', icon: Bot, coming: false },
    ],
  },
  {
    id: 'operations',
    label: 'Operations',
    coming: false,
    items: [
      { path: '/reports', label: 'Reports', icon: FileText, coming: false },
      { path: '/audit', label: 'Audit Center', icon: ClipboardList, coming: false },
      { path: '/health', label: 'System Health', icon: Activity, coming: false },
      { path: '/security-events', label: 'Security Events', icon: ShieldAlert, coming: false },
    ],
  },
};

// Sections marked as Coming Soon / Beta / Experimental per specification
const HIDING_NAV_SECTIONS = [
  {
    id: 'enterprise',
    label: 'Enterprise',
    coming: true,
    items: [
      { path: '/org/teams', label: 'Teams', icon: Users, coming: true },
      { path: '/org/invitations', label: 'Invitations', icon: UserPlus, coming: true },
      { path: '/org/api-keys', label: 'API Keys', icon: Fingerprint, coming: true },
      { path: '/org/settings', label: 'Org Settings', icon: Settings, coming: true },
    ],
  },
  {
    id: 'compliance',
    label: 'Compliance',
    coming: true,
    items: [
      { path: '/compliance', label: 'Compliance Center', icon: Shield, coming: true },
      { path: '/executive-report', label: 'Executive Report', icon: FileText, coming: true },
      { path: '/compare', label: 'Version Compare', icon: GitCompare, coming: true },
      { path: '/exports', label: 'Export Center', icon: Download, coming: true },
    ],
  },
  {
    id: 'automation',
    label: 'Automation',
    coming: true,
    items: [
      { path: '/scheduled-scans', label: 'Scheduled Scans', icon: Clock, coming: true },
      { path: '/templates', label: 'Scan Templates', icon: Copy, coming: true },
      { path: '/policies', label: 'Policy Engine', icon: ShieldAlert, coming: true },
      { path: '/webhooks', label: 'Webhooks', icon: Bell, coming: true },
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
                ))
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
                <button className="org-dropdown-item" onClick={() => { selectProject(null); setProjectDropdownOpen(false); }}></button>
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
          </div>
        )}

        {/* Command Palette Trigger */}
        <button className="cmd-trigger" onClick={() => setCmdOpen(true)}>
          <Search size={14} />
          <span className="cmd-trigger-label">Search or jump to...</span>
          <kbd className="cmd-trigger-kbd">⌘K</kbd>
        </button>

        <nav className="sidebar-nav" aria-label="Sidebar navigation">
          {/* Core (functional) sections */}
          {CORE_NAV_SECTIONS.map(section => (
            <div key={section.id} className="sidebar-section">
              <div className="sidebar-section-label">{section.label}</div>
              {section.items.map(item => {
                const Icon = item.icon;
                const isCurrentPath = location.pathname === item.path;
                const isComing = item.coming;
                
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`sidebar-link ${isCurrentPath && !isComing ? 'active' : ''} ${isComing ? 'sidebar-link-coming' : ''}`}
                    aria-current={isCurrentPath && !isComing ? 'page' : undefined}
                  >
                    <Icon size={16} /> {item.label}
                    {isComing && <span className="sidebar-coming-badge">Coming Soon</span>
                  </Link>
                );
              })}
            </div>
          ))}

          {/* Coming Soon sections - marked as disabled */}
          {HIDING_NAV_SECTIONS.map(section => (
            <div key={section.id} className="sidebar-section sidebar-section-coming">
              <div className="sidebar-section-label coming-section-label">
                {section.label} <span className="coming-badge">Coming Soon</span>
              </div>
              {section.items.map(item => {
                const Icon = item.icon;
                return (
                  <div key={item.path} className="sidebar-link sidebar-link-coming">
                    <Icon size={16} /> {item.label}
                    <span className="sidebar-coming-badge">Coming Soon</span>
                  </div>
                );
              })}
            </div>
          ))}

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
          <div className="sidebar-section-label">// Core</div>
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

      <div className="sidebar-mobile-footer">
        <span>SentinelAI v1.1</span>
      </div>
    </>
  );
}