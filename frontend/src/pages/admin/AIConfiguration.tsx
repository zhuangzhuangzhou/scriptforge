import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, message, Space, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, ImportOutlined, CodeOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';
import { configService, AIConfiguration } from '../../services/configService';

const { TextArea } = Input;

const DEFAULT_ADAPT_METHOD = {
  key: "adapt_method",
  value: {
    name: "网文改编漫剧创作方法论（通用版）",
    core_principles: [
      "情绪钩子密度 > 故事完整性",
      "视觉冲击力 > 文学性描写",
      "快节奏刺激 > 慢节奏沉浸",
      "算法友好性 > 戏剧逻辑性"
    ],
    format: "起承转钩四段式",
    specs: {
      duration: "1-2分钟",
      word_count: "500-800字"
    }
  },
  description: "来自 adapt-method.md 的默认网文改编漫剧创作方法论"
};

const AIConfigurationPage: React.FC = () => {
  const [configs, setConfigs] = useState<AIConfiguration[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<AIConfiguration | null>(null);
  const [form] = Form.useForm();

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const data = await configService.getConfigurations();
      setConfigs(data);
    } catch (error) {
      console.error('Fetch configs error:', error);
      message.error('获取配置列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleEdit = (record: AIConfiguration) => {
    setEditingConfig(record);
    form.setFieldsValue({
      key: record.key,
      value: typeof record.value === 'string' ? record.value : JSON.stringify(record.value, null, 2),
      description: record.description
    });
    setIsModalVisible(true);
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

  const handleLoadDefault = () => {
    form.setFieldsValue({
      key: DEFAULT_ADAPT_METHOD.key,
      value: JSON.stringify(DEFAULT_ADAPT_METHOD.value, null, 2),
      description: DEFAULT_ADAPT_METHOD.description
    });
    message.info('已加载默认方法论模板');
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      let parsedValue = values.value;

      // 尝试解析 JSON
      try {
        if (values.value.trim().startsWith('{') || values.value.trim().startsWith('[')) {
          parsedValue = JSON.parse(values.value);
        }
      } catch (e) {
        // 如果不是有效的 JSON，则保持原样字符串
      }

      await configService.upsertConfiguration({
        key: values.key,
        value: parsedValue,
        description: values.description
      });

      message.success(editingConfig ? '配置已更新' : '配置已创建');
      setIsModalVisible(false);
      fetchConfigs();
    } catch (error) {
      console.error(error);
      message.error('保存失败，请检查输入格式');
    }
  };

  const columns = [
    {
      title: '配置键 (Key)',
      dataIndex: 'key',
      key: 'key',
      width: '20%',
      render: (text: string) => <span className="font-mono text-cyan-400">{text}</span>
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: '25%',
      render: (text: string) => <span className="text-slate-300">{text}</span>
    },
    {
      title: '内容 (Value)',
      dataIndex: 'value',
      key: 'value',
      render: (val: unknown) => (
        <pre className="max-h-24 overflow-auto bg-slate-950/50 p-2 rounded text-xs font-mono text-slate-400 border border-slate-800 scrollbar-thin scrollbar-thumb-slate-700">
          {typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val)}
        </pre>
      ),
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

  return (
    <div className="p-6 min-h-screen bg-slate-950">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-cyan-500 bg-clip-text text-transparent m-0">
              AI 系统配置
            </h1>
            <p className="text-slate-400 mt-1">管理 AI 模型的全局参数、提示词模板与策略配置</p>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
            className="bg-cyan-600 hover:bg-cyan-500 border-none h-10 px-6 shadow-lg shadow-cyan-900/20"
          >
            新建配置
          </Button>
        </div>

        <div className="backdrop-blur-xl bg-slate-900/60 border border-slate-800/60 rounded-2xl overflow-hidden shadow-2xl">
          <Table
            columns={columns}
            dataSource={configs}
            rowKey="key"
            loading={loading}
            pagination={{ pageSize: 10, className: "p-4" }}
            className="ant-table-dark-glass"
          />
        </div>

        <Modal
          title={<span className="text-slate-100 flex items-center gap-2"><CodeOutlined /> {editingConfig ? "编辑配置" : "新建配置"}</span>}
          open={isModalVisible}
          onOk={handleModalOk}
          onCancel={() => setIsModalVisible(false)}
          width={800}
          okText="保存配置"
          cancelText="取消"
          className="dark-glass-modal"
          okButtonProps={{ className: "bg-cyan-600 hover:bg-cyan-500 border-none" }}
          cancelButtonProps={{ className: "border-slate-600 text-slate-300 hover:text-white hover:border-slate-500" }}
        >
          <Form form={form} layout="vertical" className="mt-6">
            <div className="flex justify-end mb-2">
              <Button
                size="small"
                icon={<ImportOutlined />}
                onClick={handleLoadDefault}
                className="text-cyan-400 border-cyan-900/50 bg-cyan-950/20 hover:bg-cyan-900/40 hover:border-cyan-700"
              >
                加载默认方法论 (Adapt Method)
              </Button>
            </div>

            <Form.Item
              name="key"
              label={<span className="text-slate-300">Key (配置键)</span>}
              rules={[{ required: true, message: '请输入配置键' }]}
            >
              <Input
                disabled={!!editingConfig}
                placeholder="例如: adapt_method"
                className="glass-input font-mono"
              />
            </Form.Item>

            <Form.Item
              name="description"
              label={<span className="text-slate-300">描述</span>}
            >
              <Input
                placeholder="配置的用途说明"
                className="glass-input"
              />
            </Form.Item>

            <Form.Item
              name="value"
              label={<span className="text-slate-300">配置值 (支持 JSON)</span>}
              rules={[{ required: true, message: '请输入配置内容' }]}
            >
              <TextArea
                rows={12}
                placeholder="请输入字符串或 JSON"
                className="glass-input font-mono text-xs leading-relaxed"
                spellCheck={false}
              />
            </Form.Item>
          </Form>
        </Modal>
      </motion.div>
    </div>
  );
};

export default AIConfigurationPage;
