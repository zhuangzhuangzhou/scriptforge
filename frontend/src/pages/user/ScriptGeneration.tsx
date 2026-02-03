import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Layout, Button, List, Card, Spin } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import SkillSelector from '../../components/SkillSelector';

const { Sider, Content } = Layout;

interface Script {
  id: string;
  episode_number: number;
  title: string;
  content: any;
  batch_id: string;
}

const ScriptGeneration: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [loading, setLoading] = useState(false);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedScript, setSelectedScript] = useState<Script | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  useEffect(() => {
    loadScripts();
  }, [projectId]);

  const loadScripts = async () => {
    try {
      // TODO: 实现加载剧本列表的API调用
    } catch (error) {
      console.error(error);
    }
  };

  const generateScript = async (batchId: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/scripts/generate', {
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
      if (!response.ok) throw new Error('生成剧本失败');
      await loadScripts();
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={300} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">剧集列表</h2>
        </div>
        <List
          dataSource={scripts}
          renderItem={(script) => (
            <List.Item
              className="cursor-pointer hover:bg-gray-50 px-4"
              onClick={() => setSelectedScript(script)}
              style={{
                backgroundColor: selectedScript?.id === script.id ? '#e6f7ff' : 'transparent'
              }}
            >
              <List.Item.Meta
                title={`第${script.episode_number}集`}
                description={script.title}
              />
            </List.Item>
          )}
        />
      </Sider>
      <Content style={{ padding: '24px' }}>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">剧本生成</h1>
          <div className="space-x-2">
            <Button icon={<DownloadOutlined />}>下载本集</Button>
            <Button icon={<DownloadOutlined />}>全部打包</Button>
          </div>
        </div>

        {/* Skills选择器 */}
        <SkillSelector
          category="script"
          projectId={projectId}
          onSkillsChange={setSelectedSkills}
        />

        {selectedScript ? (
          <Card>
            <h2 className="text-xl font-semibold mb-4">{selectedScript.title}</h2>
            <div className="whitespace-pre-wrap">
              {JSON.stringify(selectedScript.content, null, 2)}
            </div>
          </Card>
        ) : (
          <Card>
            <p className="text-gray-500 text-center">请选择一个剧集查看内容</p>
          </Card>
        )}
      </Content>
    </Layout>
  );
};

export default ScriptGeneration;
