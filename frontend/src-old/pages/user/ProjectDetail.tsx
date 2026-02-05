import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Statistic, Row, Col, Button, Spin, Tabs, Descriptions, Tag, Typography } from 'antd';
import {
  ProjectOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  ExportOutlined,
  LeftOutlined
} from '@ant-design/icons';
import PlotBreakdown from './PlotBreakdown';
import ScriptGeneration from './ScriptGeneration';

const { Title } = Typography;

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
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      // Mock data for UI testing if API fails
      // setProject({ id: '1', name: 'Mock Project', novel_type: 'Sci-Fi', description: 'Test', total_chapters: 100, total_words: 50000, processed_chapters: 20, status: 'Processing' });
      // return;

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

  const renderOverview = () => (
    <>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card bordered={false}>
            <Descriptions title="项目详情" bordered column={{ xxl: 4, xl: 3, lg: 3, md: 3, sm: 2, xs: 1 }}>
              <Descriptions.Item label="项目名称">{project?.name}</Descriptions.Item>
              <Descriptions.Item label="类型"><Tag color="blue">{project?.novel_type}</Tag></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color="processing">{project?.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="总字数">{project?.total_words?.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="章节数">{project?.total_chapters}</Descriptions.Item>
              <Descriptions.Item label="创建时间">2024-02-03</Descriptions.Item>
              <Descriptions.Item label="描述" span={3}>{project?.description || '无'}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col span={24}>
          <Card title="处理进度" bordered={false}>
            <Row gutter={16} style={{ textAlign: 'center' }}>
              <Col span={8}>
                <Statistic title="已拆解章节" value={project?.processed_chapters} suffix={`/ ${project?.total_chapters}`} />
              </Col>
              <Col span={8}>
                <Statistic title="已生成剧本" value={0} suffix="集" />
              </Col>
              <Col span={8}>
                <Statistic title="总耗时" value="2h 15m" />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </>
  );

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }}><Spin size="large" /></div>;
  if (!project) return <div>项目不存在</div>;

  const items = [
    { label: '项目概览', key: 'overview', icon: <ProjectOutlined />, children: renderOverview() },
    { label: '剧情拆解', key: 'breakdown', icon: <FileTextOutlined />, children: <PlotBreakdown /> },
    { label: '剧本生成', key: 'scripts', icon: <VideoCameraOutlined />, children: <ScriptGeneration /> },
    { label: '导出管理', key: 'export', icon: <ExportOutlined />, children: <div>导出功能开发中...</div> },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="text" icon={<LeftOutlined />} onClick={() => navigate('/dashboard')}>
          返回列表
        </Button>
      </div>

      <div style={{ background: '#fff', padding: '16px 24px', borderRadius: 8 }}>
        <Title level={3} style={{ marginTop: 0 }}>{project.name}</Title>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={items.map(item => ({
            key: item.key,
            label: (<span>{item.icon} {item.label}</span>),
            children: item.children
          }))}
        />
      </div>
    </div>
  );
};

export default ProjectDetail;
