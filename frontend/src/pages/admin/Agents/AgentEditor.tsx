import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Form, Input, Select, Button, Card, message, Space } from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import axios from 'axios';
import MonacoEditor from '@monaco-editor/react';

const { TextArea } = Input;
const { Option } = Select;

interface AgentFormData {
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  workflow: any;
  visibility: string;
}

const AgentEditor: React.FC = () => {
  const navigate = useNavigate();
  const { agentId } = useParams<{ agentId: string }>();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [workflow, setWorkflow] = useState('{\n  "steps": []\n}');

  const isEditMode = agentId && agentId !== 'new';

  useEffect(() => {
    if (isEditMode) {
      loadAgent();
    }
  }, [agentId]);

  const loadAgent = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/v1/simple-agents/${agentId}`);
      const agent = response.data;

      form.setFieldsValue({
        name: agent.name,
        display_name: agent.display_name,
        description: agent.description,
        category: agent.category,
        visibility: agent.visibility,
      });

      setWorkflow(JSON.stringify(agent.workflow, null, 2));
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      const data: AgentFormData = {
        ...values,
        workflow: JSON.parse(workflow),
      };

      if (isEditMode) {
        await axios.put(`/api/v1/simple-agents/${agentId}`, data);
        message.success('保存成功');
      } else {
        await axios.post('/api/v1/simple-agents', data);
        message.success('创建成功');
      }

      navigate('/admin/agents');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6">
      <Card>
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold">
            {isEditMode ? '编辑 Agent' : '新建 Agent'}
          </h1>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/admin/agents')}
          >
            返回
          </Button>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            visibility: 'public',
            category: 'breakdown',
          }}
        >
          <Form.Item
            label="Agent 名称"
            name="name"
            rules={[{ required: true, message: '请输入 Agent 名称' }]}
            extra="唯一标识，只能包含字母、数字和下划线"
          >
            <Input placeholder="例如：breakdown_agent" disabled={isEditMode} />
          </Form.Item>

          <Form.Item
            label="显示名称"
            name="display_name"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="例如：剧情拆解 Agent" />
          </Form.Item>

          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="简要描述此 Agent 的功能" />
          </Form.Item>

          <Form.Item label="分类" name="category">
            <Select>
              <Option value="breakdown">拆解</Option>
              <Option value="qa">质检</Option>
              <Option value="script">剧本</Option>
            </Select>
          </Form.Item>

          <Form.Item label="可见性" name="visibility">
            <Select>
              <Option value="public">公共</Option>
              <Option value="private">私有</Option>
            </Select>
          </Form.Item>

          <Form.Item label="工作流配置 (JSON)" required>
            <div className="border rounded">
              <MonacoEditor
                height="400px"
                language="json"
                value={workflow}
                onChange={(value) => setWorkflow(value || '{}')}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                }}
              />
            </div>
            <div className="text-xs text-slate-500 mt-2">
              <p>工作流示例：</p>
              <pre className="bg-slate-100 p-2 rounded mt-1">
{`{
  "steps": [
    {
      "id": "step1",
      "skill": "conflict_extraction",
      "inputs": {
        "chapters_text": "\${context.chapters_text}"
      },
      "output_key": "conflicts"
    }
  ]
}`}
              </pre>
            </div>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={saving}
              >
                保存
              </Button>
              <Button onClick={() => navigate('/admin/agents')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default AgentEditor;
