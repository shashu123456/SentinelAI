import { createContext, useContext, useState, useEffect } from 'react';
import { auth } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const savedToken = localStorage.getItem('sentinelai_token');
      const savedUser = localStorage.getItem('sentinelai_user');
      if (savedToken && savedUser) {
        const parsed = JSON.parse(savedUser);
        if (parsed && typeof parsed === 'object') {
          setToken(savedToken);
          setUser(parsed);
        } else {
          localStorage.removeItem('sentinelai_token');
          localStorage.removeItem('sentinelai_user');
        }
      }
    } catch {
      localStorage.removeItem('sentinelai_token');
      localStorage.removeItem('sentinelai_user');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const onAuthRefresh = () => {
      const savedToken = localStorage.getItem('sentinelai_token');
      const savedUser = localStorage.getItem('sentinelai_user');
      if (!savedToken || !savedUser) return;
      setToken(savedToken);
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        setUser(null);
      }
    };
    window.addEventListener('sentinelai:auth-refresh', onAuthRefresh);
    return () => window.removeEventListener('sentinelai:auth-refresh', onAuthRefresh);
  }, []);

  const login = (tokenStr, userData) => {
    localStorage.setItem('sentinelai_token', tokenStr);
    localStorage.setItem('sentinelai_user', JSON.stringify(userData));
    setToken(tokenStr);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('sentinelai_token');
    localStorage.removeItem('sentinelai_user');
    setToken(null);
    setUser(null);
  };

  const logoutAll = async () => {
    try {
      await auth.logoutAll();
    } catch {
      // proceed with local logout even if the server call fails
    }
    logout();
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, logoutAll, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
