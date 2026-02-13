import React, { useState, useEffect, useCallback } from 'react';
import { Button, Tag, message, DatePicker, Tooltip } from 'antd';
import { ReloadOutlined, EyeOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassTabs } from '../../../components/ui/GlassTabs';
import TaskDetailDrawer from './TaskDetailDrawer';

const { RangePicker } = DatePicker;

interface Task {
  id: string;
  task_type: string;
  status: string;
  progress: number;
  current_step: string | null;
  error_message: string | null;
  retry_count: number;
  project_id: string | null;
  project_name: string | null;
  batch_id: string | null;
  batch_name: string | null;
  celery_task_id: string | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

interface StatusSummary {
  queued: number;
  running: number;
  completed: number;
  failed: number;
}

interface LogStats {
  total_tasks: number;
  success_tasks: number;
  success_rate: number;
  tasks_by_type: Record<string, number>;
  daily_trend: Array<{ date: string; total: number; success: number }>;
}

const LogsPage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [statusSummary, setStatusSummary] = useState<StatusSummary>({
    queued: 0,
    running: 0,
    completed: 0,
    failed: 0
  });
  const [stats, setStats] = useState<LogStats | null>(null);

  // 筛选条件
  const [activeTab, setActiveTab] = useState('all');
  const [taskType, setTaskType] = useState<string | undefined>(undefined);
  const [keyword, setKeyword] = useState('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // 详情抽屉
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  // 加载任务列表
  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        skip: (page - 1) * pageSize,
        limit: pageSize
      };

      if (activeTab !== 'all') {
        params.status = activeTab;
      }
      if (taskType) {
        params.task_type = taskType;
      }
      if (keyword) {
        params.keyword = keyword;
      }
      if (dateRange) {
        params.date_from = dateRange[0].format('YYYY-MM-DD');
        params.date_to = dateRange[1].format('YYYY-MM-DD');
      }

      const response = await api.get('/admin/tasks', { params });
      setTasks(response.data.tasks);
      setTotal(response.data.total);
      setStatusSummary(response.data.status_summary);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载任务列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, activeTab, taskType, keyword, dateRange]);

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const response = await api.get('/admin/logs/stats', { params: { period: 'week' } });
      setStats(response.data);
    } catch (error) {
      console.error('加载统计数据失败:', error);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleViewDetail = (taskId: string) => {
    setSelectedTaskId(taskId);
    setDrawerVisible(true);
  };

  const handleCloseDrawer = () => {
    setDrawerVisible(false);
    setSelectedTaskId(null);
  };

  const handleSearch = () => {
    setPage(1);
    loadTasks();
  };

  // 状态标签颜色
  const getStatusTag = (status: string) => {
    const config: Record<string, { color: string; text: string }> = {
      queued: { color: 'default', text: '排队中' },
      running: { color: 'processing', text: '运行中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' }
    };
    const { color, text } = config[status] || { color: 'default', text: status };
    return <Tag color={color}>{text}</Tag>;
  };

  // 任务类型标签
  const getTaskTypeTag = (type: string) => {
    const config: Record<string, { color: string; text: string }> = {
      breakdown: { color: 'blue', text: '剧情拆解' },
      script: { color: 'purple', text: '剧本生成' },
      consistency_check: { color: 'cyan', text: '一致性检查' }
    };
    const { color, text } = config[type] || { color: 'default', text: type };
    return <Tag color={color}>{text}</Tag>;
  };

  // 格式化时间
  const formatTime = (timeStr: string | null) => {
    if (!timeStr) return '-';
    return dayjs(timeStr).format('MM-DD HH:mm:ss');
  };

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id: string) => (
        <Tooltip title={id}>
          <span className="font-mono text-xs">{id.slice(0, 8)}...</span>
        </Tooltip>
      )
    },
    {
      title: '类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 110,
      render: (type: string) => getTaskTypeTag(type)
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 80,
      render: (progress: number) => (
        <span className="font-mono">{progress}%</span>
      )
    },
    {
      title: '当前步骤',
      dataIndex: 'current_step',
      key: 'current_step',
      ellipsis: true,
      render: (step: string | null) => step || '-'
    },
    {
      title: '项目',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 150,
      ellipsis: true,
      render: (name: string | null) => name || '-'
    },
    {
      title: '重试',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 60,
      render: (count: number) => count > 0 ? <Tag color="orange">{count}</Tag> : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      render: (time: string | null) => formatTime(time)
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: Task) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record.id)}
        >
          详情
        </Button>
      )
    }
  ];

  const tabItems = [
    { key: 'all', label: `全部 (${total})` },
    { key: 'running', label: `运行中 (${statusSummary.running})` },
    { key: 'completed', label: `已完成 (${statusSummary.completed})` },
    { key: 'failed', label: `失败 (${statusSummary.failed})` },
    { key: 'queued', label: `排队中 (${statusSummary.queued})` }
  ];

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">本周任务总数</div>
            <div className="text-2xl font-bold text-slate-100">{stats.total_tasks}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">成功率</div>
            <div className="text-2xl font-bold text-green-400">{stats.success_rate}%</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">运行中</div>
            <div className="text-2xl font-bold text-cyan-400">{statusSummary.running}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">失败任务</div>
            <div className="text-2xl font-bold text-red-400">{statusSummary.failed}</div>
          </GlassCard>
        </div>
      )}

      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-slate-100">任务日志</h1>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { loadTasks(); loadStats(); }}
          >
            刷新
          </Button>
        </div>

        {/* 筛选器 */}
        <div className="mb-4 flex gap-4 flex-wrap">
          <GlassInput
            placeholder="搜索步骤或错误信息"
            allowClear
            style={{ width: 220 }}
            prefix={<SearchOutlined className="text-slate-500" />}
            onPressEnter={handleSearch}
            onChange={(e) => setKeyword(e.target.value)}
          />
          <GlassSelect
            placeholder="任务类型"
            allowClear
            style={{ width: 140 }}
            onChange={setTaskType}
            options={[
              { value: 'breakdown', label: '剧情拆解' },
              { value: 'script', label: '剧本生成' },
              { value: 'consistency_check', label: '一致性检查' }
            ]}
          />
          <RangePicker
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            className="bg-slate-800/50 border-slate-700"
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
            搜索
          </Button>
        </div>

        {/* 标签页 */}
        <GlassTabs
          activeKey={activeTab}
          onChange={(key) => { setActiveTab(key); setPage(1); }}
          items={tabItems}
        />

        {/* 任务列表 */}
        <GlassTable
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条记录`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); }
          }}
        />
      </GlassCard>

      {/* 详情抽屉 */}
      <TaskDetailDrawer
        visible={drawerVisible}
        taskId={selectedTaskId}
        onClose={handleCloseDrawer}
      />
    </div>
  );
};

export default LogsPage;
