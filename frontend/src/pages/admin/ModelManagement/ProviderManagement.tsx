import React, { useState, useEffect, useRef } from 'react';
import { Button, Form, Input, message, Space, Switch, Popconfirm } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassModal } from '../../../components/ui/GlassModal';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { providerApi, Provider, ProviderCreate, ProviderUpdate } from '../../../services/modelManagementApi';

const { TextArea } = Input;

const ProviderManagement: React.FC = () => {
  // 状态管理
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [form] = Form.useForm();
  const initialized = useRef(false);

  // 获取提供商列表
  const fetchProviders = async () => {
    setLoading(true);
    try {
      const response = await providerApi.getProviders();
      setProviders(response.data);
    } catch (error) {
      console.error('获取提供商列表失败:', error);
      message.error('获取提供商列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialized.current) {
      fetchProviders();
      initialized.current = true;
    }
  }, []);

  // 创建提供商
  const handleCreate = () => {
    setEditingProvider(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  // 编辑提供商
  const handleEdit = (record: Provider) => {
    setEditingProvider(record);
    form.setFieldsValue({
      provider_key: record.provider_key,
      display_name: record.display_name,
      provider_type: record.provider_type,
      api_endpoint: record.api_endpoint,
      icon_url: record.icon_url,
      description: record.description,
    });
    setIsModalVisible(true);
  };

  // 删除提供商
  const handleDelete = async (id: string) => {
    try {
      await providerApi.deleteProvider(id);
      message.success('删除成功');
      fetchProviders();
    } catch (error: any) {
      console.error('删除提供商失败:', error);
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  // 启用/禁用提供商
  const handleToggle = async (id: string) => {
    try {
      await providerApi.toggleProvider(id);
      message.success('状态更新成功');
      fetchProviders();
    } catch (error: any) {
      console.error('更新状态失败:', error);
      message.error(error.response?.data?.detail || '状态更新失败');
    }
  };

  // 保存提供商
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingProvider) {
        // 更新
        const updateData: ProviderUpdate = {
          display_name: values.display_name,
          api_endpoint: values.api_endpoint,
          icon_url: values.icon_url,
          description: values.description,
        };
        await providerApi.updateProvider(editingProvider.id, updateData);
        message.success('更新成功');
      } else {
        // 创建
        const createData: ProviderCreate = {
          provider_key: values.provider_key,
          display_name: values.display_name,
          provider_type: values.provider_type,
          api_endpoint: values.api_endpoint,
          icon_url: values.icon_url,
          description: values.description,
        };
        await providerApi.createProvider(createData);
        message.success('创建成功');
      }
      
      setIsModalVisible(false);
      fetchProviders();
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
      title: '提供商名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: Provider) => (
        <Space>
          {record.icon_url && (
            <img src={record.icon_url} alt={text} style={{ width: 24, height: 24, borderRadius: 4 }} />
          )}
          <span>{text}</span>
          {record.is_system_default && <span style={{ color: '#1890ff', fontSize: 12 }}>(默认)</span>}
        </Space>
      ),
    },
    {
      title: '标识',
      dataIndex: 'provider_key',
      key: 'provider_key',
    },
    {
      title: '类型',
      dataIndex: 'provider_type',
      key: 'provider_type',
    },
    {
      title: 'API 端点',
      dataIndex: 'api_endpoint',
      key: 'api_endpoint',
      ellipsis: true,
    },
    {
      title: '模型数',
      dataIndex: 'models_count',
      key: 'models_count',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 100,
      render: (enabled: boolean, record: Provider) => (
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
      width: 150,
      render: (_: any, record: Provider) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除？"
            description={`删除后，该提供商下的 ${record.models_count} 个模型也将被删除`}
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="link"
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

  // 渲染
  return (
    <div style={{ padding: '24px' }}>
      <GlassCard>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>提供商管理</h2>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建提供商
          </Button>
        </div>

        <GlassTable
          columns={columns}
          dataSource={providers}
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
        title={editingProvider ? '编辑提供商' : '新建提供商'}
        open={isModalVisible}
        onOk={handleSave}
        onCancel={() => setIsModalVisible(false)}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 24 }}
        >
          <Form.Item
            label="提供商标识"
            name="provider_key"
            rules={[
              { required: true, message: '请输入提供商标识' },
              { pattern: /^[a-z0-9_-]+$/, message: '只能包含小写字母、数字、下划线和连字符' },
            ]}
          >
            <GlassInput
              placeholder="例如: openai, anthropic"
              disabled={!!editingProvider}
            />
          </Form.Item>

          <Form.Item
            label="显示名称"
            name="display_name"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <GlassInput placeholder="例如: OpenAI" />
          </Form.Item>

          <Form.Item
            label="提供商类型"
            name="provider_type"
            rules={[{ required: true, message: '请选择提供商类型' }]}
          >
            <GlassSelect
              placeholder="选择类型"
              disabled={!!editingProvider}
              options={[
                { label: 'OpenAI Compatible', value: 'openai_compatible' },
                { label: 'Anthropic', value: 'anthropic' },
                { label: 'Custom', value: 'custom' },
              ]}
            />
          </Form.Item>

          <Form.Item
            label="API 端点"
            name="api_endpoint"
          >
            <GlassInput placeholder="例如: https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            label="图标 URL"
            name="icon_url"
          >
            <GlassInput placeholder="图标 URL（可选）" />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
          >
            <TextArea
              rows={3}
              placeholder="提供商描述（可选）"
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                color: '#fff',
              }}
            />
          </Form.Item>
        </Form>
      </GlassModal>
    </div>
  );
};

export default ProviderManagement;
