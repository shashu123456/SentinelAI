import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button, Input, Label } from '../components/ui';
import { Shield, CheckCircle, Loader2 } from 'lucide-react';
import './Signup.css';

export default function Signup() {
  const [isRegister, setIsRegister] = useState(true);
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login, logout } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Validate passwords match
      if (form.password !== form.confirmPassword) {
        setError('Passwords do not match');
        setLoading(false);
        return;
      }

      // Validate password strength
      if (form.password.length < 8) {
        setError('Password must be at least 8 characters');
        setLoading(false);
        return;
      }

      // Register the user
      const data = await auth.register({
        username: form.username.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
      });

      login(data.access_token, data.user);
      navigate('/reports');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (mode) => {
    setIsRegister(mode);
    setForm({
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
    });
    setError('');
  };

  if (loading) {
    return (
      <div className="auth-page">
        <div className="auth-loader">
          <Loader2 size={32} className="spin" />
          <span>Creating your account...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-box">
          <div className="auth-header">
            <Shield size={32} className="auth-icon" />
            <h2>{isRegister ? 'Create Account' : 'Sign In'}</h2>
            <p>{isRegister ? 'Join SentinelAI and start securing your APIs' : 'Log in to your account'}</p>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <Label>Username</Label>
              <Input
                type="text"
                value={form.username}
                onChange={(e) =>
                  setForm({ ...form, username: e.target.value })
                }
                placeholder="Enter username"
                required
                autoComplete="username"
              />
            </div>

            {isRegister && (
              <div className="form-group">
                <Label>Email</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) =>
                    setForm({ ...form, email: e.target.value })
                  }
                  placeholder="you@company.com"
                  required
                  autoComplete="email"
                />
              </div>
            )}

            <div className="form-group">
              <Label>Password</Label>
              <Input
                type="password"
                value={form.password}
                onChange={(e) =>
                  setForm({ ...form, password: e.target.value })
                }
                placeholder="Enter password"
                required
                minLength={8}
                autoComplete="new-password"
              />
              <small className="password-hint">
                At least 8 characters, include uppercase, number & symbol
              </small>
            </div>

            {isRegister && (
              <div className="form-group">
                <Label>Confirm Password</Label>
                <Input
                  type="password"
                  value={form.confirmPassword}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      confirmPassword: e.target.value,
                    })
                  }
                  placeholder="Confirm password"
                  required
                  autoComplete="new-password"
                />
              </div>
            )}

            <Button type="submit" className="auth-btn" disabled={loading}>
              {loading ? '[ REGISTERING... ]' : (isRegister ? '[ CREATE ACCOUNT ]' : '[ SIGN IN ]')}
            </Button>
          </form>

          <div className="auth-actions">
            {isRegister && (
              <p className="auth-switch">
                Already have an account? <Button onClick={() => handleToggle('login')}>Sign In</Button>
              </p>
            )}
            {!isRegister && (
              <p className="auth-switch">
                Don't have an account? <Button onClick={() => handleToggle('register')}>Create Account</Button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}