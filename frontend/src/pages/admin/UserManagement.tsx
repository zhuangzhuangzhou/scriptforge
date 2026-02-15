import React, { useEffect, useState } from 'react';
import { Button, Space, Form, Select, InputNumber, message } from 'antd';
import { EditOutlined, UserOutlined, ReloadOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';
import { adminApi } from '../../services/api';
import { UserTier } from '../../types';
import { GlassTable } from '../../components/ui/GlassTable';
import { GlassCard } from '../../components/ui/GlassCard';
import { GlassModal } from '../../components/ui/GlassModal';

const { Option } = Select;

interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  tier: UserTier;
  credits: number;  // 积分余额
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  const fetchUsers = async (page = 1) => {
    setLoading(true);
    try {
      const response = await adminApi.getUsers(page);
      setUsers(response.data.items);
      setTotal(response.data.total);
      setCurrentPage(page);
    } catch (error) {
      console.error('Fetch users error:', error);
      message.error('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({
      role: user.role,
      tier: user.tier,
      credits: user.credits,
      is_active: user.is_active
    });
    setIsModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      if (editingUser) {
        await adminApi.updateUser(editingUser.id, values);
        message.success('用户更新成功');
        setIsModalVisible(false);
        fetchUsers(currentPage);
      }
    } catch (error) {
      console.error('Update user error:', error);
      message.error('更新失败');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 100,
      render: (id: string) => <span className="text-slate-500 font-mono text-xs">{id.substring(0, 8)}...</span>
    },
    {
      title: '用户名',
      dataIndex: 'username',
      render: (text: string, record: User) => (
        <Space>
          <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-cyan-400">
            <UserOutlined />
          </div>
          <div className="flex flex-col">
            <span className="text-slate-200 font-medium">{text}</span>
            <span className="text-slate-500 text-xs">{record.email}</span>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      render: (role: string) => (
        <span className={`px-2 py-1 rounded text-xs border ${
          role === 'admin'
            ? 'bg-red-500/10 border-red-500/30 text-red-400'
            : 'bg-blue-500/10 border-blue-500/30 text-blue-400'
        }`}>
          {role.toUpperCase()}
        </span>
      ),
    },
    {
      title: '等级',
      dataIndex: 'tier',
      render: (tier: string) => {
        const colors: Record<string, string> = {
          FREE: 'bg-slate-500/10 border-slate-500/30 text-slate-400',
          CREATOR: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
          STUDIO: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
          ENTERPRISE: 'bg-amber-500/10 border-amber-500/30 text-amber-400'
        };
        return (
          <span className={`px-2 py-1 rounded text-xs border ${colors[tier] || colors.FREE}`}>
            {tier}
          </span>
        );
      }
    },
    {
      title: '积分',
      dataIndex: 'credits',
      render: (val: number) => <span className="font-mono text-emerald-400">{val?.toLocaleString() ?? 0}</span>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      render: (active: boolean) => (
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${active ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-red-500'}`} />
          <span className={active ? 'text-slate-300' : 'text-slate-500'}>
            {active ? '正常' : '禁用'}
          </span>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: User) => (
        <Button
          type="text"
          icon={<EditOutlined />}
          className="text-cyan-400 hover:text-cyan-300 hover:bg-cyan-950/30"
          onClick={() => handleEdit(record)}
        >
          编辑
        </Button>
      ),
    },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent m-0">
              用户管理
            </h1>
            <p className="text-slate-400 mt-1">管理系统用户、角色与权限配置</p>
          </div>
          <Button
            onClick={() => fetchUsers(currentPage)}
            icon={<ReloadOutlined />}
            className="border-slate-700 text-slate-300 hover:text-cyan-400 hover:border-cyan-400 bg-slate-900/50 backdrop-blur"
          >
            刷新列表
          </Button>
        </div>

        <GlassCard className="shadow-2xl">
          <GlassTable
            columns={columns}
            dataSource={users}
            rowKey="id"
            loading={loading}
            pagination={{
              current: currentPage,
              total: total,
              pageSize: 20,
              onChange: (page) => fetchUsers(page),
              showSizeChanger: false,
              className: "p-4"
            }}
          />
        </GlassCard>

        <GlassModal
          title={<span className="text-slate-100">编辑用户: {editingUser?.username}</span>}
          open={isModalVisible}
          onOk={handleModalOk}
          onCancel={() => setIsModalVisible(false)}
          okText="保存更改"
          cancelText="取消"
          okButtonProps={{ className: "bg-cyan-600 hover:bg-cyan-500 border-none" }}
          cancelButtonProps={{ className: "border-slate-600 text-slate-300 hover:text-white hover:border-slate-500" }}
        >
          <Form form={form} layout="vertical" className="mt-6">
            <Form.Item name="role" label={<span className="text-slate-300">角色</span>}>
              <Select>
                <Option value="user">User</Option>
                <Option value="admin">Admin</Option>
              </Select>
            </Form.Item>

            <Form.Item name="tier" label={<span className="text-slate-300">等级 (Tier)</span>}>
              <Select>
                <Option value="FREE">FREE</Option>
                <Option value="CREATOR">CREATOR</Option>
                <Option value="STUDIO">STUDIO</Option>
                <Option value="ENTERPRISE">ENTERPRISE</Option>
              </Select>
            </Form.Item>

            <Form.Item name="credits" label={<span className="text-slate-300">积分余额</span>}>
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>

            <Form.Item name="is_active" label={<span className="text-slate-300">账号状态</span>}>
              <Select>
                <Option value={true}>正常 (Active)</Option>
                <Option value={false}>禁用 (Inactive)</Option>
              </Select>
            </Form.Item>
          </Form>
        </GlassModal>
      </motion.div>
    </div>
  );
};

export default UserManagement;
