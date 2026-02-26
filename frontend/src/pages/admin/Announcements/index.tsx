import React, { useState, useEffect } from 'react';
import { Button, Space, Tag, Modal, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { announcementApi } from '../../../services/api';
import AnnouncementModal from './AnnouncementModal';
import AnnouncementStats from './AnnouncementStats';

const { Search } = GlassInput;

interface Announcement {
  id: string;
  title: string;
  content: string;
  priority: string;
  type: string;
  is_published: boolean;
  published_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

const Announcements: React.FC = () => {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // 筛选条件
  const [filters, setFilters] = useState({
    priority: undefined as string | undefined,
    type: undefined as string | undefined,
    is_published: undefined as boolean | undefined,
    search: undefined as string | undefined,
  });

  // 模态框状态
  const [modalVisible, setModalVisible] = useState(false);
  const [statsModalVisible, setStatsModalVisible] = useState(false);
  const [editingAnnouncement, setEditingAnnouncement] = useState<Announcement | null>(null);
  const [statsAnnouncementId, setStatsAnnouncementId] = useState<string | null>(null);

  // 加载通知列表
  const loadAnnouncements = async () => {
    setLoading(true);
    try {
      const response = await announcementApi.admin.getAnnouncements({
        page,
        page_size: pageSize,
        ...filters,
      });
      setAnnouncements(response.data.items);
      setTotal(response.data.total);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnnouncements();
  }, [page, pageSize, filters]);

  // 创建通知
  const handleCreate = () => {
    setEditingAnnouncement(null);
    setModalVisible(true);
  };

  // 编辑通知
  const handleEdit = (record: Announcement) => {
    setEditingAnnouncement(record);
    setModalVisible(true);
  };

  // 删除通知
  const handleDelete = async (id: string) => {
    try {
      await announcementApi.admin.deleteAnnouncement(id);
      message.success('删除成功');
      loadAnnouncements();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  // 发布/取消发布
  const handleTogglePublish = async (record: Announcement) => {
    try {
      if (record.is_published) {
        await announcementApi.admin.unpublishAnnouncement(record.id);
        message.success('已取消发布');
      } else {
        await announcementApi.admin.publishAnnouncement(record.id);
        message.success('发布成功');
      }
      loadAnnouncements();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  // 查看统计
  const handleViewStats = (id: string) => {
    setStatsAnnouncementId(id);
    setStatsModalVisible(true);
  };

  // 优先级标签颜色
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'red';
      case 'warning':
        return 'orange';
      case 'info':
      default:
        return 'blue';
    }
  };

  // 类型标签颜色
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'system':
        return 'purple';
      case 'maintenance':
        return 'orange';
      case 'feature':
        return 'green';
      case 'event':
        return 'cyan';
      default:
        return 'default';
    }
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 250,
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>
          {type === 'system' && '系统通知'}
          {type === 'maintenance' && '维护公告'}
          {type === 'feature' && '新功能'}
          {type === 'event' && '活动'}
        </Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>
          {priority === 'urgent' && '紧急'}
          {priority === 'warning' && '警告'}
          {priority === 'info' && '普通'}
        </Tag>
      ),
    },
    {
      title: '发布状态',
      dataIndex: 'is_published',
      key: 'is_published',
      width: 100,
      render: (is_published: boolean) => (
        <Tag color={is_published ? 'green' : 'default'}>
          {is_published ? '已发布' : '草稿'}
        </Tag>
      ),
    },
    {
      title: '发布时间',
      dataIndex: 'published_at',
      key: 'published_at',
      width: 180,
      render: (published_at: string | null) =>
        published_at ? new Date(published_at).toLocaleString('zh-CN') : '-',
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 180,
      render: (expires_at: string | null) =>
        expires_at ? new Date(expires_at).toLocaleString('zh-CN') : '永久',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (created_at: string) => new Date(created_at).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      fixed: 'right' as const,
      render: (_: any, record: Announcement) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={record.is_published ? <CloseCircleOutlined /> : <CheckCircleOutlined />}
            onClick={() => handleTogglePublish(record)}
          >
            {record.is_published ? '取消发布' : '发布'}
          </Button>
          {record.is_published && (
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewStats(record.id)}
            >
              统计
            </Button>
          )}
          <Popconfirm
            title="确定删除这条通知吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">通知公告管理</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建通知
        </Button>
      </div>

      {/* 筛选栏 */}
      <div className="mb-4 flex gap-4">
        <Search
          placeholder="搜索标题"
          allowClear
          style={{ width: 300 }}
          onSearch={(value: string) => setFilters({ ...filters, search: value || undefined })}
        />
        <GlassSelect
          placeholder="类型"
          allowClear
          style={{ width: 150 }}
          onChange={(value) => setFilters({ ...filters, type: value })}
          options={[
            { value: 'system', label: '系统通知' },
            { value: 'maintenance', label: '维护公告' },
            { value: 'feature', label: '新功能' },
            { value: 'event', label: '活动' },
          ]}
        />
        <GlassSelect
          placeholder="优先级"
          allowClear
          style={{ width: 150 }}
          onChange={(value) => setFilters({ ...filters, priority: value })}
          options={[
            { value: 'info', label: '普通' },
            { value: 'warning', label: '警告' },
            { value: 'urgent', label: '紧急' },
          ]}
        />
        <GlassSelect
          placeholder="发布状态"
          allowClear
          style={{ width: 150 }}
          onChange={(value) => setFilters({ ...filters, is_published: value === 'true' ? true : value === 'false' ? false : undefined })}
          options={[
            { value: 'true', label: '已发布' },
            { value: 'false', label: '草稿' },
          ]}
        />
      </div>

      {/* 表格 */}
      <GlassTable
        columns={columns}
        dataSource={announcements}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1400 }}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => {
            setPage(page);
            setPageSize(pageSize);
          },
        }}
      />

      {/* 创建/编辑模态框 */}
      <AnnouncementModal
        visible={modalVisible}
        announcement={editingAnnouncement}
        onCancel={() => setModalVisible(false)}
        onSuccess={() => {
          setModalVisible(false);
          loadAnnouncements();
        }}
      />

      {/* 统计模态框 */}
      <AnnouncementStats
        visible={statsModalVisible}
        announcementId={statsAnnouncementId}
        onCancel={() => setStatsModalVisible(false)}
      />
    </div>
  );
};

export default Announcements;
