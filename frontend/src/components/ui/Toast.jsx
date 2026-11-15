import React, { createContext, useContext, useState, useEffect } from 'react';
import './Toast.css';

const ToastContext = createContext({
  showToast: (args) => {},
  dismissToast: (id) => {},
});

export const useToast = () => useContext(ToastContext);

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const showToast = (args) => {
    const { title, description, variant = 'default', duration = 5000, id: explicitId } = args;
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const newToast = { id, title, description, variant, duration, show: true };

    setToasts((prev) => [...prev, newToast]);

    // Auto-remove after duration
    const timer = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);

    return () => clearTimeout(timer);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast, dismissToast }}>
      <div className="toast-container">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast toast-${toast.variant} ${toast.show ? 'visible' : 'hidden'}`}
            style={{ animation: toast.show ? 'slideIn 0.3s ease-out' : 'slideOut 0.3s ease-in' }}
          >
            <span className="toast-icon">
              {toast.variant === 'success' && <CheckCircle size={16} />}
              {toast.variant === 'error' && <AlertCircle size={16} />}
              {toast.variant === 'warning' && <AlertTriangle size={16} />}
              {toast.variant === 'info' && <Info size={16} />}
            </span>
            <div className="toast-content">
              <strong className="toast-title">{toast.title}</strong>
              <p className="toast-description">{toast.description}</p>
            </div>
            <button
              className="toast-dismiss"
              onClick={() => dismissToast(toast.id)}
              aria-label="Dismiss toast"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export default ToastProvider;