import { Component } from 'react';
import { AlertTriangle, RefreshCw, RotateCcw } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info?.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      // Page-level compact error (inside sidebar layout)
      if (this.props.pageLevel) {
        return (
          <div className="page-content">
            <div className="eb-page-error">
              <div className="eb-page-icon">
                <AlertTriangle size={24} />
              </div>
              <h3>This page encountered an error</h3>
              <p>{this.state.error?.message || 'An unexpected error occurred'}</p>
              <div className="eb-page-actions">
                <button className="eb-btn" onClick={this.handleReset}>
                  <RotateCcw size={14} /> Try Again
                </button>
                <button className="eb-btn primary" onClick={() => window.location.reload()}>
                  <RefreshCw size={14} /> Reload Page
                </button>
              </div>
            </div>
          </div>
        );
      }

      // Full-page error (app-level)
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          padding: '40px',
          background: 'var(--bg-page)',
          fontFamily: 'var(--font-sans)',
        }}>
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '16px',
            padding: '48px',
            maxWidth: '480px',
            textAlign: 'center',
          }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              background: 'rgba(255,51,85,0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              color: 'var(--accent-red)',
            }}>
              <AlertTriangle size={28} />
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Something went wrong
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px', lineHeight: 1.6 }}>
              An unexpected error occurred. Try reloading the page.
            </p>
            <div style={{
              background: 'var(--bg-page)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '24px',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--text-muted)',
              textAlign: 'left',
              maxHeight: '120px',
              overflow: 'auto',
              wordBreak: 'break-all',
            }}>
              {this.state.error?.message || 'Unknown error'}
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
              <button
                onClick={this.handleReset}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '8px',
                  padding: '10px 20px', background: 'transparent',
                  color: 'var(--text-muted)', border: '1px solid var(--border)',
                  borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                }}
              >
                <RotateCcw size={14} /> Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '8px',
                  padding: '10px 24px', background: 'var(--accent-blue)',
                  color: 'white', border: 'none', borderRadius: '8px',
                  fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                }}
              >
                <RefreshCw size={14} /> Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
