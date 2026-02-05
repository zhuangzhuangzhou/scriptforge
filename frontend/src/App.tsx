import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider } from './context/AuthContext';
import MainLayout from './components/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Dashboard from './pages/user/Dashboard';
import Workspace from './pages/user/Workspace';
import SkillsManagement from './pages/user/SkillsManagement';
import { UserTier } from './types';

const App: React.FC = () => {
  const [activeProject, setActiveProject] = useState<any>(null);
  const [userTier, setUserTier] = useState<UserTier>('FREE');

  return (
    <ConfigProvider locale={zhCN}>
      <AuthProvider>
        <BrowserRouter>
          <div className="min-h-screen w-full bg-slate-950 text-slate-200 selection:bg-cyan-500/30 overflow-hidden">
            <Routes>
              {/* Auth Routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Protected Workspace Routes */}
              <Route element={<MainLayout userTier={userTier} setUserTier={setUserTier} onLogout={() => window.location.href='/login'} />}>
                <Route element={<ProtectedRoute />}>
                  <Route path="/dashboard" element={
                    <Dashboard userTier={userTier} onOpenProject={(p) => setActiveProject(p)} />
                  } />
                  <Route path="/workspace" element={
                    activeProject ? <Workspace project={activeProject} userTier={userTier} /> : <Navigate to="/dashboard" />
                  } />
                  <Route path="/skills" element={<SkillsManagement />} />
                </Route>
              </Route>

              {/* Default Redirect */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  );
};

export default App;
