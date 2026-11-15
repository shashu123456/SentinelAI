import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from './ui/Toast';
import { useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { Menu, Settings, LogOut, Sun, Moon, User, Home, Search, ChevronDown } from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const [showMenu, setShowMenu] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const stored = localStorage.getItem('sentinelai-dark-mode');
    setDarkMode(stored === 'true' || (!stored && prefersDark));
  }, []);

  useEffect(() => {
    if (darkMode) {
      localStorage.setItem('sentinelai-dark-mode', 'true');
      document.documentElement.classList.add('dark');
    } else {
      localStorage.setItem('sentinelai-dark-mode', 'false');
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const handleLogout = () => {
    logout();
    showToast('Logged out successfully', 'success');
    navigate('/');
  };

  const showToast = (msg, type = 'success') => {
    useToast()(showToast, { title: type === 'success' ? 'Success' : 'Error', description: msg, variant: type, duration: 3000 });
  };

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <a href="/" className="navbar-logo">
          <Sun size={20} className="hidden-dark" />
          <Moon size={20} className="visible-dark" />
          SentinelAI
        </a>
      </div>

      <div className="navbar-center">
        <div className="navbar-search">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search"
            className="search-input"
          />
        </div>
      </div>

      <div className="navbar-right">
        {isAuthenticated && user && (
          <div className="navbar-user">
            <User size={24} className="navbar-user-avatar" />
            <span className="navbar-user-name">{user.username}</span>
            <ChevronDown size={12} className="navbar-user-arrow" />
          </div>
        )}

        <button
          className="navbar-menu-btn"
          onClick={() => setShowMenu(!showMenu)}
          aria-label="Menu"
        >
          <Menu size={20} />
        </button>

        {showMenu && (
          <div className="navbar-dropdown">
            <a href="/dashboard" className="navbar-dropdown-item">
              <Home size={14} className="navbar-dropdown-icon" /> Dashboard
            </a>
            <a href="/settings" className="navbar-dropdown-item">
              <Settings size={14} className="navbar-dropdown-icon" /> Settings
            </a>
            <hr className="navbar-dropdown-divider" />
            <button
              onClick={handleLogout}
              className="navbar-dropdown-item navbar-dropdown-logout"
            >
              <LogOut size={14} className="navbar-dropdown-icon" /> Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}