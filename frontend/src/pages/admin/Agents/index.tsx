import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Button, Input, Select, Tag, Space, message, Modal, Card } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Search } = Input;
const { Option } = Select;

interface Agent {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  is_builtin: boolean;
  is_active: boolean;
  visibility: string;
  created_at: string;
}

const AgentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);

  const loadAgents = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchText) params.search = searchText;
      if (categoryFilter) params.category = categoryFilter;

      const response = await axios.get('/api/v1/simple-agents', { params });
      setAgents(response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, [searchText, categoryFilter]);

  const handleDelete = (agent: Agent) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除 Agent "${agent.display_name}" 吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await axios.delete(`/api/v1/simple-agents/${agent.id}`);
          message.success('删除成功');
          loadAgents();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: Agent) => (
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
      render: (category: string) => {
        const colorMap: Record<string, string> = {
          breakdown: 'blue',
          qa: 'green',
          script: 'purple',
        };
        return <Tag color={colorMap[category] || 'default'}>{category}</Tag>;
      },
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_: any, record: Agent) => (
        <Space>
          {record.is_builtin && <Tag color="gold">内置</Tag>}
          {record.visibility === 'private' && <Tag>私有</Tag>}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: Agent) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => navigate(`/admin/agents/${record.id}/test`)}
          >
            测试
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/admin/agents/${record.id}/edit`)}
            disabled={record.is_builtin}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
            disabled={record.is_builtin}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6">
      <Card>
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold">Agent 管理</h1>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/admin/agents/new')}
          >
            新建 Agent
          </Button>
        </div>

        <div className="mb-4 flex gap-4">
          <Search
            placeholder="搜索 Agent 名称或描述"
            allowClear
            style={{ width: 300 }}
            onSearch={setSearchText}
            onChange={(e) => !e.target.value && setSearchText('')}
          />
          <Select
            placeholder="选择分类"
            allowClear
            style={{ width: 150 }}
            onChange={setCategoryFilter}
          >
            <Option value="breakdown">拆解</Option>
            <Option value="qa">质检</Option>
            <Option value="script">剧本</Option>
          </Select>
        </div>

        <Table
          columns={columns}
          dataSource={agents}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 Agent`,
          }}
        />
      </Card>
    </div>
  );
};

export default AgentsPage;
