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
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = isRegister
        ? await auth.register({ username, email, password })
        : await auth.login({ username, password });
      login(data.access_token, data.user);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-left">
        <div className="login-brand">
          <div className="login-brand-icon"><Shield size={28} /></div>
          <div>
            <div className="login-brand-name">SentinelAI</div>
            <div className="login-brand-tag">Security Intelligence Platform</div>
          </div>
        </div>
        <div className="login-hero">
          <h1>AI-Powered<br />Security Analysis</h1>
          <p>Identify vulnerabilities, analyze risk, and remediate threats across your API surface with intelligent automation.</p>
          <div className="login-features">
            <div className="login-feature">
              <div className="login-feature-dot" />
              <span>OWASP API Security Top 10</span>
            </div>
            <div className="login-feature">
              <div className="login-feature-dot" />
              <span>Static Application Security Testing</span>
            </div>
            <div className="login-feature">
              <div className="login-feature-dot" />
              <span>Dependency Vulnerability Scanning</span>
            </div>
            <div className="login-feature">
              <div className="login-feature-dot" />
              <span>AI Security Copilot</span>
            </div>
          </div>
        </div>
      </div>

      <div className="login-right">
        <div className="login-card">
          <div className="login-tabs">
            <button className={`login-tab ${!isRegister ? 'active' : ''}`} onClick={() => { setIsRegister(false); setError(''); }}>Sign In</button>
            <button className={`login-tab ${isRegister ? 'active' : ''}`} onClick={() => { setIsRegister(true); setError(''); }}>Register</button>
          </div>

          {error && <div className="login-error">{error}</div>}

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label>Username</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="Enter username" required minLength={3} />
            </div>

            {isRegister && (
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Enter email" required />
              </div>
            )}

            <div className="form-group">
              <label>Password</label>
              <div className="login-pw-wrap">
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" required minLength={6} />
                <button type="button" className="pw-toggle" onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? 'Please wait...' : isRegister ? 'Create Account' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
