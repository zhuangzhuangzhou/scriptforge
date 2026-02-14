import React, { useState, useEffect } from 'react';
import { Form, Button, message, Spin, Tag } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import api from '../../../services/api';
import { GlassModal } from '../../../components/ui/GlassModal';
import { GlassInput, GlassTextArea } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import MarkdownEditor from '../../../components/MarkdownEditor';

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
    margin-bottom: 16px;
  }
`;

interface ResourceEditorModalProps {
  open: boolean;
  resourceId?: string | null;
  onClose: () => void;
  onSuccess?: () => void;
  showVariables?: boolean;
}

const ResourceEditorModal: React.FC<ResourceEditorModalProps> = ({
  open,
  resourceId,
  onClose,
  onSuccess,
  showVariables = false,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [content, setContent] = useState('');
  const [isBuiltin, setIsBuiltin] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [visibility, setVisibility] = useState('public');

  const isEditMode = !!resourceId;

  useEffect(() => {
    if (open) {
      if (isEditMode) {
        loadResource();
      } else {
        // 新建模式，重置表单
        form.resetFields();
        setContent('');
        setIsBuiltin(false);
        setDisplayName('');
        setVisibility('public');
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, resourceId]);

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
      setDisplayName(resource.display_name || '');
      setVisibility(resource.visibility || 'public');
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

      onSuccess?.();
      onClose();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  // 生成弹窗标题
  const modalTitle = (
    <div className="flex items-center gap-2">
      <span>{isEditMode ? displayName || '编辑资源' : '新建资源'}</span>
      {isEditMode && isBuiltin && <Tag color="gold">内置</Tag>}
      {isEditMode && (
        <Tag color={visibility === 'public' ? 'green' : 'orange'}>
          {visibility === 'public' ? '公共' : '私有'}
        </Tag>
      )}
    </div>
  );

  return (
    <GlassModal
      title={modalTitle}
      open={open}
      onCancel={onClose}
      width="90vw"
      footer={null}
      closable={!saving}
      destroyOnClose
    >
      <style>{FORM_STYLES}</style>

      {loading ? (
        <div className="flex justify-center items-center py-20">
          <Spin size="large" tip="加载中..." />
        </div>
      ) : (
        <div className="flex gap-6" style={{ height: 'calc(85vh - 120px)' }}>
          {/* 左侧：内容编辑器 */}
          <div className="flex-1 flex flex-col overflow-hidden -mt-2">
            <MarkdownEditor
              value={content}
              onChange={setContent}
              height="100%"
              showVariables={showVariables}
              showSplitView={false}
            />
          </div>

          {/* 右侧：配置面板 */}
          <div className="w-80 flex flex-col gap-2">
            {/* 顶部占位（与左侧 tabs 高度一致） */}
            <div className="h-[38px] flex items-center justify-end">
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={() => form.submit()}
              >
                保存
              </Button>
            </div>

            {/* 卡片内容 */}
            <div className="flex-1 bg-slate-900/50 rounded-xl border border-slate-800/50">
              {/* 内置资源提示 */}
              {isBuiltin && (
                <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/30 rounded-t-xl">
                  <div className="text-amber-400 text-xs">内置资源 - 只能修改显示名称、描述和内容</div>
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
                <div className="p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <Form.Item
                      label="资源名称"
                      name="name"
                      rules={[{ required: true, message: '请输入' }]}
                      extra="唯一标识"
                      className="mb-0"
                    >
                      <GlassInput
                        placeholder="adapt_method_default"
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
                          { value: 'methodology', label: '方法论' },
                          { value: 'type_guide', label: '类型指南' },
                          { value: 'output_style', label: '输出风格' },
                          { value: 'qa_rules', label: '质检标准' },
                          { value: 'template', label: '模板案例' },
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
                    <GlassInput placeholder="网文改编方法论" />
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
                      rows={4}
                      placeholder="简要描述此资源的用途"
                      className="resize-none"
                    />
                  </Form.Item>
                </div>
              </Form>
            </div>
          </div>
        </div>
      )}
    </GlassModal>
  );
};

export default ResourceEditorModal;
