import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider, useAuth } from './context/AuthContext';
import MainLayout from './components/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Dashboard from './pages/user/Dashboard';
import Workspace from './pages/user/Workspace';
import SkillsManagement from './pages/user/SkillsManagement';
import { UserTier } from './types';

// 加载状态组件
const LoadingScreen: React.FC = () => (
  <div className="min-h-screen w-full bg-slate-950 text-slate-200 flex items-center justify-center">
    <div className="text-center">
      <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
      <p className="text-slate-400">加载中...</p>
    </div>
  </div>
);

// 内部组件，用于从 AuthContext 获取 userTier
const AppContent: React.FC = () => {
  const { user, loading } = useAuth();
  const [userTier, setUserTier] = useState<UserTier>('FREE');

  // 当 user 加载完成后，从 user.tier 获取实际的等级
  useEffect(() => {
    if (!loading && user?.tier) {
      console.log('AppContent: 从后端获取到 user.tier:', user.tier);
      setUserTier(user.tier as UserTier);
    }
  }, [user, loading]);

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <Routes>
      {/* Auth Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected Workspace Routes */}
      <Route element={<MainLayout
        userTier={userTier}
        setUserTier={setUserTier}
        onLogout={() => {
          localStorage.removeItem('token');
          localStorage.removeItem('username');
          window.location.href = '/login';
        }}
      />}>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard userTier={userTier} />} />
          <Route path="/workspace/:projectId" element={<Workspace userTier={userTier} />} />
          <Route path="/skills" element={<SkillsManagement />} />
        </Route>
      </Route>

      {/* Default Redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <AuthProvider>
        <BrowserRouter>
          <div className="min-h-screen w-full bg-slate-950 text-slate-200 selection:bg-cyan-500/30 overflow-hidden">
            <AppContent />
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  );
};

export default App;
