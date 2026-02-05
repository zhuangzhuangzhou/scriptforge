import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Select, Input, Space, Modal, message, Tabs, List } from 'antd';
import { CodeOutlined, PlayCircleOutlined, HistoryOutlined, SaveOutlined } from '@ant-design/icons';
import type { Editor } from '@monaco-editor/react';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

interface SkillVersion {
  id: string;
  version: string;
  code: string;
  description: string;
  created_at: string;
  is_active: boolean;
}

interface SkillsEditorProps {
  skillId: string;
  skillName: string;
}

const SkillsEditor: React.FC<SkillsEditorProps> = ({ skillId, skillName }) => {
  const editorRef = useRef<Editor | null>(null);
  const [code, setCode] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('editor');
  const [versions, setVersions] = useState<SkillVersion[]>([]);
  const [description, setDescription] = useState<string>('');
  const [showVersionModal, setShowVersionModal] = useState(false);

  useEffect(() => {
    loadSkillCode();
    loadVersions();
  }, [skillId]);

  const loadSkillCode = async () => {
    try {
      const response = await fetch(`/api/v1/skills/code?skill_id=${skillId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('加载失败');
      const data = await response.json();
      if (data.active_version) {
        setCode(data.active_version.code);
        setDescription(data.active_version.description || '');
      }
    } catch (error) {
      message.error('加载Skill代码失败');
    }
  };

  const loadVersions = async () => {
    try {
      const response = await fetch(`/api/v1/skills/code?skill_id=${skillId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('加载版本失败');
      const data = await response.json();
      setVersions(data.versions || []);
    } catch (error) {
      message.error('加载版本历史失败');
    }
  };

  const handleSave = async () => {
    if (!code.trim()) {
      message.warning('代码不能为空');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/v1/skills/code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          skill_id: skillId,
          code: code,
          description: description
        })
      });

      if (!response.ok) throw new Error('保存失败');
      message.success('保存成功');
      loadVersions();
      loadSkillCode();
    } catch (error) {
      message.error('保存失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    Modal.info({
      title: '测试功能',
      content: 'Skill测试功能开发中...'
    });
  };

  const handleRollback = async (versionId: string) => {
    try {
      const response = await fetch(`/api/v1/skills/code/${versionId}/rollback`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('回滚失败');
      message.success('回滚成功');
      loadVersions();
      loadSkillCode();
    } catch (error) {
      message.error('回滚失败');
    }
  };

  const handleVersionSelect = (versionId: string) => {
    const version = versions.find(v => v.id === versionId);
    if (version) {
      setCode(version.code);
      setShowVersionModal(false);
    }
  };

  return (
    <div className="skills-editor">
      <Card
        title={
          <Space>
            <CodeOutlined />
            <span>{skillName} - 代码编辑器</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<HistoryOutlined />}
              onClick={() => setShowVersionModal(true)}
            >
              版本历史
            </Button>
            <Button
              icon={<PlayCircleOutlined />}
              onClick={handleTest}
            >
              测试
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={loading}
            >
              保存
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane
            tab="编辑器"
            key="editor"
          >
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                版本描述
              </label>
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="输入本次修改的描述..."
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Skill代码
              </label>
              <TextArea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                rows={20}
                className="font-mono text-sm"
                placeholder="输入Skill代码..."
              />
            </div>
          </TabPane>

          <TabPane
            tab="参数Schema"
            key="schema"
          >
            <div className="p-4 bg-gray-50 rounded">
              <p className="text-gray-500">
                定义Skill的输入参数Schema（JSON格式）
              </p>
              <TextArea
                rows={10}
                className="font-mono text-sm mt-2"
                placeholder={'{"type": "object", "properties": {...}}'}
              />
            </div>
          </TabPane>

          <TabPane
            tab="文档"
            key="docs"
          >
            <div className="p-4">
              <h4 className="mb-4">Skill开发指南</h4>
              <div className="prose max-w-none">
                <h5>基本结构</h5>
                <pre className="bg-gray-100 p-4 rounded text-sm">
{`class YourSkill(BaseSkill):
    def __init__(self):
        super().__init__(
            name="your_skill",
            description="你的Skill描述"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # 获取输入
        input_data = context.get("input", {})

        # 处理逻辑
        result = {...}

        # 返回结果
        return {"output": result}`}
                </pre>

                <h5>可用上下文</h5>
                <ul>
                  <li><code>context["input"]</code> - 输入数据</li>
                  <li><code>context["chapters"]</code> - 章节内容</li>
                  <li><code>context["breakdown_data"]</code> - Breakdown结果</li>
                  <li><code>context["model_adapter"]</code> - 模型适配器</li>
                </ul>
              </div>
            </div>
          </TabPane>
        </Tabs>
      </Card>

      {/* 版本历史弹窗 */}
      <Modal
        title="版本历史"
        open={showVersionModal}
        onCancel={() => setShowVersionModal(false)}
        footer={null}
        width={600}
      >
        <List
          dataSource={versions}
          renderItem={(version) => (
            <List.Item
              actions={[
                <Button
                  type="link"
                  onClick={() => handleVersionSelect(version.id)}
                >
                  查看
                </Button>,
                <Button
                  type="link"
                  onClick={() => handleRollback(version.id)}
                  disabled={version.is_active}
                >
                  {version.is_active ? '当前版本' : '回滚'}
                </Button>
              ]}
            >
              <List.Item.Meta
                title={`版本 ${version.version}`}
                description={
                  <div>
                    <p>{version.description || '无描述'}</p>
                    <p className="text-gray-400 text-xs">
                      创建时间: {new Date(version.created_at).toLocaleString()}
                    </p>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
};

export default SkillsEditor;
