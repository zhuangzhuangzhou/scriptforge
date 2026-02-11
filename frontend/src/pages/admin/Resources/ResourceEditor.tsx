import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, message, Space, Spin } from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import MonacoEditor from '@monaco-editor/react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';

const { TextArea } = Input;
const { Option } = Select;

const ResourceEditor: React.FC = () => {
  const { resourceId } = useParams<{ resourceId: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [content, setContent] = useState('');

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
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      const data = {
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
              label="资源名称"
              name="name"
              rules={[{ required: true, message: '请输入资源名称' }]}
              extra="唯一标识，只能包含字母、数字和下划线"
            >
              <Input placeholder="例如：adapt_method_default" disabled={isEditMode} />
            </Form.Item>

            <Form.Item
              label="显示名称"
              name="display_name"
              rules={[{ required: true, message: '请输入显示名称' }]}
            >
              <Input placeholder="例如：网文改编方法论" />
            </Form.Item>
          </div>

          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="简要描述此资源的用途" />
          </Form.Item>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item label="分类" name="category">
              <Select>
                <Option value="methodology">方法论</Option>
                <Option value="output_style">输出风格</Option>
                <Option value="template">模板</Option>
                <Option value="example">示例</Option>
              </Select>
            </Form.Item>

            <Form.Item label="可见性" name="visibility">
              <Select>
                <Option value="public">公共</Option>
                <Option value="private">私有</Option>
              </Select>
            </Form.Item>
          </div>

          <Form.Item label="资源内容 (Markdown)" required>
            <div className="border border-slate-700 rounded">
              <MonacoEditor
                height="500px"
                language="markdown"
                theme="vs-dark"
                value={content}
                onChange={(value) => setContent(value || '')}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  wordWrap: 'on',
                  lineNumbers: 'on',
                }}
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
