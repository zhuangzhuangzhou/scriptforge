import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider } from './context/AuthContext';
import MainLayout from './components/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Dashboard from './pages/user/Dashboard';
import CreateProject from './pages/user/CreateProject';
import ProjectDetail from './pages/user/ProjectDetail';
import PlotBreakdown from './pages/user/PlotBreakdown';
import ScriptGeneration from './pages/user/ScriptGeneration';
import SkillsManagement from './pages/user/SkillsManagement';
import Workspace from './pages/user/Workspace';
import { UserTier } from './types';

const App: React.FC = () => {
  const [activeProject, setActiveProject] = useState<any>(null);
  const [userTier, setUserTier] = useState<UserTier>('FREE');

  return (
    <ConfigProvider locale={zhCN}>
      <AuthProvider>
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

                  {/* Workspace Route (Modern UI) */}
                  <Route path="/workspace" element={
                    activeProject ? <Workspace project={activeProject} userTier={userTier} /> : <Navigate to="/dashboard" />
                  } />

                  {/* Legacy Project Routes (Keeping them accessible) */}
                  <Route path="/projects/create" element={<CreateProject />} />
                  <Route path="/projects/:projectId" element={<ProjectDetail />} />
                  <Route path="/projects/:projectId/breakdown" element={<PlotBreakdown />} />
                  <Route path="/projects/:projectId/scripts" element={<ScriptGeneration />} />

                  <Route path="/skills" element={<SkillsManagement />} />
                </Route>
              </Route>

              {/* Default Redirect */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
      </AuthProvider>
    </ConfigProvider>
  );
};

export default App;
