import React, { useEffect, useState } from 'react';
import { Button, Space, Form, Input, Select, Table, Tag, message, Modal, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';
import { adminApi } from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';

const { Option } = Select;

interface SplitRule {
  id: string;
  name: string;
  display_name: string;
  pattern: string;
  pattern_type: string;
  example?: string;
  is_default: boolean;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

const SplitRulesPage: React.FC = () => {
  const [rules, setRules] = useState<SplitRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<SplitRule | null>(null);
  const [form] = Form.useForm();

  const fetchRules = async () => {
    setLoading(true);
    try {
      const response = await adminApi.getSplitRules(false); // 获取所有规则，包括禁用的
      setRules(response.data);
    } catch (error) {
      console.error('Fetch rules error:', error);
      message.error('获取拆分规则列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleAdd = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({
      pattern_type: 'regex',
      is_active: true,
      is_default: false,
    });
    setIsModalVisible(true);
  };

  const handleEdit = (record: SplitRule) => {
    setEditingRule(record);
    form.setFieldsValue({
      name: record.name,
      display_name: record.display_name,
      pattern: record.pattern,
      pattern_type: record.pattern_type,
      example: record.example,
      is_default: record.is_default,
      is_active: record.is_active,
    });
    setIsModalVisible(true);
  };

  const handleDelete = (record: SplitRule) => {
    if (record.is_default) {
      message.error('不能删除默认规则');
      return;
    }

    Modal.confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除拆分规则「${record.display_name}」吗？`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await adminApi.deleteSplitRule(record.id);
          message.success('删除成功');
          fetchRules();
        } catch (error) {
          console.error('Delete error:', error);
          message.error('删除失败');
        }
      },
    });
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      if (editingRule) {
        await adminApi.updateSplitRule(editingRule.id, values);
        message.success('更新成功');
      } else {
        await adminApi.createSplitRule(values);
        message.success('创建成功');
      }
      setIsModalVisible(false);
      fetchRules();
    } catch (error) {
      console.error('Save error:', error);
      message.error('保存失败');
    }
  };

  const handleInitDefaults = async () => {
    Modal.confirm({
      title: '初始化预置规则',
      icon: <ExclamationCircleOutlined />,
      content: '这将创建或更新预置的拆分规则。是否继续？',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await adminApi.initDefaultSplitRules();
          message.success(response.data.message);
          fetchRules();
        } catch (error) {
          console.error('Init error:', error);
          message.error('初始化失败');
        }
      },
    });
  };

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: SplitRule) => (
        <Space>
          {text}
          {record.is_default && <Tag color="gold">默认</Tag>}
        </Space>
      ),
    },
    {
      title: '标识',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: '类型',
      dataIndex: 'pattern_type',
      key: 'pattern_type',
      render: (type: string) => (
        <Tag color={type === 'regex' ? 'blue' : 'green'}>
          {type === 'regex' ? '正则表达式' : '空行分隔'}
        </Tag>
      ),
    },
    {
      title: '匹配模式',
      dataIndex: 'pattern',
      key: 'pattern',
      render: (pattern: string) => (
        <Tooltip title={pattern}>
          <code className="text-xs truncate max-w-[200px] block">{pattern || '(空)'}</code>
        </Tooltip>
      ),
    },
    {
      title: '示例',
      dataIndex: 'example',
      key: 'example',
      render: (example: string) => (
        <Tooltip title={example}>
          <span className="text-gray-400 text-xs truncate max-w-[150px] block">{example || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: SplitRule) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
            disabled={record.is_default}
          />
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">拆分规则管理</h1>
            <p className="text-gray-400 mt-1">管理小说章节拆分规则，支持自定义正则表达式模式</p>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleInitDefaults}
            >
              初始化预置规则
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              添加规则
            </Button>
          </Space>
        </div>

        <GlassCard>
          <Table
            columns={columns}
            dataSource={rules}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </GlassCard>

        <Modal
          title={editingRule ? '编辑拆分规则' : '添加拆分规则'}
          open={isModalVisible}
          onOk={handleModalOk}
          onCancel={() => setIsModalVisible(false)}
          width={600}
        >
          <Form
            form={form}
            layout="vertical"
          >
            <Form.Item
              name="display_name"
              label="显示名称"
              rules={[{ required: true, message: '请输入显示名称' }]}
            >
              <Input placeholder="例如：中文标准 - 第N章" />
            </Form.Item>

            <Form.Item
              name="name"
              label="内部标识"
              rules={[
                { required: true, message: '请输入内部标识' },
                { pattern: /^[a-z0-9_]+$/, message: '只能使用小写字母、数字和下划线' }
              ]}
            >
              <Input placeholder="例如：standard_chinese" disabled={!!editingRule} />
            </Form.Item>

            <Form.Item
              name="pattern_type"
              label="拆分类型"
              rules={[{ required: true }]}
            >
              <Select>
                <Option value="regex">正则表达式</Option>
                <Option value="blank_line">空行分隔</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="pattern"
              label="匹配模式"
              rules={[{ required: true, message: '请输入匹配模式' }]}
              tooltip="正则表达式，用于匹配章节标题"
            >
              <Input placeholder="例如：第[一二三四五六七八九十百千\d]+章" />
            </Form.Item>

            <Form.Item
              name="example"
              label="示例文字"
              tooltip="用于展示给用户看这个规则的效果"
            >
              <Input.TextArea
                rows={2}
                placeholder="例如：第1章 初入江湖"
              />
            </Form.Item>

            <Form.Item
              name="is_default"
              valuePropName="checked"
            >
              <label>
                <input type="checkbox" className="mr-2" />
                设为默认规则
              </label>
            </Form.Item>

            <Form.Item
              name="is_active"
              valuePropName="checked"
            >
              <label>
                <input type="checkbox" className="mr-2" />
                启用此规则
              </label>
            </Form.Item>
          </Form>
        </Modal>
      </motion.div>
    </div>
  );
};

export default SplitRulesPage;
