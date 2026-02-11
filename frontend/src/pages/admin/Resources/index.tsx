import React, { useState, useEffect } from 'react';
import { Button, Tag, Space, message, Modal } from 'antd';
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
  scope: string;
  visibility: string;
  owner_id: string;
  created_at: string;
}

const categoryMap: Record<string, string> = {
  methodology: '方法论',
  output_style: '输出风格',
  template: '模板',
  example: '示例',
};

const categoryColorMap: Record<string, string> = {
  methodology: 'blue',
  output_style: 'purple',
  template: 'cyan',
  example: 'green',
};

const ResourcesPage: React.FC = () => {
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const navigate = useNavigate();

  // 加载资源列表
  const loadResources = async () => {
    setLoading(true);
    try {
      const params: any = {};
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

  // 复制资源
  const handleClone = async (resource: Resource) => {
    try {
      const response = await api.post(`/ai-resources/${resource.id}/clone`);
      message.success('复制成功，可以编辑自己的版本');
      navigate(`/admin/resources/${response.data.id}/edit`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '复制失败');
    }
  };

  // 删除资源
  const handleDelete = (resource: Resource) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除资源「${resource.display_name}」吗？`,
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
      width: 120,
      render: (category: string) => (
        <Tag color={categoryColorMap[category] || 'default'}>
          {categoryMap[category] || category}
        </Tag>
      ),
    },
    {
      title: '类型',
      key: 'scope',
      width: 100,
      render: (_: any, record: Resource) => (
        <Tag color={record.scope === 'builtin' ? 'gold' : 'geekblue'}>
          {record.scope === 'builtin' ? '内置' : '自定义'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: Resource) => (
        <Space>
          {record.scope === 'builtin' ? (
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleClone(record)}
            >
              复制
            </Button>
          ) : (
            <>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => navigate(`/admin/resources/${record.id}/edit`)}
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
    { key: 'template', label: '模板' },
    { key: 'example', label: '示例' },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-slate-100">资源文档管理</h1>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/admin/resources/new')}
          >
            新建资源
          </Button>
        </div>

        <div className="mb-4">
          <GlassInput
            placeholder="搜索资源名称或描述"
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
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total: number) => `共 ${total} 个资源`,
          }}
        />
      </GlassCard>
    </div>
  );
};

export default ResourcesPage;
