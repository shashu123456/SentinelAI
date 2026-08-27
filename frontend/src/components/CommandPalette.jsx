import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Search, Shield, LayoutDashboard, Upload, FileCode, Package,
  Bot, AlertTriangle, ClipboardList, FileText, Settings, Users,
  Key, Activity, Heart, Bell, BookOpen, ChevronRight,
  ArrowRight, CornerDownLeft, Search as SearchIcon, X,
} from 'lucide-react';

const COMMAND_SECTIONS = [
  {
    id: 'navigation',
    label: 'Navigation',
    items: [
      { id: 'nav-dashboard', label: 'Mission Control', description: 'Executive security overview', icon: LayoutDashboard, path: '/dashboard', keywords: ['home', 'overview', 'main'] },
      { id: 'nav-new-scan', label: 'New API Scan', description: 'Upload OpenAPI spec for analysis', icon: Upload, path: '/new-scan', keywords: ['scan', 'upload', 'openapi', 'swagger'] },
      { id: 'nav-sast', label: 'SAST Analysis', description: 'Static application security testing', icon: FileCode, path: '/sast', keywords: ['static', 'code', 'analysis', 'python', 'javascript', 'java'] },
      { id: 'nav-deps', label: 'Dependency Scanner', description: 'Scan for vulnerable dependencies', icon: Package, path: '/deps', keywords: ['dependencies', 'packages', 'cve', 'npm', 'pypi'] },
      { id: 'nav-copilot', label: 'AI Security Copilot', description: 'Ask security questions with AI', icon: Bot, path: '/copilot', keywords: ['ai', 'chat', 'assistant', 'help'] },
      { id: 'nav-vulns', label: 'Vulnerability Explorer', description: 'Browse and manage all findings', icon: AlertTriangle, path: '/vulnerabilities', keywords: ['vulns', 'findings', 'issues', 'cve', 'weakness'] },
      { id: 'nav-reports', label: 'Report Center', description: 'Generate and download reports', icon: FileText, path: '/reports', keywords: ['pdf', 'export', 'compliance', 'executive'] },
      { id: 'nav-audit', label: 'Audit Center', description: 'Security event log and timeline', icon: ClipboardList, path: '/audit', keywords: ['logs', 'events', 'activity', 'history'] },
      { id: 'nav-settings', label: 'Organization Settings', description: 'Manage teams, roles, and config', icon: Settings, path: '/settings', keywords: ['org', 'team', 'config', 'preferences'] },
      { id: 'nav-health', label: 'System Health', description: 'Backend status and system metrics', icon: Activity, path: '/health', keywords: ['health', 'status', 'uptime', 'metrics', 'system'] },
    ],
  },
];

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const navigate = useNavigate();
  const { user } = useAuth();

  const filteredItems = useMemo(() => {
    if (!query.trim()) {
      return COMMAND_SECTIONS.flatMap(s => s.items);
    }
    const q = query.toLowerCase();
    return COMMAND_SECTIONS.flatMap(s => s.items).filter(item => {
      const searchable = [item.label, item.description, ...(item.keywords || [])].join(' ').toLowerCase();
      return searchable.includes(q);
    });
  }, [query]);

  const executeItem = useCallback((item) => {
    if (item.path) {
      navigate(item.path);
    } else if (item.action) {
      item.action();
    }
    setIsOpen(false);
    setQuery('');
    setSelectedIndex(0);
  }, [navigate]);

  useEffect(() => {
    if (!isOpen) return;
    inputRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
        setQuery('');
        setSelectedIndex(0);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const handleListKeyDown = useCallback((e) => {
    const maxIndex = filteredItems.length - 1;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, maxIndex));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        executeItem(filteredItems[selectedIndex]);
      }
    }
  }, [filteredItems, selectedIndex, executeItem]);

  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const el = listRef.current.children[selectedIndex];
      if (el) el.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="cmd-overlay" onClick={() => { setIsOpen(false); setQuery(''); }}>
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
          />
          <kbd className="cmd-kbd">ESC</kbd>
        </div>

        <div className="cmd-list" ref={listRef}>
          {filteredItems.length === 0 && (
            <div className="cmd-empty">No results found for "{query}"</div>
          )}
          {filteredItems.map((item, i) => {
            const Icon = item.icon;
            return (
              <div
                key={item.id}
                className={`cmd-item ${i === selectedIndex ? 'selected' : ''}`}
                onClick={() => executeItem(item)}
                onMouseEnter={() => setSelectedIndex(i)}
              >
                <div className="cmd-item-icon">
                  <Icon size={16} />
                </div>
                <div className="cmd-item-text">
                  <div className="cmd-item-label">{item.label}</div>
                  <div className="cmd-item-desc">{item.description}</div>
                </div>
                {i === selectedIndex && (
                  <div className="cmd-item-action">
                    <CornerDownLeft size={12} />
                    <span>Go</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="cmd-footer">
          <div className="cmd-footer-hint">
            <kbd>↑</kbd><kbd>↓</kbd> navigate
          </div>
          <div className="cmd-footer-hint">
            <kbd>↵</kbd> select
          </div>
          <div className="cmd-footer-hint">
            <kbd>esc</kbd> close
          </div>
        </div>
      </div>
    </div>
  );
}
