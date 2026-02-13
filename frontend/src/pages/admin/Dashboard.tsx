import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Typography } from 'antd';
import { UserOutlined, ProjectOutlined, ThunderboltOutlined, DatabaseOutlined, SettingOutlined, TeamOutlined, ApiOutlined, CodeOutlined, RobotOutlined, FileTextOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../../services/api';

const { Title } = Typography;

interface AdminStats {
  total_users: number;
  active_projects: number;
  pending_tasks: number;
  system_status: string;
  credit_consumed_today: number;
}

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const { data } = await adminApi.getStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch admin stats', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex justify-between items-center mb-6">
        <Title level={2} className="text-slate-100 m-0">系统概览</Title>
      </div>

      <Row gutter={[16, 16]} className="mb-8">
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="bg-slate-800 text-slate-200">
            <Statistic
              title={<span className="text-slate-400">总用户数</span>}
              value={stats?.total_users}
              loading={loading}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#3b82f6' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="bg-slate-800 text-slate-200">
            <Statistic
              title={<span className="text-slate-400">活跃项目</span>}
              value={stats?.active_projects}
              loading={loading}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="bg-slate-800 text-slate-200">
            <Statistic
              title={<span className="text-slate-400">待处理任务</span>}
              value={stats?.pending_tasks}
              loading={loading}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#f59e0b' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="bg-slate-800 text-slate-200">
            <Statistic
              title={<span className="text-slate-400">今日消耗算力</span>}
              value={stats?.credit_consumed_today}
              loading={loading}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#ec4899' }}
            />
          </Card>
        </Col>
      </Row>

      <Title level={3} className="text-slate-100 mb-4">快速操作</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            className="bg-slate-800 border-slate-700 cursor-pointer group"
            onClick={() => navigate('/admin/users')}
          >
            <div className="flex flex-col items-center justify-center py-4">
              <div className="p-3 rounded-full bg-blue-500/10 mb-3 group-hover:bg-blue-500/20 transition-colors">
                <TeamOutlined className="text-2xl text-blue-500" />
              </div>
              <span className="text-slate-200 font-medium">用户管理</span>
              <span className="text-slate-500 text-xs mt-1">管理用户权限与等级</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            className="bg-slate-800 border-slate-700 cursor-pointer group"
            onClick={() => navigate('/admin/configurations')}
          >
            <div className="flex flex-col items-center justify-center py-4">
              <div className="p-3 rounded-full bg-cyan-500/10 mb-3 group-hover:bg-cyan-500/20 transition-colors">
                <SettingOutlined className="text-2xl text-cyan-500" />
              </div>
              <span className="text-slate-200 font-medium">AI 系统配置</span>
              <span className="text-slate-500 text-xs mt-1">配置方法论与系统参数</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            className="bg-slate-800 border-slate-700 cursor-pointer group"
            onClick={() => navigate('/admin/models')}
          >
            <div className="flex flex-col items-center justify-center py-4">
              <div className="p-3 rounded-full bg-purple-500/10 mb-3 group-hover:bg-purple-500/20 transition-colors">
                <ApiOutlined className="text-2xl text-purple-500" />
              </div>
              <span className="text-slate-200 font-medium">模型管理</span>
              <span className="text-slate-500 text-xs mt-1">管理 AI 模型与凭证</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            className="bg-slate-800 border-slate-700 cursor-pointer group"
            onClick={() => navigate('/admin/skills')}
          >
            <div className="flex flex-col items-center justify-center py-4">
              <div className="p-3 rounded-full bg-emerald-500/10 mb-3 group-hover:bg-emerald-500/20 transition-colors">
                <CodeOutlined className="text-2xl text-emerald-500" />
              </div>
              <span className="text-slate-200 font-medium">Skills 管理</span>
              <span className="text-slate-500 text-xs mt-1">管理 AI 技能与 Prompt</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            className="bg-slate-800 border-slate-700 cursor-pointer group"
            onClick={() => navigate('/admin/agents')}
          >
            <div className="flex flex-col items-center justify-center py-4">
              <div className="p-3 rounded-full bg-amber-500/10 mb-3 group-hover:bg-amber-500/20 transition-colors">
                <RobotOutlined className="text-2xl text-amber-500" />
              </div>
              <span className="text-slate-200 font-medium">Agents 管理</span>
              <span className="text-slate-500 text-xs mt-1">管理 AI 工作流</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            className="bg-slate-800 border-slate-700 cursor-pointer group"
            onClick={() => navigate('/admin/resources')}
          >
            <div className="flex flex-col items-center justify-center py-4">
              <div className="p-3 rounded-full bg-rose-500/10 mb-3 group-hover:bg-rose-500/20 transition-colors">
                <FileTextOutlined className="text-2xl text-rose-500" />
              </div>
              <span className="text-slate-200 font-medium">资源文档</span>
              <span className="text-slate-500 text-xs mt-1">管理方法论与模板文档</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            className="bg-slate-800 border-slate-700 cursor-pointer group"
            onClick={() => navigate('/admin/logs')}
          >
            <div className="flex flex-col items-center justify-center py-4">
              <div className="p-3 rounded-full bg-indigo-500/10 mb-3 group-hover:bg-indigo-500/20 transition-colors">
                <UnorderedListOutlined className="text-2xl text-indigo-500" />
              </div>
              <span className="text-slate-200 font-medium">任务日志</span>
              <span className="text-slate-500 text-xs mt-1">查看系统任务执行日志</span>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdminDashboard;
