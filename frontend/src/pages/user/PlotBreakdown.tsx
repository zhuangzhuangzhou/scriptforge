import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Button, Card, Timeline, Tag, Row, Col, Typography, Empty } from 'antd';
import { PlayCircleOutlined, CheckCircleOutlined, ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';
import SkillSelector from '../../components/SkillSelector';

const { Text } = Typography;

interface Batch {
  id: string;
  batch_number: number;
  start_chapter: number;
  end_chapter: number;
  breakdown_status: string;
}

const PlotBreakdown: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [loading, setLoading] = useState(false);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  useEffect(() => {
    loadBatches();
  }, [projectId]);

  const loadBatches = async () => {
    try {
      const response = await fetch(`/api/v1/projects/${projectId}/batches`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('加载批次失败');
      const data = await response.json();
      setBatches(data);
    } catch (error) {
      console.error(error);
    }
  };

  const startBreakdown = async (batchId: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/breakdown/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          batch_id: batchId,
          selected_skills: selectedSkills
        })
      });
      if (!response.ok) throw new Error('启动拆解失败');
      // Refresh status logic here
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'processing';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircleOutlined />;
      case 'processing': return <SyncOutlined spin />;
      default: return <ClockCircleOutlined />;
    }
  };

  return (
    <Row gutter={24}>
      <Col span={16}>
        <Card title="批次时间轴" bordered={false} style={{ height: '100%' }}>
          {batches.length > 0 ? (
            <Timeline
              mode="left"
              items={batches.map(batch => ({
                color: batch.breakdown_status === 'completed' ? 'green' : 'blue',
                dot: getStatusIcon(batch.breakdown_status),
                children: (
                  <Card 
                    size="small" 
                    bordered={false} 
                    style={{ background: '#f9f9f9', marginBottom: 16 }}
                    actions={[
                      <Button 
                        type={batch.breakdown_status === 'pending' ? 'primary' : 'default'}
                        size="small"
                        icon={<PlayCircleOutlined />}
                        onClick={() => startBreakdown(batch.id)}
                        disabled={batch.breakdown_status === 'completed' || loading}
                      >
                        {batch.breakdown_status === 'processing' ? '处理中' : '开始拆解'}
                      </Button>
                    ]}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text strong>批次 {batch.batch_number}</Text>
                      <Tag color={getStatusColor(batch.breakdown_status)}>{batch.breakdown_status}</Tag>
                    </div>
                    <Text type="secondary">包含章节: {batch.start_chapter} - {batch.end_chapter}</Text>
                  </Card>
                )
              }))}
            />
          ) : (
            <Empty description="暂无批次信息" />
          )}
        </Card>
      </Col>
      <Col span={8}>
        <Card title="AI 技能配置" bordered={false}>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            选择需要应用于本轮剧情拆解的 AI 技能模型。
          </Text>
          <SkillSelector
            category="breakdown"
            selectedSkillIds={selectedSkills}
            onChange={setSelectedSkills}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default PlotBreakdown;
