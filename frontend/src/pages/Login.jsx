import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { auth } from '../services/api';
import { Shield, Eye, EyeOff } from 'lucide-react';
import './Login.css';

export default function Login() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = isRegister
        ? await auth.register({ username: username.trim(), email: email.trim().toLowerCase(), password })
        : await auth.login({ username: username.trim(), password });
      login(data.access_token, data.user);
      navigate('/reports');
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async () => {
    setError('');
    setDemoLoading(true);
    try {
      const data = await auth.demoLogin();
      localStorage.setItem('sentinelai_demo', 'true');
      login(data.access_token, data.user);
      navigate('/reports');
    } catch (err) {
      setError(err.message || 'The demo is not available right now.');
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-left">
        <div className="login-brand">
          <div className="login-brand-icon"><Shield size={24} /></div>
          <div>
            <div className="login-brand-name">SentinelAI</div>
            <div className="login-brand-tag">Application security console</div>
          </div>
        </div>
        <div className="login-hero">
          <h1>Find it.<br />Understand it.<br />Fix it.</h1>
          <p>Three scanners, one upload box: API specs, dependency manifests and source files, with deterministic scoring and a fix instruction per finding.</p>
          <div className="login-features">
            <div className="login-feature">
              <span>OWASP API Security Top 10 Engine</span>
            </div>
            <div className="login-feature">
              <span>Static Application Security Testing</span>
            </div>
            <div className="login-feature">
              <span>Dependency CVE Intelligence</span>
            </div>
            <div className="login-feature">
              <span>Rule-based Security Copilot</span>
            </div>
          </div>
        </div>
      </div>

      <div className="login-right">
        <div className="login-card">
          <div className="login-intro">
            <h2>{isRegister ? 'Create your account' : 'Welcome back'}</h2>
            <p>
              {isRegister
                ? 'Use an address you can access — password recovery is sent there.'
                : 'Sign in to run a scan, read a report, or ask the Copilot.'}
            </p>
          </div>
          <div className="login-tabs">
            <button className={`login-tab ${!isRegister ? 'active' : ''}`} onClick={() => { setIsRegister(false); setError(''); }}>Sign In</button>
            <button className={`login-tab ${isRegister ? 'active' : ''}`} onClick={() => { setIsRegister(true); setError(''); }}>Register</button>
          </div>

          {error && <div className="login-error">{error}</div>}

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label>Username</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="analyst" required minLength={3} autoComplete="username" />
            </div>

            {isRegister && (
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  required
                  autoComplete="email"
                  spellCheck={false}
                />
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                  Use an address you can access — password recovery is sent there.
                </span>
              </div>
            )}

            <div className="form-group">
              <label>Password</label>
              <div className="login-pw-wrap">
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" required minLength={isRegister ? 8 : 1} autoComplete={isRegister ? 'new-password' : 'current-password'} />
                <button type="button" className="pw-toggle" onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {isRegister && (
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                  At least 8 characters, including an uppercase letter, a number and a symbol.
                </span>
              )}
            </div>

            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? 'Signing in…' : isRegister ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <div className="login-demo">
            <span className="login-demo-divider">or</span>
            <button
              type="button"
              className="login-demo-btn"
              onClick={handleDemo}
              disabled={demoLoading}
            >
              {demoLoading ? 'Loading demo…' : 'Try the live demo'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
