import React, { useState, useEffect } from 'react';
import { Button, Tag, Space, message, Modal, Switch, Empty } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassTabs } from '../../../components/ui/GlassTabs';

interface Resource {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  visibility: string;
  owner_id: string;
  is_builtin: boolean;
  is_active: boolean;
  created_at: string;
}

const categoryMap: Record<string, string> = {
  methodology: '方法论',
  output_style: '输出风格',
  qa_rules: '质检标准',
  template: '模板案例',
  breakdown_prompt: '拆解提示词',
};

const categoryColorMap: Record<string, string> = {
  methodology: 'blue',
  output_style: 'purple',
  qa_rules: 'orange',
  template: 'cyan',
  breakdown_prompt: 'indigo',
};

const TemplatesPage: React.FC = () => {
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const navigate = useNavigate();

  // 加载资源列表
  const loadResources = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (searchText) params.search = searchText;
      if (activeTab !== 'all') params.category = activeTab;

      const response = await api.get('/ai-resources', { params });
      setResources(response.data.items || response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResources();
  }, [searchText, activeTab]);

  // 复制资源为自己的版本
  const handleClone = async (resource: Resource) => {
    try {
      const response = await api.post(`/ai-resources/${resource.id}/clone`);
      message.success('已复制为我的模板，可以开始编辑');
      navigate(`/user/templates/${response.data.id}/edit`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '复制失败');
    }
  };

  // 删除资源
  const handleDelete = (resource: Resource) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除模板「${resource.display_name}」吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.delete(`/ai-resources/${resource.id}`);
          message.success('删除成功');
          loadResources();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  // 切换启用/禁用状态
  const handleToggle = async (resource: Resource) => {
    try {
      await api.patch(`/ai-resources/${resource.id}/toggle`);
      message.success(resource.is_active ? '已禁用' : '已启用');
      loadResources();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: Resource) => (
        <div>
          <div className="font-medium">{text}</div>
          <div className="text-xs text-slate-500">{record.name}</div>
        </div>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category: string) => (
        <Tag color={categoryColorMap[category] || 'default'}>
          {categoryMap[category] || category}
        </Tag>
      ),
    },
    {
      title: '来源',
      key: 'source',
      width: 100,
      render: (_: any, record: Resource) => (
        <Tag color={record.is_builtin ? 'gold' : 'geekblue'}>
          {record.is_builtin ? '系统内置' : '我的模板'}
        </Tag>
      ),
    },
    {
      title: '状态',
      key: 'is_active',
      width: 80,
      render: (_: any, record: Resource) => {
        // 内置资源不显示开关（用户无法切换）
        if (record.is_builtin) {
          return (
            <Tag color={record.is_active ? 'green' : 'default'}>
              {record.is_active ? '启用' : '禁用'}
            </Tag>
          );
        }
        return (
          <Switch
            size="small"
            checked={record.is_active}
            onChange={() => handleToggle(record)}
            checkedChildren="启用"
            unCheckedChildren="禁用"
          />
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: Resource) => (
        <Space>
          {record.is_builtin ? (
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleClone(record)}
            >
              复制为我的
            </Button>
          ) : (
            <>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => navigate(`/user/templates/${record.id}/edit`)}
              >
                编辑
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record)}
              >
                删除
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = [
    { key: 'all', label: '全部' },
    { key: 'methodology', label: '方法论' },
    { key: 'output_style', label: '输出风格' },
    { key: 'qa_rules', label: '质检标准' },
    { key: 'template', label: '模板案例' },
    { key: 'breakdown_prompt', label: '拆解提示词' },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">提示词模板</h1>
            <p className="text-sm text-slate-400 mt-1">
              管理 AI 改编使用的提示词模板，可以复制系统模板创建自己的版本
            </p>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/user/templates/new')}
          >
            新建模板
          </Button>
        </div>

        <div className="mb-4">
          <GlassInput
            placeholder="搜索模板名称或描述"
            allowClear
            style={{ width: 300 }}
            onPressEnter={(e) => setSearchText((e.target as HTMLInputElement).value)}
            onChange={(e) => !e.target.value && setSearchText('')}
          />
        </div>

        <GlassTabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

        <GlassTable
          columns={columns}
          dataSource={resources}
          rowKey="id"
          loading={loading}
          locale={{
            emptyText: (
              <Empty
                description="暂无模板"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total: number) => `共 ${total} 个模板`,
          }}
        />
      </GlassCard>
    </div>
  );
};

export default TemplatesPage;
