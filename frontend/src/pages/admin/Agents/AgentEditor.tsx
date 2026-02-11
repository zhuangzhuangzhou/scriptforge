import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, message, Space, Spin } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import api from '../../../services/api';
import WorkflowEditor, { WorkflowConfig, SkillInfo } from '../../../components/WorkflowEditor';

const { TextArea } = Input;
const { Option } = Select;

interface AgentEditorProps {
  agentId: string | null; // null 表示新建
  onSaved: () => void;
  onCancel: () => void;
}

interface AgentFormData {
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  workflow: WorkflowConfig;
  visibility: string;
}

const defaultWorkflow: WorkflowConfig = {
  type: 'sequential',
  steps: [],
};

const AgentEditor: React.FC<AgentEditorProps> = ({ agentId, onSaved, onCancel }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [workflow, setWorkflow] = useState<WorkflowConfig>(defaultWorkflow);
  const [availableSkills, setAvailableSkills] = useState<SkillInfo[]>([]);

  const isEditMode = !!agentId;

  // 加载可用 Skills
  useEffect(() => {
    loadSkills();
  }, []);

  useEffect(() => {
    if (isEditMode) {
      loadAgent();
    } else {
      form.resetFields();
      setWorkflow(defaultWorkflow);
    }
  }, [agentId]);

  const loadSkills = async () => {
    try {
      const response = await api.get('/skills/available');
      setAvailableSkills(response.data || []);
    } catch (error) {
      console.error('加载 Skills 失败:', error);
    }
  };

  const loadAgent = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/simple-agents/${agentId}`);
      const agent = response.data;

      form.setFieldsValue({
        name: agent.name,
        display_name: agent.display_name,
        description: agent.description,
        category: agent.category,
        visibility: agent.visibility,
      });

      // 解析工作流配置
      const wf = agent.workflow || defaultWorkflow;
      setWorkflow({
        type: wf.type || 'sequential',
        max_iterations: wf.max_iterations,
        exit_condition: wf.exit_condition,
        steps: Array.isArray(wf.steps) ? wf.steps : [],
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    // 验证工作流
    if (workflow.steps.length === 0) {
      message.warning('请至少添加一个工作流步骤');
      return;
    }

    const hasEmptySkill = workflow.steps.some((s) => !s.skill);
    if (hasEmptySkill) {
      message.warning('请为所有步骤选择 Skill');
      return;
    }

    setSaving(true);
    try {
      const data: AgentFormData = {
        ...values,
        workflow,
      };

      if (isEditMode) {
        await api.put(`/simple-agents/${agentId}`, data);
        message.success('保存成功');
      } else {
        await api.post('/simple-agents', data);
        message.success('创建成功');
      }

      onSaved();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSave}
      initialValues={{
        visibility: 'public',
        category: 'breakdown',
      }}
    >
      <div className="grid grid-cols-2 gap-4">
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
      </div>

      <Form.Item label="描述" name="description">
        <TextArea rows={2} placeholder="简要描述此 Agent 的功能" />
      </Form.Item>

      <div className="grid grid-cols-2 gap-4">
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
      </div>

      <Form.Item label="工作流配置" required>
        <div className="h-[500px]">
          <WorkflowEditor
            value={workflow}
            onChange={setWorkflow}
            availableSkills={availableSkills}
          />
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
          <Button onClick={onCancel}>
            取消
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
};

export default AgentEditor;
