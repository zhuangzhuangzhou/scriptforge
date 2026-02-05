import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Space, Button, Modal, Form, Select, InputNumber, message } from 'antd';
import { ReloadOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Option } = Select;

interface UserRow {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  role: string;
  balance: number;
  is_active: boolean;
  tier?: string;
  created_at?: string;
}

const UsersAdmin: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [editingUser, setEditingUser] = useState<UserRow | null>(null);
  const [form] = Form.useForm();

  const loadUsers = async (pageNum = page, size = pageSize) => {
    setLoading(true);
    try {
      const res = await api.get('/admin/users', {
        params: {
          skip: (pageNum - 1) * size,
          limit: size
        }
      });
      setUsers(res.data.users || []);
      setTotal(res.data.total || 0);
    } catch (error) {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const openEdit = (user: UserRow) => {
    setEditingUser(user);
    form.setFieldsValue({
      role: user.role,
      balance: Number(user.balance || 0),
      is_active: user.is_active
    });
  };

  const handleUpdate = async () => {
    if (!editingUser) return;
    try {
      const values = await form.validateFields();
      await api.put(`/admin/users/${editingUser.id}`, values);
      message.success('更新成功');
      setEditingUser(null);
      loadUsers();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    }
  };

  const toggleActive = async (user: UserRow) => {
    try {
      await api.put(`/admin/users/${user.id}`, { is_active: !user.is_active });
      message.success(user.is_active ? '已禁用' : '已启用');
      loadUsers();
    } catch (error) {
      message.error('更新状态失败');
    }
  };

  const columns = [
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      render: (_: string, record: UserRow) => (
        <Space direction="vertical" size={0}>
          <span>{record.username}</span>
          <span style={{ color: '#999', fontSize: 12 }}>{record.email}</span>
        </Space>
      )
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => <Tag color={role === 'admin' ? 'gold' : 'blue'}>{role}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'error'}>
          {active ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '余额',
      dataIndex: 'balance',
      key: 'balance'
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: UserRow) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Button
            size="small"
            danger={record.is_active}
            icon={record.is_active ? <StopOutlined /> : <CheckCircleOutlined />}
            onClick={() => toggleActive(record)}
          >
            {record.is_active ? '禁用' : '启用'}
          </Button>
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
          <Button icon={<ReloadOutlined />} onClick={() => loadUsers()}>
            刷新
          </Button>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={users}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, s) => {
              setPage(p);
              setPageSize(s);
              loadUsers(p, s);
            }
          }}
        />
      </Card>

      <Modal
        title="编辑用户"
        open={!!editingUser}
        onCancel={() => setEditingUser(null)}
        onOk={handleUpdate}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select>
              <Option value="user">user</Option>
              <Option value="admin">admin</Option>
            </Select>
          </Form.Item>
          <Form.Item name="balance" label="余额">
            <InputNumber style={{ width: '100%' }} min={0} step={1} />
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

export default UsersAdmin;
