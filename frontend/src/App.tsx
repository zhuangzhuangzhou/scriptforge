import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import Dashboard from './pages/user/Dashboard'
import CreateProject from './pages/user/CreateProject'
import ProjectDetail from './pages/user/ProjectDetail'
import PlotBreakdown from './pages/user/PlotBreakdown'
import ScriptGeneration from './pages/user/ScriptGeneration'
import SkillsManagement from './pages/user/SkillsManagement'

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects/create" element={<CreateProject />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/projects/:projectId/breakdown" element={<PlotBreakdown />} />
          <Route path="/projects/:projectId/scripts" element={<ScriptGeneration />} />
          <Route path="/skills" element={<SkillsManagement />} />
          <Route path="/" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
