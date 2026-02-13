import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api, { USE_MOCK } from '../services/api';
import { mockUser } from '../services/mockData';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  role: string;
  balance: number;  // 积分余额（来自后端 credits 字段）
  is_active: boolean;
  tier?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    
    const initAuth = async () => {
      if (USE_MOCK) {
        if (isMounted) {
          setUser(mockUser as any);
          setLoading(false);
        }
        return;
      }

      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        try {
          const response = await api.get('/auth/me');
          if (isMounted) {
            setUser(response.data);
          }
        } catch {
          if (isMounted) {
            localStorage.removeItem('token');
            localStorage.removeItem('username');
          }
        }
      }
      if (isMounted) {
        setLoading(false);
      }
    };
    
    initAuth();
    
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (username: string, password: string) => {
    if (USE_MOCK) {
      // 模拟网络延迟
      await new Promise(resolve => setTimeout(resolve, 800));
      const mockToken = 'mock-jwt-token';
      localStorage.setItem('token', mockToken);
      setToken(mockToken);
      setUser(mockUser as any);
      return mockUser as any;
    }

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '登录失败');
    }

    const data = await response.json();
    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);

    const userResponse = await api.get('/auth/me');
    setUser(userResponse.data);
    return userResponse.data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
