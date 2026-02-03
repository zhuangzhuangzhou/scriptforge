import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Menu, Card, Statistic, Row, Col, Button, Spin } from 'antd';
import {
  ProjectOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  ExportOutlined,
  SettingOutlined
} from '@ant-design/icons';

const { Sider, Content } = Layout;

interface Project {
  id: string;
  name: string;
  novel_type: string;
  description: string;
  total_chapters: number;
  total_words: number;
  processed_chapters: number;
  status: string;
}

const ProjectDetail: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<Project | null>(null);
  const [selectedMenu, setSelectedMenu] = useState('overview');

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      const response = await fetch(`/api/v1/projects/${projectId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('加载项目失败');
      const data = await response.json();
      setProject(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const menuItems = [
    { key: 'overview', icon: <ProjectOutlined />, label: '项目概览' },
    { key: 'breakdown', icon: <FileTextOutlined />, label: '剧情拆解' },
    { key: 'scripts', icon: <VideoCameraOutlined />, label: '剧本生成' },
    { key: 'export', icon: <ExportOutlined />, label: '导出管理' },
    { key: 'settings', icon: <SettingOutlined />, label: '项目设置' }
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    setSelectedMenu(key);
    if (key === 'breakdown') {
      navigate(`/projects/${projectId}/breakdown`);
    } else if (key === 'scripts') {
      navigate(`/projects/${projectId}/scripts`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spin size="large" />
      </div>
    );
  }

  if (!project) {
    return <div>项目不存在</div>;
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={200} theme="light">
        <div className="p-4 border-b">
          <Button
            type="link"
            onClick={() => navigate('/dashboard')}
            className="p-0"
          >
            ← 返回项目列表
          </Button>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedMenu]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Content style={{ padding: '24px' }}>
          {selectedMenu === 'overview' && (
            <div>
              <h1 className="text-2xl font-bold mb-6">{project.name}</h1>

              {/* 项目基础信息 */}
              <Card title="项目信息" className="mb-4">
                <p><strong>小说类型：</strong>{project.novel_type}</p>
                <p><strong>项目描述：</strong>{project.description || '无'}</p>
                <p><strong>状态：</strong>{project.status}</p>
              </Card>

              {/* 统计信息 */}
              <Card title="统计信息" className="mb-4">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic title="章节总数" value={project.total_chapters} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="总字数" value={project.total_words} />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="已处理章节"
                      value={project.processed_chapters}
                      suffix={`/ ${project.total_chapters}`}
                    />
                  </Col>
                </Row>
              </Card>
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  );
};

export default ProjectDetail;
