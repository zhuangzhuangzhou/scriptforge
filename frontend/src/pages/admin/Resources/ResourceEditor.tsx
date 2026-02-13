import React, { useState, useEffect } from 'react';
import { Form, Button, message, Spin } from 'antd';
import { SaveOutlined, ArrowLeftOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassInput, GlassTextArea } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import MarkdownEditor from '../../../components/MarkdownEditor';

// 深色主题提示框组件
const GlassAlert: React.FC<{
  type?: 'info' | 'warning' | 'error';
  title: string;
  description?: string;
}> = ({ type = 'info', title, description }) => {
  const colorMap = {
    info: {
      bg: 'bg-cyan-500/10',
      border: 'border-cyan-500/30',
      icon: 'text-cyan-400',
      title: 'text-cyan-300',
    },
    warning: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      icon: 'text-amber-400',
      title: 'text-amber-300',
    },
    error: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/30',
      icon: 'text-red-400',
      title: 'text-red-300',
    },
  };

  const colors = colorMap[type];

  return (
    <div className={`${colors.bg} ${colors.border} border rounded-lg p-4 flex items-start gap-3`}>
      <InfoCircleOutlined className={`${colors.icon} text-lg mt-0.5`} />
      <div>
        <div className={`${colors.title} font-medium`}>{title}</div>
        {description && (
          <div className="text-slate-400 text-sm mt-1">{description}</div>
        )}
      </div>
    </div>
  );
};

// 表单样式
const FORM_STYLES = `
  .resource-editor-form .ant-form-item-label > label {
    color: #cbd5e1 !important;
    font-weight: 500;
  }

  .resource-editor-form .ant-form-item-explain-error {
    color: #f87171 !important;
  }

  .resource-editor-form .ant-form-item-extra {
    color: #64748b !important;
  }

  .resource-editor-form .ant-form-item {
    margin-bottom: 20px;
  }
`;

const ResourceEditor: React.FC = () => {
  const { resourceId } = useParams<{ resourceId: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [content, setContent] = useState('');
  const [isBuiltin, setIsBuiltin] = useState(false);

  const isEditMode = !!resourceId;

  useEffect(() => {
    if (isEditMode) {
      loadResource();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resourceId]);

  const loadResource = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/ai-resources/${resourceId}`);
      const resource = response.data;
      form.setFieldsValue({
        name: resource.name,
        display_name: resource.display_name,
        description: resource.description,
        category: resource.category,
        visibility: resource.visibility,
      });
      setContent(resource.content || '');
      setIsBuiltin(resource.is_builtin || false);
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
      // 内置资源只提交允许修改的字段
      const data = isBuiltin
        ? {
            display_name: values.display_name,
            description: values.description,
            content,
          }
        : {
            ...values,
            content,
          };

      if (isEditMode) {
        await api.put(`/ai-resources/${resourceId}`, data);
        message.success('保存成功');
      } else {
        await api.post('/ai-resources', data);
        message.success('创建成功');
      }

      navigate('/admin/resources');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 h-full overflow-y-auto bg-slate-950">
        <div className="flex justify-center items-center py-20">
          <Spin size="large" tip="加载中..." />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <style>{FORM_STYLES}</style>

      {/* 页面标题栏 */}
      <div className="mb-6 flex items-center gap-4">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/admin/resources')}
          className="flex items-center"
        >
          返回
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            {isEditMode ? '编辑资源' : '新建资源'}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {isEditMode ? '修改资源文档内容' : '创建新的资源文档'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：基本信息 */}
        <div className="col-span-1">
          <GlassCard className="sticky top-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">基本信息</h2>

            {isBuiltin && (
              <div className="mb-4">
                <GlassAlert
                  type="info"
                  title="内置资源"
                  description="内置资源只能修改显示名称、描述和内容"
                />
              </div>
            )}

            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              className="resource-editor-form"
              initialValues={{
                visibility: 'public',
                category: 'methodology',
              }}
            >
              <Form.Item
                label="资源名称"
                name="name"
                rules={[{ required: true, message: '请输入资源名称' }]}
                extra="唯一标识，只能包含字母、数字和下划线"
              >
                <GlassInput
                  placeholder="例如：adapt_method_default"
                  disabled={isEditMode}
                />
              </Form.Item>

              <Form.Item
                label="显示名称"
                name="display_name"
                rules={[{ required: true, message: '请输入显示名称' }]}
              >
                <GlassInput placeholder="例如：网文改编方法论" />
              </Form.Item>

              <Form.Item label="描述" name="description">
                <GlassTextArea rows={3} placeholder="简要描述此资源的用途" />
              </Form.Item>

              <Form.Item label="分类" name="category">
                <GlassSelect
                  disabled={isBuiltin}
                  options={[
                    { value: 'methodology', label: '方法论' },
                    { value: 'output_style', label: '输出风格' },
                    { value: 'qa_rules', label: '质检标准' },
                    { value: 'template', label: '模板案例' },
                  ]}
                />
              </Form.Item>

              <Form.Item label="可见性" name="visibility">
                <GlassSelect
                  disabled={isBuiltin}
                  options={[
                    { value: 'public', label: '公共' },
                    { value: 'private', label: '私有' },
                  ]}
                />
              </Form.Item>

              <div className="flex gap-3 pt-2">
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  loading={saving}
                  className="flex-1"
                >
                  保存
                </Button>
                <Button onClick={() => navigate('/admin/resources')}>
                  取消
                </Button>
              </div>
            </Form>
          </GlassCard>
        </div>

        {/* 右侧：内容编辑器 */}
        <div className="col-span-2">
          <GlassCard>
            <h2 className="text-lg font-semibold text-slate-100 mb-4">
              资源内容
              <span className="text-red-400 ml-1">*</span>
            </h2>
            <MarkdownEditor
              value={content}
              onChange={setContent}
              height="calc(100vh - 280px)"
              showVariables={true}
            />
          </GlassCard>
        </div>
      </div>
    </div>
  );
};

export default ResourceEditor;
