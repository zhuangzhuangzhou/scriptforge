import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Space, Button, Modal, Form, Input, Select, message, Typography } from 'antd';
import { ReloadOutlined, EditOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Option } = Select;
const { Text } = Typography;

interface SkillRow {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  is_builtin: boolean;
  is_active: boolean;
  visibility?: string;
  updated_at?: string;
}

const SkillsAdmin: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [skills, setSkills] = useState<SkillRow[]>([]);
  const [category, setCategory] = useState<string>();
  const [editingSkill, setEditingSkill] = useState<SkillRow | null>(null);
  const [form] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectedRows, setSelectedRows] = useState<SkillRow[]>([]);

  const loadSkills = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/skills/skills', {
        params: {
          skip: 0,
          limit: 100,
          category
        }
      });
      setSkills(res.data.skills || []);
    } catch (error) {
      message.error('加载Skills失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSkills();
  }, [category]);

  const openEdit = (skill: SkillRow) => {
    setEditingSkill(skill);
    form.setFieldsValue({
      display_name: skill.display_name,
      description: skill.description,
      category: skill.category,
      is_active: skill.is_active,
      visibility: skill.visibility || 'public'
    });
  };

  const handleUpdate = async () => {
    if (!editingSkill) return;
    try {
      const values = await form.validateFields();
      await api.put(`/admin/skills/skills/${editingSkill.id}`, values);
      message.success('更新成功');
      setEditingSkill(null);
      loadSkills();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    }
  };

  const toggleActive = async (skill: SkillRow) => {
    const doToggle = async () => {
      try {
        await api.put(`/admin/skills/skills/${skill.id}`, { is_active: !skill.is_active });
        message.success(skill.is_active ? '已禁用' : '已启用');
        loadSkills();
      } catch (error) {
        message.error('更新状态失败');
      }
    };

    if (skill.is_builtin && skill.is_active) {
      Modal.confirm({
        title: '禁用内置 Skill',
        icon: <ExclamationCircleOutlined />,
        content: '内置 Skill 禁用可能影响默认流程和已有任务，确认禁用吗？',
        okText: '确认禁用',
        cancelText: '取消',
        onOk: doToggle
      });
      return;
    }

    await doToggle();
  };

  const deleteSkill = async (skill: SkillRow) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该 Skill 吗？此操作不可恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.delete(`/admin/skills/skills/${skill.id}`);
          message.success('删除成功');
          loadSkills();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || '删除失败');
        }
      }
    });
  };

  const bulkUpdateActive = async (isActive: boolean) => {
    if (selectedRows.length === 0) {
      message.warning('请先选择要操作的 Skill');
      return;
    }

    const containsBuiltin = selectedRows.some(row => row.is_builtin);
    const proceed = async () => {
      try {
        await Promise.all(
          selectedRows.map(row =>
            api.put(`/admin/skills/skills/${row.id}`, { is_active: isActive })
          )
        );
        message.success(isActive ? '批量启用成功' : '批量禁用成功');
        setSelectedRowKeys([]);
        setSelectedRows([]);
        loadSkills();
      } catch (error) {
        message.error('批量更新失败');
      }
    };

    if (!isActive && containsBuiltin) {
      Modal.confirm({
        title: '批量禁用内置 Skill',
        icon: <ExclamationCircleOutlined />,
        content: '所选包含内置 Skill，禁用可能影响默认流程，确认继续吗？',
        okText: '确认禁用',
        cancelText: '取消',
        onOk: proceed
      });
      return;
    }

    await proceed();
  };

  const bulkDelete = async () => {
    if (selectedRows.length === 0) {
      message.warning('请先选择要删除的 Skill');
      return;
    }

    const deletable = selectedRows.filter(row => !row.is_builtin);
    const blocked = selectedRows.filter(row => row.is_builtin);

    if (deletable.length === 0) {
      message.warning('所选均为内置 Skill，无法删除');
      return;
    }

    const infoText = blocked.length
      ? `所选包含 ${blocked.length} 个内置 Skill，将自动跳过`
      : '确定要删除所选 Skill 吗？此操作不可恢复。';

    Modal.confirm({
      title: '确认批量删除',
      icon: <ExclamationCircleOutlined />,
      content: infoText,
      okText: '确认删除',
      cancelText: '取消',
      onOk: async () => {
        try {
          await Promise.all(
            deletable.map(row => api.delete(`/admin/skills/skills/${row.id}`))
          );
          message.success('批量删除成功');
          setSelectedRowKeys([]);
          setSelectedRows([]);
          loadSkills();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || '批量删除失败');
        }
      }
    });
  };

  const bulkUpdateCategory = async (newCategory?: string) => {
    if (!newCategory) {
      message.warning('请选择分类');
      return;
    }
    if (selectedRows.length === 0) {
      message.warning('请先选择要操作的 Skill');
      return;
    }
    try {
      await Promise.all(
        selectedRows.map(row =>
          api.put(`/admin/skills/skills/${row.id}`, { category: newCategory })
        )
      );
      message.success('批量更新分类成功');
      loadSkills();
      setSelectedRowKeys([]);
      setSelectedRows([]);
    } catch (error) {
      message.error('批量更新分类失败');
    }
  };

  const bulkUpdateVisibility = async (visibility?: string) => {
    if (!visibility) {
      message.warning('请选择权限');
      return;
    }
    if (selectedRows.length === 0) {
      message.warning('请先选择要操作的 Skill');
      return;
    }
    try {
      await Promise.all(
        selectedRows.map(row =>
          api.put(`/admin/skills/skills/${row.id}`, { visibility })
        )
      );
      message.success('批量更新权限成功');
      loadSkills();
      setSelectedRowKeys([]);
      setSelectedRows([]);
    } catch (error) {
      message.error('批量更新权限失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (_: string, record: SkillRow) => (
        <Space direction="vertical" size={0}>
          <span>{record.display_name}</span>
          <span style={{ color: '#999', fontSize: 12 }}>{record.name}</span>
        </Space>
      )
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (value: string) => <Tag color={value === 'breakdown' ? 'blue' : 'green'}>{value}</Tag>
    },
    {
      title: '权限',
      dataIndex: 'visibility',
      key: 'visibility',
      render: (value: string) => <Tag>{value || 'public'}</Tag>
    },
    {
      title: '类型',
      dataIndex: 'is_builtin',
      key: 'is_builtin',
      render: (value: boolean) => <Tag color={value ? 'gold' : 'default'}>{value ? '内置' : '自定义'}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (value: boolean) => <Tag color={value ? 'success' : 'error'}>{value ? '启用' : '禁用'}</Tag>
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: SkillRow) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Button size="small" onClick={() => toggleActive(record)}>
            {record.is_active ? '禁用' : '启用'}
          </Button>
          {!record.is_builtin && (
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => deleteSkill(record)}>
              删除
            </Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <div>
      <Card
        bordered={false}
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            <Select
              allowClear
              placeholder="分类过滤"
              style={{ width: 160 }}
              value={category}
              onChange={setCategory}
            >
              <Option value="breakdown">breakdown</Option>
              <Option value="script">script</Option>
              <Option value="analysis">analysis</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadSkills}>
              刷新
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 12 }}>
          <Button onClick={() => bulkUpdateActive(true)} disabled={selectedRows.length === 0}>
            批量启用
          </Button>
          <Button onClick={() => bulkUpdateActive(false)} disabled={selectedRows.length === 0}>
            批量禁用
          </Button>
          <Button danger onClick={bulkDelete} disabled={selectedRows.length === 0}>
            批量删除
          </Button>
          <Select
            allowClear
            placeholder="批量分类"
            style={{ width: 160 }}
            onChange={bulkUpdateCategory}
          >
            <Option value="breakdown">breakdown</Option>
            <Option value="script">script</Option>
            <Option value="analysis">analysis</Option>
          </Select>
          <Select
            allowClear
            placeholder="批量权限"
            style={{ width: 160 }}
            onChange={bulkUpdateVisibility}
          >
            <Option value="public">public</Option>
            <Option value="private">private</Option>
            <Option value="shared">shared</Option>
          </Select>
          <Text type="secondary">
            内置 Skill 不可删除，可禁用但建议谨慎操作。
          </Text>
        </Space>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={skills}
          loading={loading}
          pagination={false}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys, rows) => {
              setSelectedRowKeys(keys);
              setSelectedRows(rows as SkillRow[]);
            }
          }}
        />
      </Card>

      <Modal
        title="编辑 Skill"
        open={!!editingSkill}
        onCancel={() => setEditingSkill(null)}
        onOk={handleUpdate}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Select>
              <Option value="breakdown">breakdown</Option>
              <Option value="script">script</Option>
              <Option value="analysis">analysis</Option>
            </Select>
          </Form.Item>
          <Form.Item name="visibility" label="权限">
            <Select>
              <Option value="public">public</Option>
              <Option value="private">private</Option>
              <Option value="shared">shared</Option>
            </Select>
          </Form.Item>
          <Form.Item name="is_active" label="状态" rules={[{ required: true }]}>
            <Select>
              <Option value={true}>启用</Option>
              <Option value={false}>禁用</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SkillsAdmin;
