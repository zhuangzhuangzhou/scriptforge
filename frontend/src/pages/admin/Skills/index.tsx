import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Button, Input, Select, Tag, Space, message, Modal, Card } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Search } = Input;
const { Option } = Select;

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
  created_at: string;
}

const SkillsPage: React.FC = () => {
  const navigate = useNavigate();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);

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
      width: 200,
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
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/admin/skills/${record.id}/edit`)}
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

        <Table
          columns={columns}
          dataSource={skills}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 Skill`,
          }}
        />
      </Card>
    </div>
  );
};

export default SkillsPage;
