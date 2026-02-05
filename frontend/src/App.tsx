import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { AuthProvider } from './context/AuthContext'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import Dashboard from './pages/user/Dashboard'
import CreateProject from './pages/user/CreateProject'
import ProjectDetail from './pages/user/ProjectDetail'
import PlotBreakdown from './pages/user/PlotBreakdown'
import ScriptGeneration from './pages/user/ScriptGeneration'
import SkillsManagement from './pages/user/SkillsManagement'
import MainLayout from './components/MainLayout'
import ProtectedRoute from './components/ProtectedRoute'
import PipelineExecutions from './pages/admin/PipelineExecutions'
import AdminRoute from './components/AdminRoute'
import AdminDashboard from './pages/admin/AdminDashboard'
import UsersAdmin from './pages/admin/UsersAdmin'
import SkillsAdmin from './pages/admin/SkillsAdmin'

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route element={<MainLayout />}>
              <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/projects/create" element={<CreateProject />} />
                <Route path="/projects/:projectId" element={<ProjectDetail />} />
                <Route path="/projects/:projectId/breakdown" element={<PlotBreakdown />} />
                <Route path="/projects/:projectId/scripts" element={<ScriptGeneration />} />
                <Route path="/skills" element={<SkillsManagement />} />
                <Route element={<AdminRoute />}>
                  <Route path="/admin/dashboard" element={<AdminDashboard />} />
                  <Route path="/admin/users" element={<UsersAdmin />} />
                  <Route path="/admin/skills" element={<SkillsAdmin />} />
                  <Route path="/admin/pipeline-executions" element={<PipelineExecutions />} />
                </Route>
              </Route>
            </Route>

            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  )
}

export default App
