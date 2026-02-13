import React, { useState, useEffect, useRef } from 'react';
import { Button, Form, Input, InputNumber, message, Space, Switch, Popconfirm, DatePicker, Progress, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, CheckCircleOutlined, CloseCircleOutlined, CopyOutlined, SafetyOutlined, ApiOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassModal } from '../../../components/ui/GlassModal';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { credentialApi, providerApi, Credential, CredentialCreate, CredentialUpdate, Provider } from '../../../services/modelManagementApi';
import { extractArrayData } from '../../../utils/apiHelpers';
import dayjs from 'dayjs';

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
  .credential-form .ant-form-item-label > label {
    color: #cbd5e1 !important;
  }
  .credential-form .ant-form-item-extra {
    color: #64748b !important;
  }
`;

const CredentialManagement: React.FC = () => {
  // 状态管理
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingCredential, setEditingCredential] = useState<Credential | null>(null);
  const [selectedProviderId, setSelectedProviderId] = useState<string | undefined>(undefined);
  const [testingId, setTestingId] = useState<string | null>(null);
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

  // 获取凭证列表
  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const response = await credentialApi.getCredentials(selectedProviderId);
      setCredentials(extractArrayData<Credential>(response.data));
    } catch (error) {
      console.error('获取凭证列表失败:', error);
      message.error('获取凭证列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialized.current) {
      fetchProviders();
      fetchCredentials();
      initialized.current = true;
    }
  }, []);

  useEffect(() => {
    if (initialized.current) {
      fetchCredentials();
    }
  }, [selectedProviderId]);

  // 创建凭证
  const handleCreate = () => {
    setEditingCredential(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  // 编辑凭证
  const handleEdit = (record: Credential) => {
    setEditingCredential(record);
    form.setFieldsValue({
      provider_id: record.provider.id,
      credential_name: record.credential_name,
      quota_limit: record.quota_limit,
      expires_at: record.expires_at ? dayjs(record.expires_at) : null,
    });
    setIsModalVisible(true);
  };

  // 删除凭证
  const handleDelete = async (id: string) => {
    try {
      await credentialApi.deleteCredential(id);
      message.success('删除成功');
      fetchCredentials();
    } catch (error: any) {
      console.error('删除凭证失败:', error);
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  // 启用/禁用凭证
  const handleToggle = async (id: string) => {
    try {
      await credentialApi.toggleCredential(id);
      message.success('状态更新成功');
      fetchCredentials();
    } catch (error: any) {
      console.error('更新状态失败:', error);
      message.error(error.response?.data?.detail || '状态更新失败');
    }
  };

  // 测试凭证
  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const response = await credentialApi.testCredential(id);
      if (response.data.success) {
        message.success(response.data.message || '凭证测试成功');
      } else {
        message.warning(response.data.message || '凭证测试失败');
      }
    } catch (error: any) {
      console.error('测试凭证失败:', error);
      message.error(error.response?.data?.detail || '测试失败');
    } finally {
      setTestingId(null);
    }
  };

  // 复制 API Key
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  // 保存凭证
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingCredential) {
        // 更新
        const updateData: CredentialUpdate = {
          credential_name: values.credential_name,
          api_key: values.api_key,
          api_secret: values.api_secret,
          quota_limit: values.quota_limit,
          expires_at: values.expires_at ? values.expires_at.toISOString() : undefined,
        };
        await credentialApi.updateCredential(editingCredential.id, updateData);
        message.success('更新成功');
      } else {
        // 创建
        const createData: CredentialCreate = {
          provider_id: values.provider_id,
          credential_name: values.credential_name,
          api_key: values.api_key,
          api_secret: values.api_secret,
          quota_limit: values.quota_limit,
          expires_at: values.expires_at ? values.expires_at.toISOString() : undefined,
        };
        await credentialApi.createCredential(createData);
        message.success('创建成功');
      }
      
      setIsModalVisible(false);
      fetchCredentials();
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
      title: '提供商',
      key: 'provider',
      width: 120,
      render: (_: any, record: Credential) => record.provider.display_name,
    },
    {
      title: '凭证名称',
      dataIndex: 'credential_name',
      key: 'credential_name',
      render: (text: string, record: Credential) => (
        <Space>
          <span>{text}</span>
          {record.is_system_default && <SafetyOutlined style={{ color: '#1890ff' }} />}
        </Space>
      ),
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
      render: (text: string) => (
        <Space>
          <code style={{ fontSize: 12, color: '#888' }}>{text}</code>
          <Tooltip title="复制">
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleCopy(text)}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '配额使用',
      key: 'quota',
      width: 200,
      render: (_: any, record: Credential) => {
        if (!record.quota_limit) return '-';
        const percent = (record.quota_used / record.quota_limit) * 100;
        return (
          <div>
            <Progress
              percent={Math.round(percent)}
              size="small"
              status={percent > 90 ? 'exception' : percent > 70 ? 'normal' : 'success'}
            />
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              {record.quota_used.toLocaleString()} / {record.quota_limit.toLocaleString()}
            </div>
          </div>
        );
      },
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 120,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '最后使用',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 120,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean, record: Credential) => (
        <Switch
          checked={active}
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
      render: (_: any, record: Credential) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<ApiOutlined />}
            loading={testingId === record.id}
            onClick={() => handleTest(record.id)}
          >
            测试
          </Button>
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

  // 渲染
  return (
    <div className="p-6">
      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <h2 className="m-0 text-xl font-semibold text-slate-100">凭证管理</h2>
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
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建凭证
          </Button>
        </div>

        <div className="mb-4">
          <GlassAlert
            type="info"
            title="安全提示"
            description="API Key 将使用 AES-256-GCM 加密存储，传输过程使用 HTTPS 加密。请妥善保管您的 API Key。"
          />
        </div>

        <GlassTable
          columns={columns}
          dataSource={credentials}
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
        title={editingCredential ? '编辑凭证' : '新建凭证'}
        open={isModalVisible}
        onOk={handleSave}
        onCancel={() => setIsModalVisible(false)}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <style>{FORM_STYLES}</style>
        <Form
          form={form}
          layout="vertical"
          className="credential-form mt-6"
        >
          <Form.Item
            label="提供商"
            name="provider_id"
            rules={[{ required: true, message: '请选择提供商' }]}
          >
            <GlassSelect
              placeholder="选择提供商"
              disabled={!!editingCredential}
              options={providers.map(p => ({
                label: p.display_name,
                value: p.id,
              }))}
            />
          </Form.Item>

          <Form.Item
            label="凭证名称"
            name="credential_name"
            rules={[{ required: true, message: '请输入凭证名称' }]}
          >
            <GlassInput placeholder="例如: OpenAI 主账号" />
          </Form.Item>

          <Form.Item
            label="API Key"
            name="api_key"
            rules={[
              { required: !editingCredential, message: '请输入 API Key' },
            ]}
            extra={editingCredential ? '留空则不修改' : ''}
          >
            <Input.Password
              placeholder="输入 API Key"
              className="glass-password-input"
              style={{
                background: 'rgba(2, 6, 23, 0.5)',
                border: '1px solid rgba(51, 65, 85, 0.6)',
                borderRadius: '6px',
                color: '#e2e8f0',
              }}
            />
          </Form.Item>

          <Form.Item
            label="API Secret（可选）"
            name="api_secret"
            extra={editingCredential ? '留空则不修改' : ''}
          >
            <Input.Password
              placeholder="输入 API Secret（如需要）"
              className="glass-password-input"
              style={{
                background: 'rgba(2, 6, 23, 0.5)',
                border: '1px solid rgba(51, 65, 85, 0.6)',
                borderRadius: '6px',
                color: '#e2e8f0',
              }}
            />
          </Form.Item>

          <Form.Item
            label="配额限制"
            name="quota_limit"
          >
            <InputNumber
              placeholder="不限制"
              className="w-full"
              min={0}
            />
          </Form.Item>

          <Form.Item
            label="过期时间"
            name="expires_at"
          >
            <DatePicker
              className="w-full"
              placeholder="选择过期时间（可选）"
            />
          </Form.Item>
        </Form>
      </GlassModal>
    </div>
  );
};

export default CredentialManagement;
