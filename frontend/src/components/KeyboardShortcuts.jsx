import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Keyboard } from 'lucide-react';
import './KeyboardShortcuts.css';

const SHORTCUTS = [
  { keys: ['⌘', 'K'], description: 'Open command palette', category: 'Navigation' },
  { keys: ['?'], description: 'Show keyboard shortcuts', category: 'Navigation' },
  { keys: ['/'], description: 'Focus search', category: 'Navigation' },
  { keys: ['Esc'], description: 'Close modals / panels', category: 'Navigation' },
  { keys: ['G', 'D'], description: 'Go to Dashboard', category: 'Go to...' },
  { keys: ['G', 'N'], description: 'Go to New Scan', category: 'Go to...' },
  { keys: ['G', 'S'], description: 'Go to SAST', category: 'Go to...' },
  { keys: ['G', 'V'], description: 'Go to Vulnerabilities', category: 'Go to...' },
  { keys: ['G', 'C'], description: 'Go to AI Copilot', category: 'Go to...' },
  { keys: ['G', 'R'], description: 'Go to Reports', category: 'Go to...' },
  { keys: ['G', 'A'], description: 'Go to Audit Center', category: 'Go to...' },
  { keys: ['G', 'H'], description: 'Go to System Health', category: 'Go to...' },
];

const GO_ROUTES = {
  D: '/dashboard',
  N: '/new-scan',
  S: '/sast',
  V: '/vulnerabilities',
  C: '/copilot',
  R: '/reports',
  A: '/audit',
  H: '/health',
};

export function KeyboardShortcutsProvider({ children }) {
  const [showHelp, setShowHelp] = useState(false);
  const [pendingGo, setPendingGo] = useState(false);
  const navigate = useNavigate();

  const handleKeyDown = useCallback((e) => {
    const tag = e.target.tagName;
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable;

    // Always allow Escape
    if (e.key === 'Escape') {
      setShowHelp(false);
      setPendingGo(false);
      window.dispatchEvent(new Event('close-panels'));
      return;
    }

    // Don't trigger shortcuts when typing in inputs
    if (isInput) return;

    // ? for help
    if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      setShowHelp(prev => !prev);
      return;
    }

    // / for search focus
    if (e.key === '/' && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      window.dispatchEvent(new Event('open-cmd-palette'));
      return;
    }

    // Go-to sequences: G + key
    if (pendingGo) {
      setPendingGo(false);
      const route = GO_ROUTES[e.key.toUpperCase()];
      if (route) {
        e.preventDefault();
        navigate(route);
      }
      return;
    }

    if (e.key === 'g' || e.key === 'G') {
      e.preventDefault();
      setPendingGo(true);
      setTimeout(() => setPendingGo(false), 2000);
      return;
    }
  }, [navigate, pendingGo]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <>
      {children}
      {showHelp && <ShortcutsModal onClose={() => setShowHelp(false)} />}
      {pendingGo && (
        <div className="shortcuts-go-indicator">
          <span>G →</span>
          <span className="shortcuts-go-hint">Press a key to navigate</span>
        </div>
      )}
    </>
  );
}

function ShortcutsModal({ onClose }) {
  const categories = [...new Set(SHORTCUTS.map(s => s.category))];

  return (
    <div className="shortcuts-overlay" onClick={onClose}>
      <div className="shortcuts-modal" onClick={e => e.stopPropagation()}>
        <div className="shortcuts-header">
          <div className="shortcuts-header-left">
            <Keyboard size={18} />
            <h2>Keyboard Shortcuts</h2>
          </div>
          <button className="shortcuts-close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div className="shortcuts-body">
          {categories.map(cat => (
            <div key={cat} className="shortcuts-category">
              <h3 className="shortcuts-category-title">{cat}</h3>
              <div className="shortcuts-list">
                {SHORTCUTS.filter(s => s.category === cat).map((shortcut, i) => (
                  <div key={i} className="shortcuts-item">
                    <span className="shortcuts-desc">{shortcut.description}</span>
                    <div className="shortcuts-keys">
                      {shortcut.keys.map((key, j) => (
                        <span key={j}>
                          <kbd className="shortcuts-key">{key}</kbd>
                          {j < shortcut.keys.length - 1 && <span className="shortcuts-plus">+</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="shortcuts-footer">
          Press <kbd className="shortcuts-key">?</kbd> to toggle this panel
        </div>
      </div>
    </div>
  );
}
