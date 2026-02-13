import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, message, Space, Spin } from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import MarkdownEditor from '../../../components/MarkdownEditor';

const { TextArea } = Input;
const { Option } = Select;

const TemplateEditor: React.FC = () => {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [content, setContent] = useState('');

  const isEditMode = !!templateId;

  useEffect(() => {
    if (isEditMode) {
      loadTemplate();
    }
  }, [templateId]);

  const loadTemplate = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/ai-resources/${templateId}`);
      const resource = response.data;

      // 检查是否是内置资源（用户不能直接编辑内置资源）
      if (resource.is_builtin) {
        message.warning('内置模板不能直接编辑，请先复制为自己的版本');
        navigate('/user/templates');
        return;
      }

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
      navigate('/user/templates');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    if (!content.trim()) {
      message.error('请输入模板内容');
      return;
    }

    setSaving(true);
    try {
      const data = {
        ...values,
        content,
      };

      if (isEditMode) {
        await api.put(`/ai-resources/${templateId}`, data);
        message.success('保存成功');
      } else {
        await api.post('/ai-resources', data);
        message.success('创建成功');
      }

      navigate('/user/templates');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12 h-full bg-slate-950">
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
            onClick={() => navigate('/user/templates')}
          >
            返回
          </Button>
          <h1 className="text-2xl font-bold text-slate-100 m-0">
            {isEditMode ? '编辑模板' : '新建模板'}
          </h1>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            visibility: 'private',
            category: 'methodology',
          }}
        >
          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              label="模板名称"
              name="name"
              rules={[
                { required: true, message: '请输入模板名称' },
                { pattern: /^[a-z0-9_]+$/, message: '只能包含小写字母、数字和下划线' },
              ]}
              extra="唯一标识，只能包含小写字母、数字和下划线"
            >
              <Input placeholder="例如：my_adapt_method" disabled={isEditMode} />
            </Form.Item>

            <Form.Item
              label="显示名称"
              name="display_name"
              rules={[{ required: true, message: '请输入显示名称' }]}
            >
              <Input placeholder="例如：我的改编方法论" />
            </Form.Item>
          </div>

          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="简要描述此模板的用途和特点" />
          </Form.Item>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              label="分类"
              name="category"
              rules={[{ required: true, message: '请选择分类' }]}
            >
              <Select disabled={isEditMode}>
                <Option value="methodology">方法论</Option>
                <Option value="output_style">输出风格</Option>
                <Option value="qa_rules">质检标准</Option>
                <Option value="template">模板案例</Option>
              </Select>
            </Form.Item>

            <Form.Item label="可见性" name="visibility">
              <Select>
                <Option value="private">仅自己可见</Option>
                <Option value="public">公开（其他用户可复制）</Option>
              </Select>
            </Form.Item>
          </div>

          <Form.Item label="模板内容 (Markdown)" required>
            <MarkdownEditor
              value={content}
              onChange={setContent}
              height="450px"
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
              <Button onClick={() => navigate('/user/templates')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </GlassCard>
    </div>
  );
};

export default TemplateEditor;
