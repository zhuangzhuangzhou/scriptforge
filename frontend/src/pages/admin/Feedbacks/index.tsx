import React, { useState, useEffect } from 'react';
import { Button, Space, Tag, message, Input } from 'antd';
import { EyeOutlined, EditOutlined } from '@ant-design/icons';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassModal } from '../../../components/ui/GlassModal';
import { feedbackApi } from '../../../services/api';

interface Feedback {
  id: string;
  user_id: string;
  username: string | null;
  type: string;
  content: string;
  contact: string | null;
  status: string;
  admin_note: string | null;
  created_at: string;
  updated_at: string;
}

const STATUS_OPTIONS = [
  { value: 'pending', label: '待处理', color: 'default' },
  { value: 'processing', label: '处理中', color: 'processing' },
  { value: 'resolved', label: '已完成', color: 'success' },
  { value: 'closed', label: '已关闭', color: 'default' },
];

const TYPE_OPTIONS = [
  { value: 'suggestion', label: '需求建议', color: 'blue' },
  { value: 'bug', label: '问题报告', color: 'orange' },
  { value: 'other', label: '其他', color: 'default' },
];

const Feedbacks: React.FC = () => {
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // 筛选条件
  const [filters, setFilters] = useState({
    type: undefined as string | undefined,
    status: undefined as string | undefined,
  });

  // 详情弹窗
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentFeedback, setCurrentFeedback] = useState<Feedback | null>(null);

  // 编辑弹窗
  const [editVisible, setEditVisible] = useState(false);
  const [editStatus, setEditStatus] = useState('');
  const [editNote, setEditNote] = useState('');
  const [editLoading, setEditLoading] = useState(false);

  const loadFeedbacks = async () => {
    setLoading(true);
    try {
      const response = await feedbackApi.admin.list({
        page,
        page_size: pageSize,
        ...filters,
      });
      setFeedbacks(response.data.items);
      setTotal(response.data.total);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeedbacks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, filters]);

  const handleViewDetail = (record: Feedback) => {
    setCurrentFeedback(record);
    setDetailVisible(true);
  };

  const handleEdit = (record: Feedback) => {
    setCurrentFeedback(record);
    setEditStatus(record.status);
    setEditNote(record.admin_note || '');
    setEditVisible(true);
  };

  const handleEditSubmit = async () => {
    if (!currentFeedback) return;

    setEditLoading(true);
    try {
      await feedbackApi.admin.update(currentFeedback.id, {
        status: editStatus,
        admin_note: editNote || undefined,
      });
      message.success('更新成功');
      setEditVisible(false);
      loadFeedbacks();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '更新失败');
    } finally {
      setEditLoading(false);
    }
  };

  const getTypeTag = (type: string) => {
    const option = TYPE_OPTIONS.find(o => o.value === type);
    return <Tag color={option?.color || 'default'}>{option?.label || type}</Tag>;
  };

  const getStatusTag = (status: string) => {
    const option = STATUS_OPTIONS.find(o => o.value === status);
    return <Tag color={option?.color || 'default'}>{option?.label || status}</Tag>;
  };

  const columns = [
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (username: string | null) => username || '-',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => getTypeTag(type),
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      width: 300,
      ellipsis: true,
    },
    {
      title: '联系方式',
      dataIndex: 'contact',
      key: 'contact',
      width: 150,
      ellipsis: true,
      render: (contact: string | null) => contact || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (created_at: string) => new Date(created_at).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: Feedback) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            处理
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">用户反馈管理</h1>
      </div>

      {/* 筛选栏 */}
      <div className="mb-4 flex gap-4">
        <GlassSelect
          placeholder="反馈类型"
          allowClear
          style={{ width: 150 }}
          onChange={(value) => setFilters({ ...filters, type: value })}
          options={TYPE_OPTIONS}
        />
        <GlassSelect
          placeholder="处理状态"
          allowClear
          style={{ width: 150 }}
          onChange={(value) => setFilters({ ...filters, status: value })}
          options={STATUS_OPTIONS}
        />
      </div>

      {/* 表格 */}
      <GlassTable
        columns={columns}
        dataSource={feedbacks}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1200 }}
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

      {/* 详情弹窗 */}
      <GlassModal
        title="反馈详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
          <Button
            key="edit"
            type="primary"
            onClick={() => {
              setDetailVisible(false);
              if (currentFeedback) handleEdit(currentFeedback);
            }}
          >
            处理
          </Button>,
        ]}
        width={600}
      >
        {currentFeedback && (
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <div className="text-slate-400 text-sm mb-1">用户</div>
                <div className="text-white">{currentFeedback.username || '-'}</div>
              </div>
              <div className="flex-1">
                <div className="text-slate-400 text-sm mb-1">类型</div>
                <div>{getTypeTag(currentFeedback.type)}</div>
              </div>
              <div className="flex-1">
                <div className="text-slate-400 text-sm mb-1">状态</div>
                <div>{getStatusTag(currentFeedback.status)}</div>
              </div>
            </div>
            <div>
              <div className="text-slate-400 text-sm mb-1">联系方式</div>
              <div className="text-white">{currentFeedback.contact || '未提供'}</div>
            </div>
            <div>
              <div className="text-slate-400 text-sm mb-1">反馈内容</div>
              <div className="text-white bg-slate-800/50 p-3 rounded-lg whitespace-pre-wrap">
                {currentFeedback.content}
              </div>
            </div>
            {currentFeedback.admin_note && (
              <div>
                <div className="text-slate-400 text-sm mb-1">处理备注</div>
                <div className="text-white bg-slate-800/50 p-3 rounded-lg whitespace-pre-wrap">
                  {currentFeedback.admin_note}
                </div>
              </div>
            )}
            <div className="flex gap-4 text-sm text-slate-500">
              <div>提交时间：{new Date(currentFeedback.created_at).toLocaleString('zh-CN')}</div>
              <div>更新时间：{new Date(currentFeedback.updated_at).toLocaleString('zh-CN')}</div>
            </div>
          </div>
        )}
      </GlassModal>

      {/* 编辑弹窗 */}
      <GlassModal
        title="处理反馈"
        open={editVisible}
        onCancel={() => setEditVisible(false)}
        onOk={handleEditSubmit}
        confirmLoading={editLoading}
        okText="保存"
        cancelText="取消"
      >
        <div className="space-y-4 py-4">
          <div>
            <div className="text-slate-300 text-sm mb-2">处理状态</div>
            <GlassSelect
              value={editStatus}
              onChange={setEditStatus}
              style={{ width: '100%' }}
              options={STATUS_OPTIONS}
            />
          </div>
          <div>
            <div className="text-slate-300 text-sm mb-2">处理备注</div>
            <Input.TextArea
              value={editNote}
              onChange={(e) => setEditNote(e.target.value)}
              placeholder="添加处理备注..."
              rows={4}
              maxLength={2000}
              showCount
            />
          </div>
        </div>
      </GlassModal>
    </div>
  );
};

export default Feedbacks;
