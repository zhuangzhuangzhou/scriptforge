import React, { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Typography, message } from 'antd';
import { UserOutlined, ProjectOutlined, ThunderboltOutlined, CheckCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;

interface AdminStats {
  total_users: number;
  active_users: number;
  total_projects: number;
  total_tasks: number;
}

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(false);

  const loadStats = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/stats');
      setStats(res.data);
    } catch (error) {
      message.error('加载统计信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <div>
      <Title level={4} style={{ marginTop: 0 }}>管理概览</Title>
      <Text type="secondary">系统实时数据概览</Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="总用户数" value={stats?.total_users || 0} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="活跃用户" value={stats?.active_users || 0} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="项目数" value={stats?.total_projects || 0} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="AI任务数" value={stats?.total_tasks || 0} prefix={<ThunderboltOutlined />} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdminDashboard;
