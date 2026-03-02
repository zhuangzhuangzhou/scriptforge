import React, { useState, useEffect, useRef } from 'react';
import { Button, Form, InputNumber, message, Space, Switch, Popconfirm, Tag } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, CheckCircleOutlined, CloseCircleOutlined, StarOutlined, StarFilled } from '@ant-design/icons';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassModal } from '../../../components/ui/GlassModal';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassInput, GlassTextArea } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { modelApi, providerApi, AIModel, AIModelCreate, AIModelUpdate, Provider } from '../../../services/modelManagementApi';
import { extractArrayData } from '../../../utils/apiHelpers';

// 表单样式
const FORM_STYLES = `
  .model-form .ant-form-item-label > label {
    color: #cbd5e1 !important;
  }
  .model-form .ant-form-item-extra {
    color: #64748b !important;
  }
`;

const ModelConfiguration: React.FC = () => {
  // 状态管理
  const [models, setModels] = useState<AIModel[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingModel, setEditingModel] = useState<AIModel | null>(null);
  const [selectedProviderId, setSelectedProviderId] = useState<string | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [form] = Form.useForm();
  const initialized = useRef(false);

  // 获取提供商列表
  const fetchProviders = async () => {
    try {
      const response = await providerApi.getProviders();
      setProviders(extractArrayData<Provider>(response.data));
    } catch (error) {
      console.error('获取提供商列表失败:', error);
    }
  };

  // 获取模型列表
  const fetchModels = async () => {
    setLoading(true);
    try {
      const response = await modelApi.getModels(selectedProviderId);
      setModels(extractArrayData<AIModel>(response.data));
    } catch (error) {
      console.error('获取模型列表失败:', error);
      message.error('获取模型列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialized.current) {
      fetchProviders();
      fetchModels();
      initialized.current = true;
    }
  }, []);

  useEffect(() => {
    if (initialized.current) {
      fetchModels();
    }
  }, [selectedProviderId]);

  // 创建模型
  const handleCreate = () => {
    setEditingModel(null);
    form.resetFields();
    form.setFieldsValue({
      timeout_seconds: 120,
      temperature_default: 0.7,
      supports_streaming: true,
      supports_function_calling: false,
    });
    setIsModalVisible(true);
  };

  // 编辑模型
  const handleEdit = (record: AIModel) => {
    setEditingModel(record);
    form.setFieldsValue({
      provider_id: record.provider_id,
      model_key: record.model_key,
      display_name: record.display_name,
      model_type: record.model_type,
      max_tokens: record.max_tokens,
      max_input_tokens: record.max_input_tokens,
      max_output_tokens: record.max_output_tokens,
      timeout_seconds: record.timeout_seconds,
      temperature_default: record.temperature_default,
      supports_streaming: record.supports_streaming,
      supports_function_calling: record.supports_function_calling,
      description: record.description,
    });
    setIsModalVisible(true);
  };

  // 删除模型
  const handleDelete = async (id: string) => {
    try {
      await modelApi.deleteModel(id);
      message.success('删除成功');
      fetchModels();
    } catch (error: any) {
      console.error('删除模型失败:', error);
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  // 启用/禁用模型
  const handleToggle = async (id: string) => {
    try {
      await modelApi.toggleModel(id);
      message.success('状态更新成功');
      fetchModels();
    } catch (error: any) {
      console.error('更新状态失败:', error);
      message.error(error.response?.data?.detail || '状态更新失败');
    }
  };

  // 设置为默认模型
  const handleSetDefault = async (id: string) => {
    try {
      await modelApi.setDefaultModel(id);
      message.success('已设置为默认模型');
      fetchModels();
    } catch (error: any) {
      console.error('设置默认模型失败:', error);
      message.error(error.response?.data?.detail || '设置失败');
    }
  };

  // 保存模型
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingModel) {
        // 更新
        const updateData: AIModelUpdate = {
          display_name: values.display_name,
          model_type: values.model_type,
          max_tokens: values.max_tokens,
          max_input_tokens: values.max_input_tokens,
          max_output_tokens: values.max_output_tokens,
          timeout_seconds: values.timeout_seconds,
          temperature_default: values.temperature_default,
          supports_streaming: values.supports_streaming,
          supports_function_calling: values.supports_function_calling,
          description: values.description,
        };
        await modelApi.updateModel(editingModel.id, updateData);
        message.success('更新成功');
      } else {
        // 创建
        const createData: AIModelCreate = {
          provider_id: values.provider_id,
          model_key: values.model_key,
          display_name: values.display_name,
          model_type: values.model_type,
          max_tokens: values.max_tokens,
          max_input_tokens: values.max_input_tokens,
          max_output_tokens: values.max_output_tokens,
          timeout_seconds: values.timeout_seconds,
          temperature_default: values.temperature_default,
          supports_streaming: values.supports_streaming,
          supports_function_calling: values.supports_function_calling,
          description: values.description,
        };
        await modelApi.createModel(createData);
        message.success('创建成功');
      }
      
      setIsModalVisible(false);
      fetchModels();
    } catch (error: any) {
      console.error('保存失败:', error);
      if (error.errorFields) {
        message.error('请检查表单填写');
      } else {
        message.error(error.response?.data?.detail || '保存失败');
      }
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '模型名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: AIModel) => (
        <Space>
          <span>{text}</span>
          {record.is_default && <StarFilled style={{ color: '#faad14' }} />}
        </Space>
      ),
    },
    {
      title: '提供商',
      dataIndex: 'provider_name',
      key: 'provider_name',
    },
    {
      title: '模型标识',
      dataIndex: 'model_key',
      key: 'model_key',
    },
    {
      title: '类型',
      dataIndex: 'model_type',
      key: 'model_type',
      width: 100,
    },
    {
      title: 'Token 限制',
      key: 'tokens',
      width: 150,
      render: (_: any, record: AIModel) => (
        <div style={{ fontSize: 12 }}>
          <div>总: {record.max_tokens || '-'}</div>
          <div style={{ color: '#888' }}>
            输入: {record.max_input_tokens || '-'} / 输出: {record.max_output_tokens || '-'}
          </div>
        </div>
      ),
    },
    {
      title: '超时(秒)',
      dataIndex: 'timeout_seconds',
      key: 'timeout_seconds',
      width: 100,
    },
    {
      title: '功能',
      key: 'features',
      width: 120,
      render: (_: any, record: AIModel) => (
        <Space direction="vertical" size="small">
          {record.supports_streaming && <Tag color="blue">流式</Tag>}
          {record.supports_function_calling && <Tag color="green">函数调用</Tag>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 100,
      render: (enabled: boolean, record: AIModel) => (
        <Switch
          checked={enabled}
          onChange={() => handleToggle(record.id)}
          checkedChildren={<CheckCircleOutlined />}
          unCheckedChildren={<CloseCircleOutlined />}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: AIModel) => (
        <Space size="small">
          {!record.is_default && (
            <Button
              type="link"
              size="small"
              icon={<StarOutlined />}
              onClick={() => handleSetDefault(record.id)}
            >
              设为默认
            </Button>
          )}
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除？"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 根据状态筛选过滤模型
  const filteredModels = models.filter(model => {
    if (statusFilter !== undefined && statusFilter !== '') {
      return model.is_enabled === (statusFilter === 'enabled');
    }
    return true;
  });
  return (
    <div className="p-6">
      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <h2 className="m-0 text-xl font-semibold text-slate-100">模型配置</h2>
            <GlassSelect
              style={{ width: 200 }}
              placeholder="筛选提供商"
              allowClear
              value={selectedProviderId}
              onChange={setSelectedProviderId}
              options={providers.map(p => ({
                label: p.display_name,
                value: p.id,
              }))}
            />
            <GlassSelect
              style={{ width: 150 }}
              placeholder="筛选状态"
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { label: '已启用', value: 'enabled' },
                { label: '已禁用', value: 'disabled' },
              ]}
            />
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建模型
          </Button>
        </div>

        <GlassTable
          columns={columns}
          dataSource={filteredModels}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </GlassCard>

      {/* 创建/编辑弹窗 */}
      <GlassModal
        title={editingModel ? '编辑模型' : '新建模型'}
        open={isModalVisible}
        onOk={handleSave}
        onCancel={() => setIsModalVisible(false)}
        width={700}
        okText="保存"
        cancelText="取消"
      >
        <style>{FORM_STYLES}</style>
        <div className="max-h-[70vh] overflow-y-auto">
          <Form
            form={form}
            layout="vertical"
            className="model-form mt-6"
          >
            <Form.Item
              label="提供商"
              name="provider_id"
              rules={[{ required: true, message: '请选择提供商' }]}
            >
              <GlassSelect
                placeholder="选择提供商"
                disabled={!!editingModel}
                options={providers.map(p => ({
                  label: p.display_name,
                  value: p.id,
                }))}
              />
            </Form.Item>

            <Form.Item
              label="模型标识"
              name="model_key"
              rules={[{ required: true, message: '请输入模型标识' }]}
            >
              <GlassInput
                placeholder="例如: gpt-4-turbo-preview"
                disabled={!!editingModel}
              />
            </Form.Item>

            <Form.Item
              label="显示名称"
              name="display_name"
              rules={[{ required: true, message: '请输入显示名称' }]}
            >
              <GlassInput placeholder="例如: GPT-4 Turbo" />
            </Form.Item>

            <Form.Item
              label="模型类型"
              name="model_type"
            >
              <GlassSelect
                placeholder="选择类型"
                options={[
                  { label: 'Chat', value: 'chat' },
                  { label: 'Completion', value: 'completion' },
                  { label: 'Embedding', value: 'embedding' },
                ]}
              />
            </Form.Item>

            <div className="grid grid-cols-3 gap-4">
              <Form.Item
                label="最大 Token 数"
                name="max_tokens"
              >
                <InputNumber
                  placeholder="128000"
                  className="w-full"
                  min={0}
                />
              </Form.Item>

              <Form.Item
                label="最大输入 Token"
                name="max_input_tokens"
              >
                <InputNumber
                  placeholder="120000"
                  className="w-full"
                  min={0}
                />
              </Form.Item>

              <Form.Item
                label="最大输出 Token"
                name="max_output_tokens"
              >
                <InputNumber
                  placeholder="4096"
                  className="w-full"
                  min={0}
                />
              </Form.Item>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Form.Item
                label="超时时间（秒）"
                name="timeout_seconds"
              >
                <InputNumber
                  placeholder="120"
                  className="w-full"
                  min={1}
                />
              </Form.Item>

              <Form.Item
                label="默认温度"
                name="temperature_default"
              >
                <InputNumber
                  placeholder="0.7"
                  className="w-full"
                  min={0}
                  max={2}
                  step={0.1}
                />
              </Form.Item>
            </div>

            <div className="flex gap-8">
              <Form.Item
                label="支持流式输出"
                name="supports_streaming"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                label="支持函数调用"
                name="supports_function_calling"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </div>

            <Form.Item
              label="描述"
              name="description"
            >
              <GlassTextArea
                rows={3}
                placeholder="模型描述（可选）"
              />
            </Form.Item>
          </Form>
        </div>
      </GlassModal>
    </div>
  );
};

export default ModelConfiguration;
