import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Button, Input, Select, Tag, Space, message, Modal, Card, Tabs } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, SearchOutlined, CopyOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Search } = Input;
const { Option } = Select;
const { TabPane } = Tabs;

interface Skill {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  is_template_based: boolean;
  is_builtin: boolean;
  is_active: boolean;
  visibility: string;
  owner_id: string;
  created_at: string;
}

const SkillsPage: React.FC = () => {
  const navigate = useNavigate();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [activeTab, setActiveTab] = useState('all');

  // 加载 Skills 列表
  const loadSkills = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchText) params.search = searchText;
      if (categoryFilter) params.category = categoryFilter;

      const response = await axios.get('/api/v1/skills', { params });
      setSkills(response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSkills();
  }, [searchText, categoryFilter]);

  // 复制 Skill
  const handleClone = async (skill: Skill) => {
    try {
      const response = await axios.post(`/api/v1/skills/${skill.id}/clone`);
      message.success('复制成功！您现在可以编辑自己的版本');
      loadSkills();
      // 跳转到编辑页面
      navigate(`/admin/skills/${response.data.id}/edit`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '复制失败');
    }
  };

  // 删除 Skill
  const handleDelete = (skill: Skill) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除 Skill "${skill.display_name}" 吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await axios.delete(`/api/v1/skills/${skill.id}`);
          message.success('删除成功');
          loadSkills();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  // 根据标签页筛选
  const filteredSkills = skills.filter(skill => {
    if (activeTab === 'builtin') return skill.is_builtin;
    if (activeTab === 'mine') return !skill.is_builtin;
    return true;
  });

  // 表格列定义
  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: Skill) => (
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
      title: '类型',
      dataIndex: 'is_template_based',
      key: 'is_template_based',
      width: 100,
      render: (isTemplate: boolean) => (
        <Tag color={isTemplate ? 'cyan' : 'orange'}>
          {isTemplate ? '模板' : '代码'}
        </Tag>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_: any, record: Skill) => (
        <Space>
          {record.is_builtin && <Tag color="gold">内置</Tag>}
          {record.visibility === 'private' && <Tag>私有</Tag>}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      render: (_: any, record: Skill) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => navigate(`/admin/skills/${record.id}/test`)}
          >
            测试
          </Button>
          {record.is_builtin ? (
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleClone(record)}
            >
              复制
            </Button>
          ) : (
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => navigate(`/admin/skills/${record.id}/edit`)}
            >
              编辑
            </Button>
          )}
          {!record.is_builtin && (
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6">
      <Card>
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold">Skill 管理</h1>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/admin/skills/new')}
          >
            新建 Skill
          </Button>
        </div>

        <div className="mb-4 flex gap-4">
          <Search
            placeholder="搜索 Skill 名称或描述"
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

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="全部" key="all" />
          <TabPane tab="系统内置" key="builtin" />
          <TabPane tab="我的 Skills" key="mine" />
        </Tabs>

        <Table
          columns={columns}
          dataSource={filteredSkills}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 Skill`,
          }}
        />

        {activeTab === 'builtin' && (
          <div className="mt-4 p-4 bg-blue-50 rounded">
            <p className="text-sm text-blue-700">
              💡 提示：系统内置的 Skills 不能直接编辑。如果您想修改 Prompt，请点击"复制"按钮创建自己的版本。
            </p>
          </div>
        )}
      </Card>
    </div>
  );
};

export default SkillsPage;
