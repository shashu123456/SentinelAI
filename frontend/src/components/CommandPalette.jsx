import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import {
  Search, Shield, LayoutDashboard, Upload, FileCode, Package,
  Bot, AlertTriangle, ClipboardList, FileText, Settings, Users,
  Key, Activity, Heart, Bell, ChevronRight, ArrowRight,
  CornerDownLeft, X, Sun, Moon, LogOut, Building2,
  ShieldAlert, Fingerprint, UserPlus, Globe,
} from 'lucide-react';

const COMMAND_SECTIONS = [
  {
    id: 'navigation',
    label: 'Navigation',
    items: [
      { id: 'nav-dashboard', label: 'Mission Control', description: 'Executive security overview', icon: LayoutDashboard, path: '/dashboard', keywords: ['home', 'overview', 'main'] },
      { id: 'nav-new-scan', label: 'New API Scan', description: 'Upload OpenAPI spec for analysis', icon: Upload, path: '/new-scan', keywords: ['scan', 'upload', 'openapi', 'swagger'] },
      { id: 'nav-sast', label: 'SAST Analysis', description: 'Static application security testing', icon: FileCode, path: '/sast', keywords: ['static', 'code', 'analysis'] },
      { id: 'nav-deps', label: 'Dependency Scanner', description: 'Scan for vulnerable dependencies', icon: Package, path: '/deps', keywords: ['dependencies', 'packages', 'cve'] },
      { id: 'nav-copilot', label: 'AI Security Copilot', description: 'Ask security questions with AI', icon: Bot, path: '/copilot', keywords: ['ai', 'chat', 'assistant'] },
      { id: 'nav-vulns', label: 'Vulnerability Explorer', description: 'Browse and manage all findings', icon: AlertTriangle, path: '/vulnerabilities', keywords: ['vulns', 'findings', 'issues'] },
      { id: 'nav-reports', label: 'Report Center', description: 'Generate and download reports', icon: FileText, path: '/reports', keywords: ['pdf', 'export'] },
      { id: 'nav-audit', label: 'Audit Center', description: 'Security event log and timeline', icon: ClipboardList, path: '/audit', keywords: ['logs', 'events', 'history'] },
      { id: 'nav-security', label: 'Security Events', description: 'Real-time threat monitoring', icon: ShieldAlert, path: '/security-events', keywords: ['threats', 'monitoring'] },
      { id: 'nav-health', label: 'System Health', description: 'Backend status and system metrics', icon: Activity, path: '/health', keywords: ['health', 'status', 'metrics'] },
    ],
  },
  {
    id: 'enterprise',
    label: 'Enterprise',
    items: [
      { id: 'nav-teams', label: 'Teams', description: 'Manage team members and roles', icon: Users, path: '/org/teams', keywords: ['team', 'members'] },
      { id: 'nav-invites', label: 'Invitations', description: 'Manage pending invitations', icon: UserPlus, path: '/org/invitations', keywords: ['invite', 'email'] },
      { id: 'nav-api-keys', label: 'API Keys', description: 'Manage API key access', icon: Fingerprint, path: '/org/api-keys', keywords: ['api', 'key', 'token'] },
      { id: 'nav-org-settings', label: 'Org Settings', description: 'Organization configuration', icon: Settings, path: '/org/settings', keywords: ['org', 'config'] },
    ],
  },
];

const QUICK_ACTIONS = [
  { id: 'action-theme', label: 'Toggle Theme', description: 'Switch dark/light mode', icon: Sun, action: 'toggle-theme', keywords: ['theme', 'dark', 'light', 'mode'] },
  { id: 'action-shortcuts', label: 'Keyboard Shortcuts', description: 'Show all keyboard shortcuts', icon: Key, action: 'show-shortcuts', keywords: ['keyboard', 'shortcuts', 'help'] },
];

const RECENT_STORAGE_KEY = 'sentinelai-recent-searches';
const MAX_RECENT = 5;

function getRecentSearches() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_STORAGE_KEY) || '[]');
  } catch { return []; }
}

function saveRecentSearch(query) {
  if (!query.trim()) return;
  const recent = getRecentSearches().filter(r => r !== query);
  recent.unshift(query);
  localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(recent.slice(0, MAX_RECENT)));
}

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentSearches, setRecentSearches] = useState([]);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const allItems = useMemo(() => [
    ...COMMAND_SECTIONS.flatMap(s => s.items),
    ...QUICK_ACTIONS,
  ], []);

  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems;
    const q = query.toLowerCase();
    return allItems.filter(item => {
      const searchable = [item.label, item.description, ...(item.keywords || [])].join(' ').toLowerCase();
      return searchable.includes(q);
    });
  }, [query, allItems]);

  const groupedItems = useMemo(() => {
    const groups = {};
    filteredItems.forEach(item => {
      const section = COMMAND_SECTIONS.find(s => s.items.some(i => i.id === item.id));
      const label = section?.label || 'Quick Actions';
      if (!groups[label]) groups[label] = [];
      groups[label].push(item);
    });
    return groups;
  }, [filteredItems]);

  const flatFiltered = useMemo(() => Object.values(groupedItems).flat(), [groupedItems]);

  const executeItem = useCallback((item) => {
    if (item.action === 'toggle-theme') {
      toggleTheme();
    } else if (item.action === 'show-shortcuts') {
      window.dispatchEvent(new Event('open-shortcuts-help'));
    } else if (item.path) {
      navigate(item.path);
      if (query.trim()) saveRecentSearch(query.trim());
    }
    setIsOpen(false);
    setQuery('');
    setSelectedIndex(0);
  }, [navigate, toggleTheme, query]);

  useEffect(() => {
    if (!isOpen) return;
    inputRef.current?.focus();
    setRecentSearches(getRecentSearches());
  }, [isOpen]);

  useEffect(() => { setSelectedIndex(0); }, [query]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
        setQuery('');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Listen for external open events
  useEffect(() => {
    const handler = () => setIsOpen(true);
    window.addEventListener('open-cmd-palette', handler);
    return () => window.removeEventListener('open-cmd-palette', handler);
  }, []);

  const handleListKeyDown = useCallback((e) => {
    const maxIndex = flatFiltered.length - 1;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, maxIndex));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (flatFiltered[selectedIndex]) executeItem(flatFiltered[selectedIndex]);
    }
  }, [flatFiltered, selectedIndex, executeItem]);

  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const el = listRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      if (el) el.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  let globalIndex = 0;

  return (
    <div className="cmd-overlay" onClick={() => { setIsOpen(false); setQuery(''); }} role="dialog" aria-label="Command palette">
      <div className="cmd-palette" onClick={e => e.stopPropagation()}>
        <div className="cmd-input-wrap">
          <Search size={18} className="cmd-search-icon" />
          <input
            ref={inputRef}
            className="cmd-input"
            placeholder="Type a command or search..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleListKeyDown}
            autoComplete="off"
            spellCheck={false}
            aria-label="Search commands"
          />
          {query && (
            <button className="cmd-clear" onClick={() => { setQuery(''); inputRef.current?.focus(); }}>
              <X size={14} />
            </button>
          )}
          <kbd className="cmd-kbd">ESC</kbd>
        </div>

        <div className="cmd-list" ref={listRef}>
          {/* Recent searches (shown when empty) */}
          {!query.trim() && recentSearches.length > 0 && (
            <div className="cmd-section">
              <div className="cmd-section-label">Recent</div>
              {recentSearches.map((search, i) => (
                <div
                  key={`recent-${i}`}
                  className="cmd-item"
                  onClick={() => { setQuery(search); }}
                >
                  <div className="cmd-item-icon" style={{ opacity: 0.5 }}>
                    <Search size={14} />
                  </div>
                  <div className="cmd-item-text">
                    <div className="cmd-item-label">{search}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Search results */}
          {flatFiltered.length === 0 && query.trim() && (
            <div className="cmd-empty">
              <Search size={20} style={{ opacity: 0.3, marginBottom: 8 }} />
              <div>No results found for "{query}"</div>
            </div>
          )}

          {/* Grouped results */}
          {Object.entries(groupedItems).map(([sectionLabel, items]) => (
            <div key={sectionLabel} className="cmd-section">
              <div className="cmd-section-label">{sectionLabel}</div>
              {items.map((item) => {
                const currentIndex = globalIndex++;
                const Icon = item.icon;
                return (
                  <div
                    key={item.id}
                    data-index={currentIndex}
                    className={`cmd-item ${currentIndex === selectedIndex ? 'selected' : ''}`}
                    onClick={() => executeItem(item)}
                    onMouseEnter={() => setSelectedIndex(currentIndex)}
                    role="option"
                    aria-selected={currentIndex === selectedIndex}
                  >
                    <div className="cmd-item-icon">
                      <Icon size={16} />
                    </div>
                    <div className="cmd-item-text">
                      <div className="cmd-item-label">{item.label}</div>
                      <div className="cmd-item-desc">{item.description}</div>
                    </div>
                    {item.path && currentIndex === selectedIndex && (
                      <div className="cmd-item-action">
                        <CornerDownLeft size={12} />
                        <span>Go</span>
                      </div>
                    )}
                    {item.action && currentIndex === selectedIndex && (
                      <div className="cmd-item-action">
                        <CornerDownLeft size={12} />
                        <span>Do</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div className="cmd-footer">
          <div className="cmd-footer-hints">
            <div className="cmd-footer-hint">
              <kbd>↑</kbd><kbd>↓</kbd> <span>navigate</span>
            </div>
            <div className="cmd-footer-hint">
              <kbd>↵</kbd> <span>select</span>
            </div>
            <div className="cmd-footer-hint">
              <kbd>esc</kbd> <span>close</span>
            </div>
          </div>
          <div className="cmd-footer-user">
            {user?.username}
          </div>
        </div>
      </div>
    </div>
  );
}
