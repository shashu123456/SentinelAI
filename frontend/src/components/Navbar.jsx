import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Shield, LayoutDashboard, Upload, FileCode, Package,
  Bot, LogOut
} from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    if (path === '/dashboard') return location.pathname === '/' || location.pathname === '/dashboard';
    return location.pathname === path;
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Shield size={18} />
        </div>
        <div className="sidebar-brand-text">
          <span className="sidebar-brand-name">SentinelAI</span>
          <span className="sidebar-brand-tag">Security</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Overview</div>
        <Link to="/dashboard" className={`sidebar-link ${isActive('/dashboard') ? 'active' : ''}`}>
          <LayoutDashboard size={18} /> Dashboard
        </Link>

        <div className="sidebar-section-label">Scanning</div>
        <Link to="/new-scan" className={`sidebar-link ${isActive('/new-scan') ? 'active' : ''}`}>
          <Upload size={18} /> API Scan
        </Link>
        <Link to="/sast" className={`sidebar-link ${isActive('/sast') ? 'active' : ''}`}>
          <FileCode size={18} /> SAST Analysis
        </Link>
        <Link to="/deps" className={`sidebar-link ${isActive('/deps') ? 'active' : ''}`}>
          <Package size={18} /> Dependencies
        </Link>

        <div className="sidebar-section-label">Intelligence</div>
        <Link to="/copilot" className={`sidebar-link ${isActive('/copilot') ? 'active' : ''}`}>
          <Bot size={18} /> AI Copilot
        </Link>
      </nav>

      <div className="sidebar-user">
        <div className="sidebar-avatar">{user?.username?.charAt(0).toUpperCase()}</div>
        <div className="sidebar-user-info">
          <div className="sidebar-username">{user?.username}</div>
          <div className="sidebar-userrole">Security Analyst</div>
        </div>
        <button className="sidebar-logout" onClick={handleLogout} title="Logout">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
