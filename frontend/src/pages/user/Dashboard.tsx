import React, { useEffect, useState } from 'react';
import { Card, Button, Empty, Row, Col, Statistic, Tag, Progress, Space, Typography } from 'antd';
import { PlusOutlined, ProjectOutlined, ClockCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

interface Project {
  id: string;
  name: string;
  novel_type: string;
  status: 'processing' | 'completed' | 'pending';
  progress: number;
  last_updated: string;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // Mock data loading
  useEffect(() => {
    // TODO: Replace with actual API call
    setTimeout(() => {
      setProjects([
        // Example data for visualization
        // { id: '1', name: '星际穿越', novel_type: '科幻', status: 'processing', progress: 45, last_updated: '2024-02-03' },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'completed': return <Tag color="success" icon={<CheckCircleOutlined />}>已完成</Tag>;
      case 'processing': return <Tag color="processing" icon={<ClockCircleOutlined />}>处理中</Tag>;
      default: return <Tag color="default">待开始</Tag>;
    }
  };

  return (
    <div style={{ minHeight: '100%' }}>
      {/* Header Section */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ marginBottom: 0 }}>工作台</Title>
          <Text type="secondary">欢迎回来，这里是你创作剧本的指挥中心</Text>
        </div>
        <Button
          type="primary"
          size="large"
          icon={<PlusOutlined />}
          onClick={() => navigate('/projects/create')}
          style={{ borderRadius: 6 }}
        >
          新建项目
        </Button>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={8}>
          <Card bordered={false}>
            <Statistic title="总项目数" value={projects.length} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card bordered={false}>
            <Statistic title="正在进行" value={projects.filter(p => p.status === 'processing').length} valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card bordered={false}>
            <Statistic title="已完成剧本" value={projects.filter(p => p.status === 'completed').length} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
      </Row>

      {/* Project Grid */}
      <Title level={4} style={{ marginBottom: 16 }}>我的项目</Title>
      
      {loading ? (
        <Card loading bordered={false} />
      ) : projects.length > 0 ? (
        <Row gutter={[16, 16]}>
          {projects.map(project => (
            <Col xs={24} sm={12} lg={8} key={project.id}>
              <Card
                hoverable
                bordered={false}
                onClick={() => navigate(`/projects/${project.id}`)}
                actions={[
                  <span key="edit">查看详情</span>,
                  <span key="setting">设置</span>
                ]}
              >
                <Card.Meta
                  avatar={<div style={{ 
                    width: 48, height: 48, 
                    background: '#e6f7ff', 
                    borderRadius: 8, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    color: '#1677ff',
                    fontSize: 24
                  }}>{project.name[0]}</div>}
                  title={
                    <Space>
                      {project.name}
                      <Tag>{project.novel_type}</Tag>
                    </Space>
                  }
                  description={
                    <div style={{ marginTop: 12 }}>
                      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>{getStatusTag(project.status)}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>{project.last_updated}</Text>
                      </div>
                      <Progress percent={project.progress} size="small" status={project.status === 'processing' ? 'active' : 'normal'} />
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      ) : (
        <Card bordered={false} style={{ textAlign: 'center', padding: '40px 0' }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>暂无项目，点击上方按钮开启你的创作之旅</span>
            }
          >
            <Button type="primary" onClick={() => navigate('/projects/create')}>立即创建</Button>
          </Empty>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
