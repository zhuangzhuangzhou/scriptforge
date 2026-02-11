import React, { useState, useEffect } from 'react';
import { Button, Tag, Space, message, Modal, Switch } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, CopyOutlined } from '@ant-design/icons';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassTabs } from '../../../components/ui/GlassTabs';
import { GlassModal } from '../../../components/ui/GlassModal';
import SkillEditor from './SkillEditor';
import SkillTester from './SkillTester';

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
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [activeTab, setActiveTab] = useState('all');

  // 弹窗状态
  const [editorVisible, setEditorVisible] = useState(false);
  const [editingSkillId, setEditingSkillId] = useState<string | null>(null);
  const [testerVisible, setTesterVisible] = useState(false);
  const [testingSkillId, setTestingSkillId] = useState<string | null>(null);
  const [testingSkillName, setTestingSkillName] = useState('');

  // 加载 Skills 列表
  const loadSkills = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchText) params.search = searchText;
      if (categoryFilter) params.category = categoryFilter;

      const response = await api.get('/skills', { params });
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
      const response = await api.post(`/skills/${skill.id}/clone`);
      message.success('复制成功！您现在可以编辑自己的版本');
      loadSkills();
      // 打开编辑弹窗
      setEditingSkillId(response.data.id);
      setEditorVisible(true);
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
          await api.delete(`/skills/${skill.id}`);
          message.success('删除成功');
          loadSkills();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  const handleToggleActive = async (skill: Skill) => {
    try {
      await api.put(`/skills/${skill.id}`, { is_active: !skill.is_active });
      message.success(skill.is_active ? '已禁用' : '已启用');
      loadSkills();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const handleEdit = (skillId: string | null) => {
    setEditingSkillId(skillId);
    setEditorVisible(true);
  };

  const handleTest = (skill: Skill) => {
    setTestingSkillId(skill.id);
    setTestingSkillName(skill.display_name);
    setTesterVisible(true);
  };

  const handleEditorSaved = () => {
    setEditorVisible(false);
    setEditingSkillId(null);
    loadSkills();
  };

  const handleEditorCancel = () => {
    setEditorVisible(false);
    setEditingSkillId(null);
  };

  const handleTesterClose = () => {
    setTesterVisible(false);
    setTestingSkillId(null);
    setTestingSkillName('');
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
      width: 150,
      render: (_: any, record: Skill) => (
        <Space>
          <Switch
            size="small"
            checked={record.is_active}
            onChange={() => handleToggleActive(record)}
          />
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
            onClick={() => handleTest(record)}
          >
            测试
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record.id)}
          >
            编辑
          </Button>
          {record.is_builtin && (
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleClone(record)}
            >
              复制
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const tabItems = [
    { key: 'all', label: '全部' },
    { key: 'builtin', label: '系统内置' },
    { key: 'mine', label: '我的 Skills' },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-slate-100">Skill 管理</h1>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleEdit(null)}
          >
            新建 Skill
          </Button>
        </div>

        <div className="mb-4 flex gap-4">
          <GlassInput
            placeholder="搜索 Skill 名称或描述"
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

        <GlassTabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

        <GlassTable
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
          <div className="mt-4 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
            <p className="text-sm text-cyan-400">
              💡 提示：系统内置的 Skills 不能直接编辑。如果您想修改 Prompt，请点击"复制"按钮创建自己的版本。
            </p>
          </div>
        )}
      </GlassCard>

      {/* 编辑/新建弹窗 */}
      <GlassModal
        title={editingSkillId ? '编辑 Skill' : '新建 Skill'}
        open={editorVisible}
        onCancel={handleEditorCancel}
        footer={null}
        width={900}
        destroyOnClose
      >
        <SkillEditor
          skillId={editingSkillId}
          onSaved={handleEditorSaved}
          onCancel={handleEditorCancel}
        />
      </GlassModal>

      {/* 测试弹窗 */}
      <GlassModal
        title={`测试 Skill: ${testingSkillName}`}
        open={testerVisible}
        onCancel={handleTesterClose}
        footer={null}
        width={1000}
        destroyOnClose
      >
        {testingSkillId && (
          <SkillTester
            skillId={testingSkillId}
          />
        )}
      </GlassModal>
    </div>
  );
};

export default SkillsPage;
