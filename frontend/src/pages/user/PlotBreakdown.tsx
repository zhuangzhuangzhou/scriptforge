import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Layout, Button, Card, List, Spin } from 'antd';
import SkillSelector from '../../components/SkillSelector';

const { Sider, Content } = Layout;

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
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const [consoleVisible, setConsoleVisible] = useState(false);
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
    setConsoleVisible(true);
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
      const data = await response.json();
      // TODO: 连接WebSocket监听进度
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: '24px' }}>
        <h1 className="text-2xl font-bold mb-6">剧情拆解</h1>

        {/* Skills选择器 */}
        <SkillSelector
          category="breakdown"
          projectId={projectId}
          onSkillsChange={setSelectedSkills}
        />

        {/* 批次列表 */}
        <Card title="批次列表" className="mb-4">
          <List
            dataSource={batches}
            renderItem={(batch) => (
              <List.Item
                actions={[
                  <Button
                    type="primary"
                    onClick={() => startBreakdown(batch.id)}
                    disabled={loading || batch.breakdown_status === 'completed'}
                  >
                    {batch.breakdown_status === 'completed' ? '已完成' : '启动拆解'}
                  </Button>
                ]}
              >
                <List.Item.Meta
                  title={`批次 ${batch.batch_number}`}
                  description={`章节 ${batch.start_chapter}-${batch.end_chapter} | 状态: ${batch.breakdown_status}`}
                />
              </List.Item>
            )}
          />
        </Card>
      </Content>
    </Layout>
  );
};

export default PlotBreakdown;
