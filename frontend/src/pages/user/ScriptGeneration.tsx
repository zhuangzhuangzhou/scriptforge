import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Button, List, Card, Layout, Typography, Empty, Tag, Space } from 'antd';
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

const ScriptGeneration: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedScript, setSelectedScript] = useState<Script | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  useEffect(() => {
    loadScripts();
  }, [projectId]);

  const loadScripts = async () => {
    // Mock scripts for UI preview
    // setScripts([{ id: '1', episode_number: 1, title: '初入江湖', content: { scene: '...' }, batch_id: '1' }]);
  };

  return (
    <Layout style={{ background: '#fff', borderRadius: 8, overflow: 'hidden', border: '1px solid #f0f0f0', height: 'calc(100vh - 140px)' }}>
      <Sider width={320} theme="light" style={{ borderRight: '1px solid #f0f0f0', overflowY: 'auto' }}>
        <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
          <Title level={5} style={{ margin: 0 }}>剧集列表</Title>
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
           <Button type="dashed" block icon={<RobotOutlined />}>自动生成下一集</Button>
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
                <Button icon={<DownloadOutlined />}>导出 PDF</Button>
                <Button icon={<FileTextOutlined />}>复制内容</Button>
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
                    selectedSkillIds={selectedSkills}
                    onChange={setSelectedSkills}
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
