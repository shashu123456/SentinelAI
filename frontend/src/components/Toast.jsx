import { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react';
import { X, CheckCircle2, AlertTriangle, Info, AlertOctagon } from 'lucide-react';

const ToastContext = createContext(null);

let toastId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [exiting, setExiting] = useState(new Set());
  const timers = useRef({});

  const removeToast = useCallback((id) => {
    // Start exit animation
    setExiting(prev => new Set([...prev, id]));
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
      setExiting(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      delete timers.current[id];
    }, 200);
  }, []);

  const addToast = useCallback((message, type = 'info', options = {}) => {
    const { duration = 4000, title, actions } = options;
    const id = ++toastId;

    setToasts(prev => {
      // Max 4 toasts visible
      const next = prev.length >= 4 ? prev.slice(1) : prev;
      return [...next, { id, message, type, title, actions, duration }];
    });

    if (duration > 0) {
      timers.current[id] = setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, [removeToast]);

  const success = useCallback((msg, opts) => addToast(msg, 'success', opts), [addToast]);
  const error = useCallback((msg, opts) => addToast(msg, 'error', { duration: 6000, ...opts }), [addToast]);
  const warning = useCallback((msg, opts) => addToast(msg, 'warning', { duration: 5000, ...opts }), [addToast]);
  const info = useCallback((msg, opts) => addToast(msg, 'info', opts), [addToast]);

  const pause = useCallback((id) => {
    if (timers.current[id]) {
      clearTimeout(timers.current[id]);
      delete timers.current[id];
    }
  }, []);

  const resume = useCallback((id) => {
    const toast = toasts.find(t => t.id === id);
    if (toast && toast.duration > 0) {
      timers.current[id] = setTimeout(() => removeToast(id), toast.duration);
    }
  }, [toasts, removeToast]);

  return (
    <ToastContext.Provider value={{ addToast, removeToast, success, error, warning, info, pause, resume }}>
      {children}
      <div className="toast-container" role="status" aria-live="polite">
        {toasts.map(toast => (
          <ToastItem
            key={toast.id}
            toast={toast}
            isExiting={exiting.has(toast.id)}
            onClose={() => removeToast(toast.id)}
            onPause={() => pause(toast.id)}
            onResume={() => resume(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, isExiting, onClose, onPause, onResume }) {
  const { id, message, type, title, actions, duration } = toast;

  const icons = {
    success: CheckCircle2,
    error: AlertOctagon,
    warning: AlertTriangle,
    info: Info,
  };

  const Icon = icons[type] || Info;

  return (
    <div
      className={`toast toast-${type} ${isExiting ? 'toast-exit' : ''}`}
      onClick={onClose}
      onMouseEnter={onPause}
      onMouseLeave={onResume}
      role="alert"
    >
      <div className="toast-icon">
        <Icon size={16} />
      </div>
      <div className="toast-body">
        {title && <div className="toast-title">{title}</div>}
        <div className="toast-message">{message}</div>
        {actions && actions.length > 0 && (
          <div className="toast-actions">
            {actions.map((action, i) => (
              <button
                key={i}
                className={`toast-action-btn ${action.primary ? 'primary' : ''}`}
                onClick={(e) => { e.stopPropagation(); action.onClick?.(); onClose(); }}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
      <button className="toast-close" onClick={(e) => { e.stopPropagation(); onClose(); }}>
        <X size={14} />
      </button>
      {duration > 0 && (
        <div className="toast-progress" style={{ animationDuration: `${duration}ms` }} />
      )}
    </div>
  );
}

export const useToast = () => useContext(ToastContext);
