import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, message, Space, Spin } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import MonacoEditor from '@monaco-editor/react';
import api from '../../../services/api';

const { TextArea } = Input;
const { Option } = Select;

interface SkillEditorProps {
  skillId: string | null; // null 表示新建
  onSaved: () => void;
  onCancel: () => void;
}

interface SkillFormData {
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  prompt_template?: string;
  input_schema?: any;
  output_schema?: any;
  model_config?: any;
  example_input?: any;
  example_output?: any;
  visibility: string;
}

const SkillEditor: React.FC<SkillEditorProps> = ({ skillId, onSaved, onCancel }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState('');
  const [inputSchema, setInputSchema] = useState('{}');
  const [outputSchema, setOutputSchema] = useState('{}');
  const [modelConfig, setModelConfig] = useState('{"temperature": 0.7, "max_tokens": 2000}');
  const [exampleInput, setExampleInput] = useState('{}');
  const [exampleOutput, setExampleOutput] = useState('{}');

  const isEditMode = !!skillId;

  useEffect(() => {
    if (isEditMode) {
      loadSkill();
    } else {
      form.resetFields();
      setPromptTemplate('');
      setInputSchema('{}');
      setOutputSchema('{}');
      setModelConfig('{"temperature": 0.7, "max_tokens": 2000}');
      setExampleInput('{}');
      setExampleOutput('{}');
    }
  }, [skillId]);

  const loadSkill = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/skills/${skillId}`);
      const skill = response.data;

      form.setFieldsValue({
        name: skill.name,
        display_name: skill.display_name,
        description: skill.description,
        category: skill.category,
        visibility: skill.visibility,
      });

      setPromptTemplate(skill.prompt_template || '');
      setInputSchema(JSON.stringify(skill.input_schema || {}, null, 2));
      setOutputSchema(JSON.stringify(skill.output_schema || {}, null, 2));
      setModelConfig(JSON.stringify(skill.model_config || { temperature: 0.7, max_tokens: 2000 }, null, 2));
      setExampleInput(JSON.stringify(skill.example_input || {}, null, 2));
      setExampleOutput(JSON.stringify(skill.example_output || {}, null, 2));
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      const data: SkillFormData = {
        ...values,
        prompt_template: promptTemplate,
        input_schema: JSON.parse(inputSchema),
        output_schema: JSON.parse(outputSchema),
        model_config: JSON.parse(modelConfig),
        example_input: JSON.parse(exampleInput),
        example_output: JSON.parse(exampleOutput),
      };

      if (isEditMode) {
        await api.put(`/skills/${skillId}`, data);
        message.success('保存成功');
      } else {
        await api.post('/skills', data);
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
      <Form.Item
        label="Skill 名称"
        name="name"
        rules={[{ required: true, message: '请输入 Skill 名称' }]}
        extra="唯一标识，只能包含字母、数字和下划线"
      >
        <Input placeholder="例如：conflict_extraction" disabled={isEditMode} />
      </Form.Item>

      <Form.Item
        label="显示名称"
        name="display_name"
        rules={[{ required: true, message: '请输入显示名称' }]}
      >
        <Input placeholder="例如：冲突提取" />
      </Form.Item>

      <Form.Item label="描述" name="description">
        <TextArea rows={2} placeholder="简要描述此 Skill 的功能" />
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

      <Form.Item label="Prompt 模板" required>
        <div className="border border-slate-700 rounded">
          <MonacoEditor
            height="250px"
            language="markdown"
            theme="vs-dark"
            value={promptTemplate}
            onChange={(value) => setPromptTemplate(value || '')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              wordWrap: 'on',
            }}
          />
        </div>
        <div className="text-xs text-slate-500 mt-1">
          使用 {'{变量名}'} 引用输入参数，例如：{'{chapters_text}'}
        </div>
      </Form.Item>

      <div className="grid grid-cols-2 gap-4">
        <Form.Item label="输入 Schema (JSON)">
          <div className="border border-slate-700 rounded">
            <MonacoEditor
              height="150px"
              language="json"
              theme="vs-dark"
              value={inputSchema}
              onChange={(value) => setInputSchema(value || '{}')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
              }}
            />
          </div>
        </Form.Item>

        <Form.Item label="输出 Schema (JSON)">
          <div className="border border-slate-700 rounded">
            <MonacoEditor
              height="150px"
              language="json"
              theme="vs-dark"
              value={outputSchema}
              onChange={(value) => setOutputSchema(value || '{}')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
              }}
            />
          </div>
        </Form.Item>
      </div>

      <Form.Item label="模型配置 (JSON)">
        <div className="border border-slate-700 rounded">
          <MonacoEditor
            height="120px"
            language="json"
            theme="vs-dark"
            value={modelConfig}
            onChange={(value) => setModelConfig(value || '{}')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
            }}
          />
        </div>
      </Form.Item>

      <div className="grid grid-cols-2 gap-4">
        <Form.Item label="示例输入 (JSON)">
          <div className="border border-slate-700 rounded">
            <MonacoEditor
              height="150px"
              language="json"
              theme="vs-dark"
              value={exampleInput}
              onChange={(value) => setExampleInput(value || '{}')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
              }}
            />
          </div>
        </Form.Item>

        <Form.Item label="示例输出 (JSON)">
          <div className="border border-slate-700 rounded">
            <MonacoEditor
              height="150px"
              language="json"
              theme="vs-dark"
              value={exampleOutput}
              onChange={(value) => setExampleOutput(value || '{}')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
              }}
            />
          </div>
        </Form.Item>
      </div>

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

export default SkillEditor;
