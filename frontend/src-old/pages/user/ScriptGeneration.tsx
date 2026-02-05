import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Button, List, Card, Layout, Typography, Empty, Tag, Space, Select, message } from 'antd';
import { DownloadOutlined, FileTextOutlined, RobotOutlined } from '@ant-design/icons';
import SkillSelector from '../../components/SkillSelector';

const { Content, Sider } = Layout;
const { Title, Text } = Typography;

interface Script {
  id: string;
  episode_number: number;
  title: string;
  content: any;
  batch_id: string;
}

interface Batch {
  id: string;
  batch_number: number;
  start_chapter: number;
  end_chapter: number;
  script_status: string;
  breakdown_status: string;
}

const ScriptGeneration: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedScript, setSelectedScript] = useState<Script | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadScripts();
    loadBatches();
  }, [projectId]);

  const loadScripts = async () => {
    try {
      const response = await fetch(`/api/v1/scripts?project_id=${projectId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (!response.ok) throw new Error('加载失败');
      const data = await response.json();
      setScripts(data || []);
    } catch (error) {
      console.error(error);
    }
  };

  const loadBatches = async () => {
    try {
      const response = await fetch(`/api/v1/projects/${projectId}/batches`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (!response.ok) throw new Error('加载批次失败');
      const data = await response.json();
      setBatches(data || []);
      if (data && data.length > 0) {
        setSelectedBatchId(data[0].id);
      }
    } catch (error) {
      console.error(error);
    }
  };

  const generateScript = async () => {
    if (!selectedBatchId) {
      message.warning('请选择批次');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch('/api/v1/scripts/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          batch_id: selectedBatchId,
          selected_skills: selectedSkills
        })
      });
      if (!response.ok) throw new Error('启动剧本生成失败');
      message.success('已启动剧本生成');
    } catch (error) {
      message.error('启动失败');
    } finally {
      setLoading(false);
    }
  };

  const exportScript = async (format: 'pdf' | 'docx') => {
    if (!selectedScript) return;
    try {
      const response = await fetch('/api/v1/export/single', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          script_id: selectedScript.id,
          format
        })
      });
      if (!response.ok) throw new Error('导出失败');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedScript.title || 'script'}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      message.error('导出失败');
    }
  };

  const copyContent = async () => {
    if (!selectedScript) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(selectedScript.content, null, 2));
      message.success('已复制到剪贴板');
    } catch (error) {
      message.error('复制失败');
    }
  };

  return (
    <Layout style={{ background: '#fff', borderRadius: 8, overflow: 'hidden', border: '1px solid #f0f0f0', height: 'calc(100vh - 140px)' }}>
      <Sider width={320} theme="light" style={{ borderRight: '1px solid #f0f0f0', overflowY: 'auto' }}>
        <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={5} style={{ margin: 0 }}>剧集列表</Title>
          <Button size="small" onClick={loadScripts}>刷新</Button>
        </div>
        <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
          <Select
            style={{ width: '100%' }}
            placeholder="选择批次"
            value={selectedBatchId}
            onChange={setSelectedBatchId}
          >
            {batches.map(batch => (
              <Select.Option key={batch.id} value={batch.id}>
                批次 {batch.batch_number} ({batch.start_chapter}-{batch.end_chapter})
              </Select.Option>
            ))}
          </Select>
        </div>
        <List
          dataSource={scripts}
          renderItem={(script) => (
            <List.Item
              className="cursor-pointer hover:bg-gray-50"
              onClick={() => setSelectedScript(script)}
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                background: selectedScript?.id === script.id ? '#e6f7ff' : 'transparent',
                borderLeft: selectedScript?.id === script.id ? '3px solid #1677ff' : '3px solid transparent'
              }}
            >
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text strong>第 {script.episode_number} 集</Text>
                  <Tag color="blue">已生成</Tag>
                </div>
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" ellipsis>{script.title}</Text>
                </div>
              </div>
            </List.Item>
          )}
          locale={{ emptyText: '暂无生成的剧本' }}
        />
        <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
           <Button
             type="dashed"
             block
             icon={<RobotOutlined />}
             onClick={generateScript}
             loading={loading}
           >
             自动生成下一集
           </Button>
        </div>
      </Sider>
      <Content style={{ padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        {selectedScript ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <div>
                <Title level={3} style={{ margin: 0 }}>{selectedScript.title}</Title>
                <Text type="secondary">第 {selectedScript.episode_number} 集</Text>
              </div>
              <Space>
                <Button icon={<DownloadOutlined />} onClick={() => exportScript('pdf')}>导出 PDF</Button>
                <Button icon={<FileTextOutlined />} onClick={copyContent}>复制内容</Button>
              </Space>
            </div>
            <Card bordered={false} style={{ flex: 1, background: '#fafafa' }}>
              <div style={{ fontFamily: 'Courier New, monospace', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(selectedScript.content, null, 2)}
              </div>
            </Card>
          </>
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Empty 
              image={Empty.PRESENTED_IMAGE_SIMPLE} 
              description="选择左侧剧集预览，或配置下方技能开始生成"
            >
               <div style={{ maxWidth: 400, margin: '20px auto', textAlign: 'left' }}>
                 <SkillSelector 
                    category="script" 
                    projectId={projectId} 
                    onSkillsChange={setSelectedSkills} 
                 />
               </div>
            </Empty>
          </div>
        )}
      </Content>
    </Layout>
  );
};

export default ScriptGeneration;
