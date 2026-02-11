import React, { useState, useEffect } from 'react';
import { Button, Tag, Space, message, Modal } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassModal } from '../../../components/ui/GlassModal';
import AgentEditor from './AgentEditor';
import AgentTester from './AgentTester';

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
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);

  // 弹窗状态
  const [editorVisible, setEditorVisible] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null);
  const [testerVisible, setTesterVisible] = useState(false);
  const [testingAgentId, setTestingAgentId] = useState<string | null>(null);
  const [testingAgentName, setTestingAgentName] = useState('');

  const loadAgents = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchText) params.search = searchText;
      if (categoryFilter) params.category = categoryFilter;

      const response = await api.get('/simple-agents', { params });
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
          await api.delete(`/simple-agents/${agent.id}`);
          message.success('删除成功');
          loadAgents();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  const handleEdit = (agentId: string | null) => {
    setEditingAgentId(agentId);
    setEditorVisible(true);
  };

  const handleTest = (agent: Agent) => {
    setTestingAgentId(agent.id);
    setTestingAgentName(agent.display_name);
    setTesterVisible(true);
  };

  const handleEditorSaved = () => {
    setEditorVisible(false);
    setEditingAgentId(null);
    loadAgents();
  };

  const handleEditorCancel = () => {
    setEditorVisible(false);
    setEditingAgentId(null);
  };

  const handleTesterClose = () => {
    setTesterVisible(false);
    setTestingAgentId(null);
    setTestingAgentName('');
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
            onClick={() => handleTest(record)}
          >
            测试
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record.id)}
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
    <div className="p-6 min-h-screen bg-slate-950">
      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-slate-100">Agent 管理</h1>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleEdit(null)}
          >
            新建 Agent
          </Button>
        </div>

        <div className="mb-4 flex gap-4">
          <GlassInput
            placeholder="搜索 Agent 名称或描述"
            allowClear
            style={{ width: 300 }}
            onPressEnter={(e) => setSearchText((e.target as HTMLInputElement).value)}
            onChange={(e) => !e.target.value && setSearchText('')}
          />
          <GlassSelect
            placeholder="选择分类"
            allowClear
            style={{ width: 150 }}
            onChange={setCategoryFilter}
            options={[
              { value: 'breakdown', label: '拆解' },
              { value: 'qa', label: '质检' },
              { value: 'script', label: '剧本' },
            ]}
          />
        </div>

        <GlassTable
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
      </GlassCard>

      {/* 编辑/新建弹窗 */}
      <GlassModal
        title={editingAgentId ? '编辑 Agent' : '新建 Agent'}
        open={editorVisible}
        onCancel={handleEditorCancel}
        footer={null}
        width={800}
        destroyOnClose
      >
        <AgentEditor
          agentId={editingAgentId}
          onSaved={handleEditorSaved}
          onCancel={handleEditorCancel}
        />
      </GlassModal>

      {/* 测试弹窗 */}
      <GlassModal
        title={`测试 Agent: ${testingAgentName}`}
        open={testerVisible}
        onCancel={handleTesterClose}
        footer={null}
        width={1000}
        destroyOnClose
      >
        {testingAgentId && (
          <AgentTester
            agentId={testingAgentId}
          />
        )}
      </GlassModal>
    </div>
  );
};

export default AgentsPage;
