import React, { useState, useEffect, useRef } from 'react';
import { Button, Form, message, Space, Tooltip, Tag, Select } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, CopyOutlined, CodeOutlined, RobotOutlined, GlobalOutlined, UserOutlined } from '@ant-design/icons';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { configService, AIConfiguration } from '../../services/configService';
import { GlassTable } from '../ui/GlassTable';
import { GlassModal } from '../ui/GlassModal';
import { GlassTabs } from '../ui/GlassTabs';
import { GlassInput, GlassTextArea } from '../ui/GlassInput';
import { GlassSelect } from '../ui/GlassSelect';

// Remove Input Destructuring since we use GlassInput
// const { TextArea } = Input;
const { Option } = Select;

interface AIConfigurationModalProps {
  onClose: () => void;
}

const AIConfigurationModal: React.FC<AIConfigurationModalProps> = ({ onClose }) => {
  const [allConfigs, setAllConfigs] = useState<AIConfiguration[]>([]);
  const [loading, setLoading] = useState(false);
  // Inner modal for Create/Edit
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<AIConfiguration | null>(null);
  const [activeTab, setActiveTab] = useState<string>('user');
  const [form] = Form.useForm();
  const initialized = useRef(false);

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      // merge=false 获取所有原始配置（包含系统和用户）
      const data = await configService.getConfigurations(false);
      setAllConfigs(data);
    } catch (error) {
      console.error('Fetch configs error:', error);
      message.error('获取配置列表失败');
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

  // 分离数据
  const userConfigs = allConfigs.filter(c => c.user_id !== null && c.user_id !== undefined);
  const systemConfigs = allConfigs.filter(c => c.user_id === null || c.user_id === undefined);

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, category: 'adapt_method' });
    setIsFormVisible(true);
  };

  const handleEdit = (record: AIConfiguration) => {
    setEditingConfig(record);
    form.setFieldsValue({
      key: record.key,
      value: typeof record.value === 'string' ? record.value : JSON.stringify(record.value, null, 2),
      description: record.description,
      category: record.category,
      is_active: record.is_active
    });
    setIsFormVisible(true);
  };

  const handleClone = (record: AIConfiguration) => {
    setEditingConfig(null); // 视为新建
    form.setFieldsValue({
      key: record.key, // 保持相同的 Key 以便覆盖系统配置
      value: typeof record.value === 'string' ? record.value : JSON.stringify(record.value, null, 2),
      description: `(自定义) ${record.description || ''}`,
      category: record.category,
      is_active: true
    });
    setIsFormVisible(true);
    message.info('已复制系统配置，保存后将作为您的自定义配置生效');
  };

  const handleDelete = async (key: string) => {
    try {
      await configService.deleteConfiguration(key);
      message.success('配置已删除');
      fetchConfigs();
    } catch (error) {
      message.error('删除配置失败');
    }
  };

  const handleFormSubmit = async () => {
    try {
      const values = await form.validateFields();
      let parsedValue = values.value;

      try {
        if (values.value.trim().startsWith('{') || values.value.trim().startsWith('[')) {
          parsedValue = JSON.parse(values.value);
        }
      } catch (e) {
        // keep string
      }

      await configService.upsertConfiguration({
        key: values.key,
        value: parsedValue,
        description: values.description,
        category: values.category,
        is_active: values.is_active
      });

      message.success(editingConfig ? '配置已更新' : '配置已创建');
      setIsFormVisible(false);
      fetchConfigs();
    } catch (error) {
      console.error(error);
      message.error('保存失败，请检查输入格式');
    }
  };

  const getCategoryColor = (category?: string) => {
    switch(category) {
      case 'adapt_method': return 'blue';
      case 'prompt_template': return 'purple';
      case 'quality_rule': return 'cyan';
      default: return 'default';
    }
  };

  const commonColumns = [
    {
      title: '配置键 (Key)',
      dataIndex: 'key',
      key: 'key',
      width: '20%',
      render: (text: string) => <span className="font-mono text-cyan-400 font-bold">{text}</span>
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: '10%',
      render: (text: string) => (
        <Tag color={getCategoryColor(text)} bordered={false} className="bg-opacity-20">
          {text || 'uncategorized'}
        </Tag>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: '25%',
      render: (text: string) => <span className="text-slate-300">{text}</span>
    },
    {
      title: '内容预览',
      dataIndex: 'value',
      key: 'value',
      render: (val: unknown) => {
        const str = typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val);
        return (
          <div className="max-h-16 overflow-hidden text-xs font-mono text-slate-500 opacity-70">
            {str.slice(0, 100)}{str.length > 100 ? '...' : ''}
          </div>
        );
      },
    },
  ];

  const userColumns = [
    ...commonColumns,
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: '8%',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>
          {active ? '生效中' : '已禁用'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: '15%',
      render: (_: unknown, record: AIConfiguration) => (
        <Space size="middle">
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              className="text-cyan-400 hover:text-cyan-300 hover:bg-cyan-950/30"
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="text"
              icon={<DeleteOutlined />}
              danger
              onClick={() => handleDelete(record.key)}
              className="hover:bg-red-950/30"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const systemColumns = [
    ...commonColumns,
    {
      title: '操作',
      key: 'action',
      width: '15%',
      render: (_: unknown, record: AIConfiguration) => (
        <Tooltip title="创建自定义副本 (Override)">
          <Button
            type="primary"
            ghost
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleClone(record)}
            className="border-cyan-700 text-cyan-400 hover:text-cyan-300 hover:border-cyan-500"
          >
            自定义此配置
          </Button>
        </Tooltip>
      ),
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative bg-slate-900/90 border border-slate-700/50 w-full max-w-6xl h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/60 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-400">
              <RobotOutlined className="text-xl" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white m-0">AI 系统配置中心</h2>
              <p className="text-xs text-slate-400 m-0 mt-0.5">管理改编方法论、提示词模板与核心规则</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-950/30">
          <div className="flex justify-between items-center mb-6">
            <GlassTabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                {
                  key: 'user',
                  label: (
                    <span className="flex items-center gap-2 px-2">
                      <UserOutlined /> 我的配置
                      <Tag className="ml-2 bg-cyan-900/50 text-cyan-300 border-none">{userConfigs.length}</Tag>
                    </span>
                  ),
                },
                {
                  key: 'system',
                  label: (
                    <span className="flex items-center gap-2 px-2">
                      <GlobalOutlined /> 系统默认配置
                      <Tag className="ml-2 bg-slate-800 text-slate-400 border-none">{systemConfigs.length}</Tag>
                    </span>
                  ),
                }
              ]}
            />

            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              className="bg-blue-600 hover:bg-blue-500 border-none h-9 px-4 shadow-lg shadow-blue-900/20"
            >
              新建配置
            </Button>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/60 rounded-xl overflow-hidden">
            <GlassTable
              columns={activeTab === 'user' ? userColumns : systemColumns}
              dataSource={activeTab === 'user' ? userConfigs : systemConfigs}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 8, className: "p-4" }}
            />
          </div>
        </div>

        {/* Inner Modal for Create/Edit - Using GlassModal component but controlled here */}
        {isFormVisible && (
          <GlassModal
            title={<span className="text-slate-100 flex items-center gap-2"><CodeOutlined /> {editingConfig ? "编辑配置" : "新建配置"}</span>}
            open={isFormVisible}
            onOk={handleFormSubmit}
            onCancel={() => setIsFormVisible(false)}
            width={800}
            okText="保存配置"
            cancelText="取消"
            okButtonProps={{ className: "bg-blue-600 hover:bg-blue-500 border-none" }}
            cancelButtonProps={{ className: "border-slate-600 text-slate-300 hover:text-white hover:border-slate-500" }}
            zIndex={1060} // Higher than the main modal (usually 1050 for standard modals, or custom)
          >
            <Form form={form} layout="vertical" className="mt-6">
              <Form.Item
                name="key"
                label={<span className="text-slate-300">Key (配置键 - 相同Key将覆盖系统默认值)</span>}
                rules={[{ required: true, message: '请输入配置键' }]}
              >
                <GlassInput
                  disabled={!!editingConfig} // 编辑时不可改 Key
                  placeholder="例如: adapt_method_default"
                  className="font-mono"
                />
              </Form.Item>

              <div className="grid grid-cols-2 gap-4">
                <Form.Item
                  name="category"
                  label={<span className="text-slate-300">分类</span>}
                  rules={[{ required: true }]}
                >
                  <GlassSelect>
                    <Option value="adapt_method">适配方法 (Adapt Method)</Option>
                    <Option value="prompt_template">提示词模板 (Prompt)</Option>
                    <Option value="quality_rule">质量标准 (Quality Rule)</Option>
                    <Option value="other">其他</Option>
                  </GlassSelect>
                </Form.Item>

                <Form.Item
                  name="is_active"
                  label={<span className="text-slate-300">状态</span>}
                  valuePropName="checked"
                >
                   <GlassSelect>
                      <Option value={true}>启用</Option>
                      <Option value={false}>禁用</Option>
                   </GlassSelect>
                </Form.Item>
              </div>

              <Form.Item
                name="description"
                label={<span className="text-slate-300">描述</span>}
              >
                <GlassInput
                  placeholder="配置的用途说明"
                />
              </Form.Item>

              <Form.Item
                name="value"
                label={<span className="text-slate-300">配置值 (JSON 或 文本)</span>}
                rules={[{ required: true, message: '请输入配置内容' }]}
              >
                <GlassTextArea
                  rows={15}
                  placeholder="在此输入具体配置内容..."
                  className="font-mono text-xs leading-relaxed"
                  spellCheck={false}
                />
              </Form.Item>
            </Form>
          </GlassModal>
        )}
      </motion.div>
    </div>
  );
};

export default AIConfigurationModal;
