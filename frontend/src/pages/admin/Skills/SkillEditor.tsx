import React, { useState, useEffect } from 'react';
import { Form, Button, message, Spin, Tag, Collapse } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import MonacoEditor from '@monaco-editor/react';
import api from '../../../services/api';
import { GlassInput, GlassTextArea } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import MarkdownEditor from '../../../components/MarkdownEditor';

// 表单样式
const FORM_STYLES = `
  .skill-editor-form .ant-form-item-label > label {
    color: #cbd5e1 !important;
    font-weight: 500;
  }

  .skill-editor-form .ant-form-item-explain-error {
    color: #f87171 !important;
  }

  .skill-editor-form .ant-form-item-extra {
    color: #64748b !important;
  }

  .skill-editor-form .ant-form-item {
    margin-bottom: 12px;
  }

  .skill-editor-form .ant-collapse {
    background: transparent;
    border: none;
  }

  .skill-editor-form .ant-collapse-item {
    border: 1px solid rgba(51, 65, 85, 0.5) !important;
    border-radius: 8px !important;
    margin-bottom: 8px;
    background: rgba(15, 23, 42, 0.3);
  }

  .skill-editor-form .ant-collapse-header {
    color: #cbd5e1 !important;
    padding: 8px 12px !important;
  }

  .skill-editor-form .ant-collapse-content {
    border-top: 1px solid rgba(51, 65, 85, 0.5) !important;
    background: transparent !important;
  }

  .skill-editor-form .ant-collapse-content-box {
    padding: 12px !important;
  }
`;

interface SkillEditorProps {
  skillId: string | null;
  onSaved: () => void;
  onCancel: () => void;
}

interface SkillFormData {
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  prompt_template?: string;
  input_schema?: unknown;
  output_schema?: unknown;
  model_config?: unknown;
  example_input?: unknown;
  example_output?: unknown;
  visibility: string;
}

const SkillEditor: React.FC<SkillEditorProps> = ({ skillId, onSaved }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState('');
  const [inputSchema, setInputSchema] = useState('{}');
  const [outputSchema, setOutputSchema] = useState('{}');
  const [modelConfig, setModelConfig] = useState('{"temperature": 0.7, "max_tokens": 2000}');
  const [exampleInput, setExampleInput] = useState('{}');
  const [exampleOutput, setExampleOutput] = useState('{}');
  const [isBuiltin, setIsBuiltin] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [visibility, setVisibility] = useState('public');

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
      setIsBuiltin(false);
      setDisplayName('');
      setVisibility('public');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
      setIsBuiltin(skill.is_builtin || false);
      setDisplayName(skill.display_name || '');
      setVisibility(skill.visibility || 'public');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: Record<string, unknown>) => {
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
      } as SkillFormData;

      if (isEditMode) {
        await api.put(`/skills/${skillId}`, data);
        message.success('保存成功');
      } else {
        await api.post('/skills', data);
        message.success('创建成功');
      }

      onSaved();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  // JSON 编辑器组件
  const JsonEditor = ({ value, onChange, height = '100px' }: { value: string; onChange: (v: string) => void; height?: string }) => (
    <div className="border border-slate-700 rounded overflow-hidden">
      <MonacoEditor
        height={height}
        language="json"
        theme="vs-dark"
        value={value}
        onChange={(v) => onChange(v || '{}')}
        options={{
          minimap: { enabled: false },
          fontSize: 12,
          lineNumbers: 'off',
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
      />
    </div>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <>
      <style>{FORM_STYLES}</style>

      <div className="flex gap-6" style={{ height: 'calc(85vh - 120px)' }}>
        {/* 左侧：Prompt 模板编辑器 */}
        <div className="flex-1 flex flex-col overflow-hidden -mt-2">
          <MarkdownEditor
            value={promptTemplate}
            onChange={setPromptTemplate}
            height="100%"
            showVariables={true}
            showSplitView={false}
          />
        </div>

        {/* 右侧：配置面板 */}
        <div className="w-80 flex flex-col gap-2">
          {/* 顶部：标题和保存按钮 */}
          <div className="h-[38px] flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              {isEditMode && displayName && (
                <span className="text-slate-300 text-sm font-medium truncate" title={displayName}>
                  {displayName}
                </span>
              )}
              {isEditMode && isBuiltin && <Tag color="gold">内置</Tag>}
              {isEditMode && (
                <Tag color={visibility === 'public' ? 'green' : 'orange'}>
                  {visibility === 'public' ? '公共' : '私有'}
                </Tag>
              )}
            </div>
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={() => form.submit()}
              className="flex-shrink-0"
            >
              保存
            </Button>
          </div>

          {/* 配置卡片 */}
          <div className="flex-1 bg-slate-900/50 rounded-xl border border-slate-800/50 overflow-y-auto">
            {/* 内置资源提示 */}
            {isBuiltin && (
              <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/30 rounded-t-xl">
                <div className="text-amber-400 text-xs">内置 Skill - 部分字段不可修改</div>
              </div>
            )}

            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              className="skill-editor-form"
              initialValues={{
                visibility: 'public',
                category: 'breakdown',
              }}
            >
              <div className="p-4 space-y-3">
                {/* 基本信息 */}
                <div className="grid grid-cols-2 gap-3">
                  <Form.Item
                    label="Skill 名称"
                    name="name"
                    rules={[{ required: true, message: '请输入' }]}
                    extra="唯一标识"
                    className="mb-0"
                  >
                    <GlassInput
                      placeholder="conflict_extraction"
                      disabled={isEditMode}
                    />
                  </Form.Item>

                  <Form.Item
                    label="分类"
                    name="category"
                    className="mb-0"
                  >
                    <GlassSelect
                      disabled={isBuiltin}
                      options={[
                        { value: 'breakdown', label: '拆解' },
                        { value: 'qa', label: '质检' },
                        { value: 'script', label: '剧本' },
                      ]}
                    />
                  </Form.Item>
                </div>

                <Form.Item
                  label="显示名称"
                  name="display_name"
                  rules={[{ required: true, message: '请输入' }]}
                  className="mb-0"
                >
                  <GlassInput placeholder="冲突提取" />
                </Form.Item>

                <Form.Item
                  label="可见性"
                  name="visibility"
                  className="mb-0"
                >
                  <GlassSelect
                    disabled={isBuiltin}
                    options={[
                      { value: 'public', label: '公共' },
                      { value: 'private', label: '私有' },
                    ]}
                  />
                </Form.Item>

                <Form.Item label="描述" name="description" className="mb-0">
                  <GlassTextArea
                    rows={2}
                    placeholder="简要描述此 Skill 的功能"
                    className="resize-none"
                  />
                </Form.Item>

                {/* Schema 配置（折叠面板） */}
                <Collapse
                  ghost
                  defaultActiveKey={['model']}
                  items={[
                    {
                      key: 'model',
                      label: '模型配置',
                      children: <JsonEditor value={modelConfig} onChange={setModelConfig} />,
                    },
                    {
                      key: 'input',
                      label: '输入 Schema',
                      children: <JsonEditor value={inputSchema} onChange={setInputSchema} />,
                    },
                    {
                      key: 'output',
                      label: '输出 Schema',
                      children: <JsonEditor value={outputSchema} onChange={setOutputSchema} />,
                    },
                    {
                      key: 'example_input',
                      label: '示例输入',
                      children: <JsonEditor value={exampleInput} onChange={setExampleInput} />,
                    },
                    {
                      key: 'example_output',
                      label: '示例输出',
                      children: <JsonEditor value={exampleOutput} onChange={setExampleOutput} />,
                    },
                  ]}
                />
              </div>
            </Form>
          </div>
        </div>
      </div>
    </>
  );
};

export default SkillEditor;
