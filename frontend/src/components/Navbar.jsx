import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useToast } from './ui/Toast';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Menu, LogOut, Sun, Moon, FlaskConical } from 'lucide-react';
import './Navbar.css';

// Exactly three primary destinations. Everything else lives under /beta.
const PRIMARY_LINKS = [
  { to: '/scans/new', label: 'New Scan' },
  { to: '/reports', label: 'Reports' },
  { to: '/coverage', label: 'Coverage' },
];

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const [showMenu, setShowMenu] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();

  const handleLogout = () => {
    logout();
    showToast?.({ title: 'Logged out', description: 'You have been signed out.', variant: 'success' });
    navigate('/');
  };

  const inBeta = location.pathname.startsWith('/beta');

  return (
    <nav className="navbar" aria-label="Primary">
      <div className="navbar-left">
        <NavLink to="/reports" className="navbar-logo">SentinelAI</NavLink>
      </div>

      <div className="navbar-center">
        <ul className="navbar-links">
          {PRIMARY_LINKS.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) => `navbar-link${isActive ? ' active' : ''}`}
                end={link.to === '/scans/new'}
              >
                {link.label}
              </NavLink>
            </li>
          ))}
          <li>
            <NavLink
              to="/beta/dashboard"
              className={({ isActive }) =>
                `navbar-link navbar-beta${isActive || inBeta ? ' active' : ''}`
              }
            >
              <FlaskConical size={13} aria-hidden="true" /> Beta
            </NavLink>
          </li>
        </ul>
      </div>

      <div className="navbar-right">
        <button
          className="navbar-icon-btn"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {isAuthenticated && user && (
          <span className="navbar-user-name">{user.username}</span>
        )}

        <button
          className="navbar-icon-btn"
          onClick={() => setShowMenu((v) => !v)}
          aria-label="Menu"
          aria-expanded={showMenu}
        >
          <Menu size={20} />
        </button>

        {showMenu && (
          <div className="navbar-dropdown" role="menu">
            <button onClick={handleLogout} className="navbar-dropdown-item navbar-dropdown-logout" role="menuitem">
              <LogOut size={14} className="navbar-dropdown-icon" /> Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
