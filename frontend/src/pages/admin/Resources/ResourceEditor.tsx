import React, { useState, useEffect } from 'react';
import { Form, Button, message, Space, Spin, Alert } from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassInput, GlassTextArea } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import MarkdownEditor from '../../../components/MarkdownEditor';

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
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
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
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <GlassCard>
        <div className="mb-4 flex items-center gap-4">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/admin/resources')}
          >
            返回
          </Button>
          <h1 className="text-2xl font-bold text-slate-100 m-0">
            {isEditMode ? '编辑资源' : '新建资源'}
          </h1>
        </div>

        {isBuiltin && (
          <Alert
            message="内置资源"
            description="内置资源只能修改显示名称、描述和内容，不能修改资源名称、分类和可见性。"
            type="info"
            showIcon
            className="mb-4"
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            visibility: 'public',
            category: 'methodology',
          }}
        >
          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              label={<span className="text-slate-300">资源名称</span>}
              name="name"
              rules={[{ required: true, message: '请输入资源名称' }]}
              extra={<span className="text-slate-500">唯一标识，只能包含字母、数字和下划线</span>}
            >
              <GlassInput placeholder="例如：adapt_method_default" disabled={isEditMode} />
            </Form.Item>

            <Form.Item
              label={<span className="text-slate-300">显示名称</span>}
              name="display_name"
              rules={[{ required: true, message: '请输入显示名称' }]}
            >
              <GlassInput placeholder="例如：网文改编方法论" />
            </Form.Item>
          </div>

          <Form.Item label={<span className="text-slate-300">描述</span>} name="description">
            <GlassTextArea rows={2} placeholder="简要描述此资源的用途" />
          </Form.Item>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item label={<span className="text-slate-300">分类</span>} name="category">
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

            <Form.Item label={<span className="text-slate-300">可见性</span>} name="visibility">
              <GlassSelect
                disabled={isBuiltin}
                options={[
                  { value: 'public', label: '公共' },
                  { value: 'private', label: '私有' },
                ]}
              />
            </Form.Item>
          </div>

          <Form.Item label={<span className="text-slate-300">资源内容 (Markdown)</span>} required>
            <MarkdownEditor
              value={content}
              onChange={setContent}
              height="500px"
              showVariables={true}
            />
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
              <Button onClick={() => navigate('/admin/resources')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </GlassCard>
    </div>
  );
};

export default ResourceEditor;
