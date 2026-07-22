import { createContext, useContext, useState, useEffect } from 'react';

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

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
