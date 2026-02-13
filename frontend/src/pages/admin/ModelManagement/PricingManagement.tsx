import React, { useState, useEffect, useRef } from 'react';
import { Button, Form, InputNumber, message, Space, Popconfirm, DatePicker, Tag } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassModal } from '../../../components/ui/GlassModal';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { pricingApi, modelApi, Pricing, PricingCreate, PricingUpdate, AIModel } from '../../../services/modelManagementApi';
import dayjs from 'dayjs';

// 表单样式
const FORM_STYLES = `
  .pricing-form .ant-form-item-label > label {
    color: #cbd5e1 !important;
  }
`;

const PricingManagement: React.FC = () => {
  // 状态管理
  const [pricingRules, setPricingRules] = useState<Pricing[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingPricing, setEditingPricing] = useState<Pricing | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string | undefined>(undefined);
  const [form] = Form.useForm();
  const initialized = useRef(false);

  // 获取模型列表
  const fetchModels = async () => {
    try {
      const response = await modelApi.getModels();
      setModels(response.data);
    } catch (error) {
      console.error('获取模型列表失败:', error);
    }
  };

  // 获取计费规则列表
  const fetchPricingRules = async () => {
    setLoading(true);
    try {
      const response = await pricingApi.getPricingRules(selectedModelId);
      setPricingRules(response.data);
    } catch (error) {
      console.error('获取计费规则列表失败:', error);
      message.error('获取计费规则列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialized.current) {
      fetchModels();
      fetchPricingRules();
      initialized.current = true;
    }
  }, []);

  useEffect(() => {
    if (initialized.current) {
      fetchPricingRules();
    }
  }, [selectedModelId]);

  // 创建计费规则
  const handleCreate = () => {
    setEditingPricing(null);
    form.resetFields();
    form.setFieldsValue({
      min_credits_per_request: 0,
    });
    setIsModalVisible(true);
  };

  // 编辑计费规则
  const handleEdit = (record: Pricing) => {
    setEditingPricing(record);
    form.setFieldsValue({
      model_id: record.model.id,
      input_credits_per_1k_tokens: record.input_credits_per_1k_tokens,
      output_credits_per_1k_tokens: record.output_credits_per_1k_tokens,
      min_credits_per_request: record.min_credits_per_request,
      effective_from: record.effective_from ? dayjs(record.effective_from) : null,
      effective_until: record.effective_until ? dayjs(record.effective_until) : null,
    });
    setIsModalVisible(true);
  };

  // 删除计费规则
  const handleDelete = async (id: string) => {
    try {
      await pricingApi.deletePricingRule(id);
      message.success('删除成功');
      fetchPricingRules();
    } catch (error: any) {
      console.error('删除计费规则失败:', error);
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  // 保存计费规则
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingPricing) {
        // 更新
        const updateData: PricingUpdate = {
          input_credits_per_1k_tokens: values.input_credits_per_1k_tokens,
          output_credits_per_1k_tokens: values.output_credits_per_1k_tokens,
          min_credits_per_request: values.min_credits_per_request,
          effective_from: values.effective_from ? values.effective_from.toISOString() : undefined,
          effective_until: values.effective_until ? values.effective_until.toISOString() : undefined,
        };
        await pricingApi.updatePricingRule(editingPricing.id, updateData);
        message.success('更新成功');
      } else {
        // 创建
        const createData: PricingCreate = {
          model_id: values.model_id,
          input_credits_per_1k_tokens: values.input_credits_per_1k_tokens,
          output_credits_per_1k_tokens: values.output_credits_per_1k_tokens,
          min_credits_per_request: values.min_credits_per_request,
          effective_from: values.effective_from ? values.effective_from.toISOString() : undefined,
          effective_until: values.effective_until ? values.effective_until.toISOString() : undefined,
        };
        await pricingApi.createPricingRule(createData);
        message.success('创建成功');
      }
      
      setIsModalVisible(false);
      fetchPricingRules();
    } catch (error: any) {
      console.error('保存失败:', error);
      if (error.errorFields) {
        message.error('请检查表单填写');
      } else {
        message.error(error.response?.data?.detail || '保存失败');
      }
    }
  };

  // 判断规则状态
  const getRuleStatus = (record: Pricing) => {
    const now = dayjs();
    const from = record.effective_from ? dayjs(record.effective_from) : null;
    const until = record.effective_until ? dayjs(record.effective_until) : null;

    if (!record.is_active) return { text: '已禁用', color: 'default' };
    if (from && now.isBefore(from)) return { text: '未来生效', color: 'blue' };
    if (until && now.isAfter(until)) return { text: '已过期', color: 'red' };
    return { text: '当前生效', color: 'green' };
  };

  // 表格列定义
  const columns = [
    {
      title: '模型',
      key: 'model',
      render: (_: any, record: Pricing) => (
        <div>
          <div>{record.model.display_name}</div>
          <div style={{ fontSize: 12, color: '#888' }}>{record.model.model_key}</div>
        </div>
      ),
    },
    {
      title: '输入价格',
      dataIndex: 'input_credits_per_1k_tokens',
      key: 'input_credits_per_1k_tokens',
      width: 120,
      render: (value: number) => `${value} 积分/1K`,
    },
    {
      title: '输出价格',
      dataIndex: 'output_credits_per_1k_tokens',
      key: 'output_credits_per_1k_tokens',
      width: 120,
      render: (value: number) => `${value} 积分/1K`,
    },
    {
      title: '最低消费',
      dataIndex: 'min_credits_per_request',
      key: 'min_credits_per_request',
      width: 100,
      render: (value: number) => `${value} 积分`,
    },
    {
      title: '生效时间',
      key: 'effective_time',
      width: 200,
      render: (_: any, record: Pricing) => (
        <div style={{ fontSize: 12 }}>
          <div>
            <ClockCircleOutlined /> {record.effective_from ? dayjs(record.effective_from).format('YYYY-MM-DD') : '立即'}
          </div>
          {record.effective_until && (
            <div style={{ color: '#888' }}>
              至 {dayjs(record.effective_until).format('YYYY-MM-DD')}
            </div>
          )}
        </div>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: any, record: Pricing) => {
        const status = getRuleStatus(record);
        return <Tag color={status.color}>{status.text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: Pricing) => (
        <Space size="small">
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
            <h2 className="m-0 text-xl font-semibold text-slate-100">计费规则</h2>
            <GlassSelect
              style={{ width: 200 }}
              placeholder="筛选模型"
              allowClear
              value={selectedModelId}
              onChange={setSelectedModelId}
              options={models.map(m => ({
                label: m.display_name,
                value: m.id,
              }))}
            />
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建规则
          </Button>
        </div>

        <GlassTable
          columns={columns}
          dataSource={pricingRules}
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
        title={editingPricing ? '编辑计费规则' : '新建计费规则'}
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
          className="pricing-form mt-6"
        >
          <Form.Item
            label="模型"
            name="model_id"
            rules={[{ required: true, message: '请选择模型' }]}
          >
            <GlassSelect
              placeholder="选择模型"
              disabled={!!editingPricing}
              options={models.map(m => ({
                label: `${m.display_name} (${m.model_key})`,
                value: m.id,
              }))}
            />
          </Form.Item>

          <Form.Item
            label="输入 Token 价格（每 1000 tokens）"
            name="input_credits_per_1k_tokens"
            rules={[{ required: true, message: '请输入输入 Token 价格' }]}
          >
            <InputNumber
              placeholder="1.5"
              className="w-full"
              min={0}
              step={0.1}
              addonAfter="积分"
            />
          </Form.Item>

          <Form.Item
            label="输出 Token 价格（每 1000 tokens）"
            name="output_credits_per_1k_tokens"
            rules={[{ required: true, message: '请输入输出 Token 价格' }]}
          >
            <InputNumber
              placeholder="3.0"
              className="w-full"
              min={0}
              step={0.1}
              addonAfter="积分"
            />
          </Form.Item>

          <Form.Item
            label="每次请求最低消费"
            name="min_credits_per_request"
          >
            <InputNumber
              placeholder="0"
              className="w-full"
              min={0}
              step={0.1}
              addonAfter="积分"
            />
          </Form.Item>

          <Form.Item
            label="生效时间"
            name="effective_from"
          >
            <DatePicker
              className="w-full"
              placeholder="立即生效"
              showTime
            />
          </Form.Item>

          <Form.Item
            label="失效时间"
            name="effective_until"
          >
            <DatePicker
              className="w-full"
              placeholder="永久有效"
              showTime
            />
          </Form.Item>
        </Form>
      </GlassModal>
    </div>
  );
};

export default PricingManagement;
