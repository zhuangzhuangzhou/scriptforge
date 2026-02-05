import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Tag, Tabs, message } from 'antd';
import { EyeOutlined, LockOutlined, TeamOutlined, GlobalOutlined } from '@ant-design/icons';

interface Skill {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  visibility: string;
  owner_id: string;
  is_builtin: boolean;
}

interface SkillSelectorProps {
  category?: string;
  onSelect?: (skill: Skill) => void;
  mode?: 'select' | 'list';
}

const SkillAccessControl: React.FC<SkillSelectorProps> = ({
  category,
  onSelect,
  mode = 'list'
}) => {
  const [loading, setLoading] = useState(false);
  const [publicSkills, setPublicSkills] = useState<Skill[]>([]);
  const [mySkills, setMySkills] = useState<Skill[]>([]);
  const [sharedSkills, setSharedSkills] = useState<Skill[]>([]);
  const [activeTab, setActiveTab] = useState('public');

  useEffect(() => {
    loadSkills();
  }, []);

  const loadSkills = async () => {
    setLoading(true);
    try {
      // 加载公共Skills
      const publicRes = await fetch('/api/v1/skills/public', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const publicData = await publicRes.json();
      setPublicSkills(publicData.skills || []);

      // 加载我的Skills
      const myRes = await fetch('/api/v1/skills/my', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const myData = await myRes.json();
      setMySkills(myData.skills || []);

      // 加载分享给我的Skills
      const sharedRes = await fetch('/api/v1/skills/shared', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const sharedData = await sharedRes.json();
      setSharedSkills(sharedData.skills || []);

    } catch (error) {
      message.error('加载Skills失败');
    } finally {
      setLoading(false);
    }
  };

  const getVisibilityTag = (visibility: string, isBuiltin: boolean) => {
    if (isBuiltin) {
      return <Tag icon={<GlobalOutlined />} color="gold">内置</Tag>;
    }
    if (visibility === 'public') {
      return <Tag icon={<GlobalOutlined />} color="blue">公开</Tag>;
    }
    if (visibility === 'shared') {
      return <Tag icon={<TeamOutlined />} color="purple">协作</Tag>;
    }
    return <Tag icon={<LockOutlined />} color="default">私有</Tag>;
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: Skill) => (
        <Space direction="vertical" size={0}>
          <span className="font-medium">{text}</span>
          <span className="text-gray-400 text-xs">{record.name}</span>
        </Space>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (cat: string) => (
        <Tag color={cat === 'breakdown' ? 'blue' : 'green'}>
          {cat === 'breakdown' ? '剧情拆解' : '剧本生成'}
        </Tag>
      )
    },
    {
      title: '权限',
      key: 'visibility',
      render: (_: any, record: Skill) => getVisibilityTag(record.visibility, record.is_builtin)
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Skill) => (
        <Space>
          {onSelect && (
            <Button
              type="link"
              onClick={() => onSelect(record)}
            >
              选择
            </Button>
          )}
        </Space>
      )
    }
  ];

  const tabItems = [
    {
      key: 'public',
      label: (
        <span>
          <GlobalOutlined />
          公开Skills ({publicSkills.length})
        </span>
      ),
      children: (
        <Table
          dataSource={publicSkills}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      )
    },
    {
      key: 'my',
      label: (
        <span>
          <LockOutlined />
          我的Skills ({mySkills.length})
        </span>
      ),
      children: (
        <Table
          dataSource={mySkills}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      )
    },
    {
      key: 'shared',
      label: (
        <span>
          <TeamOutlined />
          协作Skills ({sharedSkills.length})
        </span>
      ),
      children: (
        <Table
          dataSource={sharedSkills}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      )
    }
  ];

  return (
    <Card title="可用Skills">
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
      />
    </Card>
  );
};

export default SkillAccessControl;
