import React, { useEffect, useState } from 'react';
import { Row, Col, Statistic } from 'antd';
import {
  UserOutlined, ProjectOutlined, ThunderboltOutlined, DatabaseOutlined,
  SettingOutlined, TeamOutlined, ApiOutlined, CodeOutlined, RobotOutlined,
  FileTextOutlined, UnorderedListOutlined, BarChartOutlined, ClockCircleOutlined,
  BellOutlined, GiftOutlined, MessageOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { adminApi } from '../../services/api';
import { GlassCard } from '../../components/ui/GlassCard';

interface AdminStats {
  total_users: number;
  active_projects: number;
  pending_tasks: number;
  system_status: string;
  credit_consumed_today: number;
}

// 统计卡片配置
const statCards = [
  { key: 'total_users', title: '总用户数', icon: UserOutlined, color: '#3b82f6' },
  { key: 'active_projects', title: '活跃项目', icon: ProjectOutlined, color: '#10b981' },
  { key: 'pending_tasks', title: '待处理任务', icon: ThunderboltOutlined, color: '#f59e0b' },
  { key: 'credit_consumed_today', title: '今日消耗算力', icon: DatabaseOutlined, color: '#ec4899' },
] as const;

// 快速操作配置
const quickActions = [
  { path: '/admin/users', icon: TeamOutlined, color: 'blue', title: '用户管理', desc: '管理用户权限与等级' },
  { path: '/admin/configurations', icon: SettingOutlined, color: 'cyan', title: 'AI 系统配置', desc: '配置方法论与系统参数' },
  { path: '/admin/models', icon: ApiOutlined, color: 'purple', title: '模型管理', desc: '管理 AI 模型与凭证' },
  { path: '/admin/skills', icon: CodeOutlined, color: 'emerald', title: 'Skills 管理', desc: '管理 AI 技能与 Prompt' },
  { path: '/admin/agents', icon: RobotOutlined, color: 'amber', title: 'Agents 管理', desc: '管理 AI 工作流' },
  { path: '/admin/resources', icon: FileTextOutlined, color: 'rose', title: '资源文档', desc: '管理方法论与模板文档' },
  { path: '/admin/tasks', icon: ClockCircleOutlined, color: 'orange', title: '任务管理', desc: '监控和管理运行中的任务' },
  { path: '/admin/logs', icon: UnorderedListOutlined, color: 'indigo', title: '任务日志', desc: '查看系统任务执行日志' },
  { path: '/admin/analytics', icon: BarChartOutlined, color: 'teal', title: '数据分析', desc: '分析模型与质检数据' },
  { path: '/admin/announcements', icon: BellOutlined, color: 'blue', title: '通知公告', desc: '发布系统通知与公告' },
  { path: '/admin/redeem-codes', icon: GiftOutlined, color: 'emerald', title: '兑换码管理', desc: '创建和管理兑换码' },
  { path: '/admin/feedbacks', icon: MessageOutlined, color: 'pink', title: '用户反馈', desc: '查看和处理用户反馈' },
];

// 颜色映射（Tailwind 动态类名需要完整写出）
const colorClasses: Record<string, { bg: string; bgHover: string; text: string }> = {
  blue: { bg: 'bg-blue-500/10', bgHover: 'group-hover:bg-blue-500/20', text: 'text-blue-500' },
  cyan: { bg: 'bg-cyan-500/10', bgHover: 'group-hover:bg-cyan-500/20', text: 'text-cyan-500' },
  purple: { bg: 'bg-purple-500/10', bgHover: 'group-hover:bg-purple-500/20', text: 'text-purple-500' },
  emerald: { bg: 'bg-emerald-500/10', bgHover: 'group-hover:bg-emerald-500/20', text: 'text-emerald-500' },
  amber: { bg: 'bg-amber-500/10', bgHover: 'group-hover:bg-amber-500/20', text: 'text-amber-500' },
  rose: { bg: 'bg-rose-500/10', bgHover: 'group-hover:bg-rose-500/20', text: 'text-rose-500' },
  orange: { bg: 'bg-orange-500/10', bgHover: 'group-hover:bg-orange-500/20', text: 'text-orange-500' },
  indigo: { bg: 'bg-indigo-500/10', bgHover: 'group-hover:bg-indigo-500/20', text: 'text-indigo-500' },
  teal: { bg: 'bg-teal-500/10', bgHover: 'group-hover:bg-teal-500/20', text: 'text-teal-500' },
  pink: { bg: 'bg-pink-500/10', bgHover: 'group-hover:bg-pink-500/20', text: 'text-pink-500' },
};

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
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent m-0">
            系统概览
          </h1>
          <p className="text-slate-400 mt-1">管理后台控制面板</p>
        </div>

        <Row gutter={[16, 16]} className="mb-8">
          {statCards.map(({ key, title, icon: Icon, color }) => (
            <Col xs={24} sm={12} lg={6} key={key}>
              <GlassCard>
                <Statistic
                  title={<span className="text-slate-400">{title}</span>}
                  value={stats?.[key]}
                  loading={loading}
                  prefix={<Icon />}
                  valueStyle={{ color }}
                />
              </GlassCard>
            </Col>
          ))}
        </Row>

        <h2 className="text-xl font-semibold text-slate-100 mb-4">快速操作</h2>
        <Row gutter={[16, 16]}>
          {quickActions.map(({ path, icon: Icon, color, title, desc }) => {
            const colors = colorClasses[color] || colorClasses.blue;
            return (
              <Col xs={24} sm={12} md={8} lg={6} key={path}>
                <GlassCard
                  className="cursor-pointer hover:border-slate-600 transition-colors group"
                  onClick={() => navigate(path)}
                >
                  <div className="flex flex-col items-center justify-center py-4">
                    <div className={`p-3 rounded-full ${colors.bg} ${colors.bgHover} mb-3 transition-colors`}>
                      <Icon className={`text-2xl ${colors.text}`} />
                    </div>
                    <span className="text-slate-200 font-medium">{title}</span>
                    <span className="text-slate-500 text-xs mt-1">{desc}</span>
                  </div>
                </GlassCard>
              </Col>
            );
          })}
        </Row>
      </motion.div>
    </div>
  );
};

export default AdminDashboard;
