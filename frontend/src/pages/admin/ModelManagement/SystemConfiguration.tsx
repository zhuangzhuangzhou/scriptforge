import React, { useState, useEffect, useRef } from 'react';
import { Button, Form, Input, InputNumber, message, Switch, Descriptions } from 'antd';
import { EditOutlined, SettingOutlined } from '@ant-design/icons';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassModal } from '../../../components/ui/GlassModal';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassInput } from '../../../components/ui/GlassInput';
import { systemConfigApi, SystemConfig, SystemConfigUpdate } from '../../../services/modelManagementApi';

const { TextArea } = Input;

const SystemConfiguration: React.FC = () => {
  // 状态管理
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SystemConfig | null>(null);
  const [form] = Form.useForm();
  const initialized = useRef(false);

  // 获取系统配置列表
  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const response = await systemConfigApi.getSystemConfigs();
      setConfigs(response.data);
    } catch (error) {
      console.error('获取系统配置失败:', error);
      message.error('获取系统配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialized.current) {
      fetchConfigs();
      initialized.current = true;
    }
  }, []);

  // 编辑配置
  const handleEdit = (record: SystemConfig) => {
    setEditingConfig(record);

    // 根据类型设置表单值
    let formValue = record.config_value.value;
    if (record.value_type === 'json') {
      formValue = JSON.stringify(record.config_value, null, 2);
    }

    form.setFieldsValue({
      config_value: formValue,
    });
    setIsModalVisible(true);
  };

  // 保存配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      if (!editingConfig) return;

      // 根据类型转换值
      let configValue: any;
      if (editingConfig.value_type === 'json') {
        try {
          configValue = JSON.parse(values.config_value);
        } catch (e) {
          message.error('JSON 格式错误');
          return;
        }
      } else if (editingConfig.value_type === 'integer') {
        configValue = { value: parseInt(values.config_value) };
      } else if (editingConfig.value_type === 'number') {
        configValue = { value: parseFloat(values.config_value) };
      } else if (editingConfig.value_type === 'boolean') {
        configValue = { value: values.config_value };
      } else {
        configValue = { value: values.config_value };
      }

      const updateData: SystemConfigUpdate = {
        config_value: configValue,
      };

      await systemConfigApi.updateSystemConfig(editingConfig.config_key, updateData);
      message.success('更新成功');
      setIsModalVisible(false);
      fetchConfigs();
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
      title: '配置项',
      dataIndex: 'config_key',
      key: 'config_key',
      width: 200,
      render: (text: string) => <code style={{ fontSize: 12 }}>{text}</code>,
    },
    {
      title: '当前值',
      key: 'current_value',
      render: (_: any, record: SystemConfig) => {
        if (record.value_type === 'json') {
          return (
            <pre style={{ fontSize: 12, margin: 0, maxWidth: 300, overflow: 'auto' }}>
              {JSON.stringify(record.config_value, null, 2)}
            </pre>
          );
        } else if (record.value_type === 'boolean') {
          return record.config_value.value ? '是' : '否';
        } else {
          return <span>{String(record.config_value.value)}</span>;
        }
      },
    },
    {
      title: '类型',
      dataIndex: 'value_type',
      key: 'value_type',
      width: 100,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: SystemConfig) => (
        <Button
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => handleEdit(record)}
          disabled={!record.is_editable}
        >
          编辑
        </Button>
      ),
    },
  ];

  // 渲染
  return (
    <div style={{ padding: '24px' }}>
      <GlassCard>
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
            <SettingOutlined style={{ marginRight: 8 }} />
            系统配置
          </h2>
        </div>

        <GlassTable
          columns={columns}
          dataSource={configs}
          loading={loading}
          rowKey="config_key"
          pagination={false}
        />
      </GlassCard>

      {/* 编辑弹窗 */}
      <GlassModal
        title="编辑系统配置"
        open={isModalVisible}
        onOk={handleSave}
        onCancel={() => setIsModalVisible(false)}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        {editingConfig && (
          <div style={{ marginTop: 24 }}>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 24 }}>
              <Descriptions.Item label="配置项">
                <code>{editingConfig.config_key}</code>
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                {editingConfig.value_type}
              </Descriptions.Item>
              <Descriptions.Item label="描述">
                {editingConfig.description}
              </Descriptions.Item>
            </Descriptions>

            <Form
              form={form}
              layout="vertical"
            >
              <Form.Item
                label="配置值"
                name="config_value"
                rules={[{ required: true, message: '请输入配置值' }]}
              >
                {editingConfig.value_type === 'string' && (
                  <GlassInput placeholder="输入配置值" />
                )}
                {(editingConfig.value_type === 'integer' || editingConfig.value_type === 'number') && (
                  <InputNumber
                    placeholder="输入数值"
                    style={{ width: '100%' }}
                    step={editingConfig.value_type === 'integer' ? 1 : 0.1}
                  />
                )}
                {editingConfig.value_type === 'boolean' && (
                  <Switch />
                )}
                {editingConfig.value_type === 'json' && (
                  <TextArea
                    rows={8}
                    placeholder="输入 JSON 格式的配置值"
                    style={{
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontFamily: 'monospace',
                    }}
                  />
                )}
              </Form.Item>
            </Form>
          </div>
        )}
      </GlassModal>
    </div>
  );
};

export default SystemConfiguration;
