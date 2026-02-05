import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Button, Card, Timeline, Tag, Row, Col, Typography, Empty, Modal } from 'antd';
import { PlayCircleOutlined, CheckCircleOutlined, ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';
import ConsistencyResult from '../../components/ConsistencyResult';

const { Text } = Typography;

interface Batch {
  id: string;
  batch_number: number;
  start_chapter: number;
  end_chapter: number;
  breakdown_status: string;
}

interface BreakdownResult {
  batch_id: string;
  conflicts?: any[];
  plot_hooks?: any[];
  characters?: any[];
  scenes?: any[];
  emotions?: any[];
  consistency_status?: string;
  consistency_score?: number;
  consistency_results?: any;
  consistency_details?: any;
  status?: string;
}

const PlotBreakdown: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [loading, setLoading] = useState(false);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [resultVisible, setResultVisible] = useState(false);
  const [resultData, setResultData] = useState<BreakdownResult | null>(null);

  const loadBatches = useCallback(async () => {
    if (!projectId) return;
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
  }, [projectId]);

  useEffect(() => {
    loadBatches();
  }, [loadBatches]);

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
      loadBatches();
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const viewResult = async (batchId: string) => {
    try {
      const response = await fetch(`/api/v1/breakdown/results/${batchId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('加载结果失败');
      const data = await response.json();
      setResultData(data);
      setResultVisible(true);
    } catch (error) {
      console.error(error);
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
        <Card
          title="批次时间轴"
          bordered={false}
          style={{ height: '100%' }}
          extra={<Button onClick={loadBatches}>刷新</Button>}
        >
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
                      </Button>,
                      batch.breakdown_status === 'completed' ? (
                        <Button size="small" onClick={() => viewResult(batch.id)}>
                          查看结果
                        </Button>
                      ) : null
                    ].filter(Boolean)}
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
            projectId={projectId}
            onSkillsChange={setSelectedSkills}
          />
        </Card>
      </Col>

      <Modal
        title="拆解结果"
        open={resultVisible}
        onCancel={() => setResultVisible(false)}
        footer={null}
        width={900}
      >
        {resultData ? (
          <>
            <ConsistencyResult
              results={resultData.consistency_results || resultData.consistency_details || {}}
              score={resultData.consistency_score || 0}
              status={resultData.consistency_status || resultData.status || 'unknown'}
            />
            {/* 调试用：折叠显示原始数据 */}
            {/*
            <details style={{ marginTop: 20, color: '#999', cursor: 'pointer' }}>
              <summary>查看原始数据</summary>
              <pre style={{ whiteSpace: 'pre-wrap', marginTop: 10 }}>
                {JSON.stringify(resultData, null, 2)}
              </pre>
            </details>
            */}
          </>
        ) : (
          <Empty description="暂无结果数据" />
        )}
      </Modal>
    </Row>
  );
};

export default PlotBreakdown;
