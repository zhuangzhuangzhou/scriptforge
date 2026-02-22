import React, { useState, useEffect, useCallback } from 'react';
import { Button, Tag, message, Modal, Progress, Tooltip, Space, Select, Card, Typography, Table, Checkbox } from 'antd';
import { ReloadOutlined, StopOutlined, DeleteOutlined, ExclamationCircleOutlined, PlayCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { adminApi } from '../../../services/api';

const { Text, Title } = Typography;

interface RunningTask {
  id: string;
  task_type: string;
  status: string;
  progress: number;
  current_step: string;
  user_id: string;
  username: string;
  project_id: string;
  project_name: string;
  batch_id: string;
  batch_number: number;
  created_at: string;
  updated_at: string;
  running_time: number;
  idle_time: number;
  reason?: string;
}

const TaskManagement: React.FC = () => {
  const [tasks, setTasks] = useState<RunningTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5);

  // 卡住任务 Modal 状态
  const [stuckTasksModalVisible, setStuckTasksModalVisible] = useState(false);
  const [stuckTasks, setStuckTasks] = useState<RunningTask[]>([]);
  const [selectedStuckTaskIds, setSelectedStuckTaskIds] = useState<string[]>([]);
  const [loadingStuckTasks, setLoadingStuckTasks] = useState(false);
  const [terminatingTasks, setTerminatingTasks] = useState(false);

  // 加载正在运行的任务
  const loadRunningTasks = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminApi.getRunningTasks();
      setTasks(response.data.tasks || []);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载任务失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRunningTasks();
  }, [loadRunningTasks]);

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadRunningTasks();
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, loadRunningTasks]);

  // 停止任务
  const handleStopTask = (task: RunningTask) => {
    Modal.confirm({
      title: '确认停止任务',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div className="py-2">
          <div className="mb-3">确定要停止以下任务吗？</div>
          <div className="text-slate-400 text-sm space-y-1">
            <div><span className="text-slate-500">任务ID：</span>{task.id.slice(0, 8)}...</div>
            <div><span className="text-slate-500">用户：</span>{task.username}</div>
            <div><span className="text-slate-500">项目：</span>{task.project_name}</div>
            <div><span className="text-slate-500">批次：</span>第 {task.batch_number} 批</div>
            <div><span className="text-slate-500">进度：</span>{task.progress}%</div>
          </div>
          <div className="mt-3 text-amber-500 text-sm">
            ⚠️ 停止任务后，已消耗的积分不会退还
          </div>
        </div>
      ),
      okText: '确认停止',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await adminApi.stopTask(task.id);
          message.success('任务已停止');
          loadRunningTasks();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '停止任务失败');
        }
      },
    });
  };

  // 检查并终止卡住的任务
  const handleCheckStuckTasks = async () => {
    setLoadingStuckTasks(true);
    try {
      const response = await adminApi.getStuckTasks();
      const stuckTasksList = response.data.tasks || [];

      if (stuckTasksList.length === 0) {
        message.info('未发现卡住的任务');
        return;
      }

      setStuckTasks(stuckTasksList);
      setSelectedStuckTaskIds([]);
      setStuckTasksModalVisible(true);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '查询卡住任务失败');
    } finally {
      setLoadingStuckTasks(false);
    }
  };

  // 批量终止选中的卡住任务
  const handleTerminateSelectedTasks = async () => {
    if (selectedStuckTaskIds.length === 0) {
      message.warning('请至少选择一个任务');
      return;
    }

    Modal.confirm({
      title: '确认终止任务',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div className="py-2">
          <div className="mb-3">确定要终止选中的 {selectedStuckTaskIds.length} 个任务吗？</div>
          <div className="mt-3 text-amber-500 text-sm">
            ⚠️ 停止任务后，已消耗的积分不会退还
          </div>
        </div>
      ),
      okText: '确认终止',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setTerminatingTasks(true);
        let successCount = 0;
        let failCount = 0;

        for (const taskId of selectedStuckTaskIds) {
          try {
            await adminApi.stopTask(taskId);
            successCount++;
          } catch (error) {
            failCount++;
          }
        }

        setTerminatingTasks(false);

        if (successCount > 0) {
          message.success(`成功终止 ${successCount} 个任务${failCount > 0 ? `，${failCount} 个失败` : ''}`);
        } else {
          message.error('终止任务失败');
        }

        // 关闭 Modal 并刷新任务列表
        setStuckTasksModalVisible(false);
        setSelectedStuckTaskIds([]);
        loadRunningTasks();
      },
    });
  };

  // 格式化时间
  const formatTime = (timeStr: string) => {
    return dayjs(timeStr).format('MM-DD HH:mm:ss');
  };

  // 格式化运行时间
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}小时${minutes}分`;
    } else if (minutes > 0) {
      return `${minutes}分${secs}秒`;
    } else {
      return `${secs}秒`;
    }
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      running: { color: 'processing', text: '运行中' },
      processing: { color: 'processing', text: '处理中' },
      queued: { color: 'default', text: '排队中' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 获取运行时间颜色
  const getRunningTimeColor = (seconds: number) => {
    if (seconds > 3600) return { color: '#ef4444', text: 'text-red-500' };
    if (seconds > 1800) return { color: '#f59e0b', text: 'text-amber-500' };
    return { color: '#22c55e', text: 'text-green-500' };
  };

  // 获取停滞时间颜色
  const getIdleTimeColor = (seconds: number) => {
    if (seconds > 1800) return { color: '#ef4444', text: 'text-red-500' };
    if (seconds > 600) return { color: '#f59e0b', text: 'text-amber-500' };
    return { color: '#64748b', text: 'text-slate-500' };
  };

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => (
        <Tooltip title={id}>
          <span className="font-mono text-xs">{id.slice(0, 8)}...</span>
        </Tooltip>
      ),
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 100,
    },
    {
      title: '项目',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '批次',
      dataIndex: 'batch_number',
      key: 'batch_number',
      width: 80,
      render: (num: number) => <span className="font-mono">#{num}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 180,
      render: (progress: number, record: RunningTask) => (
        <div className="space-y-1">
          <Progress
            percent={progress}
            size="small"
            status={progress < 100 ? 'active' : 'success'}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          <div className="text-xs text-slate-500 truncate" title={record.current_step}>
            {record.current_step || '-'}
          </div>
        </div>
      ),
    },
    {
      title: '运行时间',
      dataIndex: 'running_time',
      key: 'running_time',
      width: 100,
      render: (time: number) => {
        const style = getRunningTimeColor(time);
        return (
          <span className={`font-mono text-xs ${style.text}`}>
            {formatDuration(time)}
          </span>
        );
      },
    },
    {
      title: '停滞时间',
      dataIndex: 'idle_time',
      key: 'idle_time',
      width: 100,
      render: (time: number) => {
        const style = getIdleTimeColor(time);
        return (
          <Tooltip title="距离上次更新的时间">
            <span className={`font-mono text-xs ${style.text}`}>
              {formatDuration(time)}
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      render: (time: string) => formatTime(time),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: RunningTask) => (
        <Button
          type="link"
          danger
          size="small"
          icon={<StopOutlined />}
          onClick={() => handleStopTask(record)}
        >
          停止
        </Button>
      ),
    },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto">
      {/* 页面标题 */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <Title level={2} className="text-slate-100 m-0">任务管理</Title>
          <Text className="text-slate-400">
            当前正在运行的任务：{tasks.length} 个
          </Text>
        </div>
        <Space>
          <Select
            value={refreshInterval}
            onChange={setRefreshInterval}
            style={{ width: 100 }}
            options={[
              { value: 3, label: '3秒' },
              { value: 5, label: '5秒' },
              { value: 10, label: '10秒' },
              { value: 30, label: '30秒' },
            ]}
            placeholder="刷新间隔"
          />
          <Button
            type={autoRefresh ? 'primary' : 'default'}
            icon={<PlayCircleOutlined />}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? '自动刷新' : '已暂停'}
          </Button>
          <Button
            icon={<DeleteOutlined />}
            onClick={handleCheckStuckTasks}
          >
            检查卡住任务
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadRunningTasks}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* 任务列表卡片 */}
      <Card
        bordered={false}
        className="bg-slate-800"
        bodyStyle={{ padding: 0 }}
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-900">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key as string}
                    className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider"
                    style={{ width: col.width }}
                  >
                    {col.title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {loading && tasks.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-12 text-center">
                    <ReloadOutlined className="animate-spin text-2xl text-slate-500" />
                  </td>
                </tr>
              ) : tasks.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-12 text-center">
                    <ClockCircleOutlined className="text-4xl text-slate-600 mb-3" />
                    <p className="text-slate-500">当前没有正在运行的任务</p>
                  </td>
                </tr>
              ) : (
                tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <Tooltip title={task.id}>
                        <span className="font-mono text-xs">{task.id.slice(0, 8)}...</span>
                      </Tooltip>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{task.username}</td>
                    <td className="px-4 py-3 text-slate-300 max-w-[150px] truncate" title={task.project_name}>
                      {task.project_name}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-slate-300">#{task.batch_number}</span>
                    </td>
                    <td className="px-4 py-3">
                      {getStatusTag(task.status)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <Progress
                          percent={task.progress}
                          size="small"
                          status={task.progress < 100 ? 'active' : 'success'}
                          strokeColor={{
                            '0%': '#108ee9',
                            '100%': '#87d068',
                          }}
                        />
                        <div className="text-xs text-slate-500 truncate max-w-[160px]" title={task.current_step}>
                          {task.current_step || '-'}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-mono text-xs ${getRunningTimeColor(task.running_time).text}`}>
                        {formatDuration(task.running_time)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Tooltip title="距离上次更新的时间">
                        <span className={`font-mono text-xs ${getIdleTimeColor(task.idle_time).text}`}>
                          {formatDuration(task.idle_time)}
                        </span>
                      </Tooltip>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {formatTime(task.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        type="link"
                        danger
                        size="small"
                        icon={<StopOutlined />}
                        onClick={() => handleStopTask(task)}
                      >
                        停止
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 底部提示 */}
      <div className="mt-4 text-xs text-slate-500 flex items-center gap-4">
        <span>颜色说明：</span>
        <span className="text-green-500">运行时间 &lt; 30分钟</span>
        <span className="text-amber-500">30分钟 - 1小时</span>
        <span className="text-red-500">超过 1小时</span>
      </div>

      {/* 卡住任务 Modal */}
      <Modal
        title="卡住的任务列表"
        open={stuckTasksModalVisible}
        onCancel={() => {
          setStuckTasksModalVisible(false);
          setSelectedStuckTaskIds([]);
        }}
        width={1200}
        footer={[
          <Button key="cancel" onClick={() => {
            setStuckTasksModalVisible(false);
            setSelectedStuckTaskIds([]);
          }}>
            取消
          </Button>,
          <Button
            key="terminate"
            type="primary"
            danger
            loading={terminatingTasks}
            disabled={selectedStuckTaskIds.length === 0}
            onClick={handleTerminateSelectedTasks}
          >
            终止选中任务 ({selectedStuckTaskIds.length})
          </Button>,
        ]}
      >
        <div className="mb-4 text-slate-400 text-sm">
          <div className="mb-2">检查条件：</div>
          <ul className="list-disc list-inside space-y-1">
            <li>创建时间超过 1 小时的任务</li>
            <li>更新时间超过 30 分钟的任务（停滞）</li>
          </ul>
        </div>

        <Table
          dataSource={stuckTasks}
          rowKey="id"
          loading={loadingStuckTasks}
          pagination={false}
          scroll={{ x: 1000 }}
          rowSelection={{
            selectedRowKeys: selectedStuckTaskIds,
            onChange: (selectedKeys) => setSelectedStuckTaskIds(selectedKeys as string[]),
          }}
          columns={[
            {
              title: '任务ID',
              dataIndex: 'id',
              key: 'id',
              width: 100,
              render: (id: string) => (
                <Tooltip title={id}>
                  <span className="font-mono text-xs">{id.slice(0, 8)}...</span>
                </Tooltip>
              ),
            },
            {
              title: '用户',
              dataIndex: 'username',
              key: 'username',
              width: 100,
            },
            {
              title: '项目',
              dataIndex: 'project_name',
              key: 'project_name',
              width: 150,
              ellipsis: true,
            },
            {
              title: '批次',
              dataIndex: 'batch_number',
              key: 'batch_number',
              width: 80,
              render: (num: number) => <span className="font-mono">#{num}</span>,
            },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              width: 100,
              render: (status: string) => getStatusTag(status),
            },
            {
              title: '进度',
              dataIndex: 'progress',
              key: 'progress',
              width: 100,
              render: (progress: number) => (
                <Progress
                  percent={progress}
                  size="small"
                  status={progress < 100 ? 'active' : 'success'}
                />
              ),
            },
            {
              title: '运行时间',
              dataIndex: 'running_time',
              key: 'running_time',
              width: 100,
              render: (time: number) => {
                const style = getRunningTimeColor(time);
                return (
                  <span className={`font-mono text-xs ${style.text}`}>
                    {formatDuration(time)}
                  </span>
                );
              },
            },
            {
              title: '停滞时间',
              dataIndex: 'idle_time',
              key: 'idle_time',
              width: 100,
              render: (time: number) => {
                const style = getIdleTimeColor(time);
                return (
                  <Tooltip title="距离上次更新的时间">
                    <span className={`font-mono text-xs ${style.text}`}>
                      {formatDuration(time)}
                    </span>
                  </Tooltip>
                );
              },
            },
            {
              title: '卡住原因',
              dataIndex: 'reason',
              key: 'reason',
              width: 150,
              render: (reason: string) => (
                <span className="text-amber-500 text-xs">{reason}</span>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  );
};

export default TaskManagement;
