import React, { useState, useEffect } from 'react';
import { Descriptions, Tag, Spin, message, Tabs } from 'antd';
import dayjs from 'dayjs';
import api from '../../../services/api';
import LogViewer from './LogViewer';
import { GlassModal } from '../../../components/ui/GlassModal';

interface TaskDetail {
  id: string;
  task_type: string;
  status: string;
  progress: number;
  current_step: string | null;
  error_message: string | null;
  retry_count: number;
  config: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  depends_on: string[] | null;
  project_id: string | null;
  project_name: string | null;
  batch_id: string | null;
  batch_name: string | null;
  celery_task_id: string | null;
  duration: number | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

interface TaskDetailModalProps {
  open: boolean;
  taskId: string | null;
  onClose: () => void;
}

const TaskDetailModal: React.FC<TaskDetailModalProps> = ({
  open,
  taskId,
  onClose
}) => {
  const [loading, setLoading] = useState(false);
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [activeTab, setActiveTab] = useState('info');

  useEffect(() => {
    if (open && taskId) {
      loadTaskDetail();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, taskId]);

  const loadTaskDetail = async () => {
    if (!taskId) return;

    setLoading(true);
    try {
      const response = await api.get(`/admin/tasks/${taskId}`);
      setTask(response.data);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载任务详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 状态标签
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
    return dayjs(timeStr).format('YYYY-MM-DD HH:mm:ss');
  };

  // 格式化时长
  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return '-';
    if (seconds < 60) return `${seconds.toFixed(1)} 秒`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)} 分钟`;
    return `${(seconds / 3600).toFixed(1)} 小时`;
  };

  const tabItems = [
    {
      key: 'info',
      label: '基本信息',
      children: task ? (
        <div className="space-y-4">
          <Descriptions column={2} size="small" className="task-descriptions">
            <Descriptions.Item label="任务ID">
              <span className="font-mono text-xs">{task.id}</span>
            </Descriptions.Item>
            <Descriptions.Item label="任务类型">
              {getTaskTypeTag(task.task_type)}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {getStatusTag(task.status)}
            </Descriptions.Item>
            <Descriptions.Item label="进度">
              <span className="font-mono">{task.progress}%</span>
            </Descriptions.Item>
            <Descriptions.Item label="项目">
              {task.project_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="批次">
              {task.batch_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="重试次数">
              {task.retry_count > 0 ? (
                <Tag color="orange">{task.retry_count}</Tag>
              ) : '0'}
            </Descriptions.Item>
            <Descriptions.Item label="执行时长">
              {formatDuration(task.duration)}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {formatTime(task.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间" span={2}>
              {formatTime(task.started_at)}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间" span={2}>
              {formatTime(task.completed_at)}
            </Descriptions.Item>
            {task.current_step && (
              <Descriptions.Item label="当前步骤" span={2}>
                {task.current_step}
              </Descriptions.Item>
            )}
            {task.celery_task_id && (
              <Descriptions.Item label="Celery Task ID" span={2}>
                <span className="font-mono text-xs">{task.celery_task_id}</span>
              </Descriptions.Item>
            )}
          </Descriptions>

          {/* 错误信息 */}
          {task.error_message && (
            <div className="mt-4">
              <div className="text-sm text-slate-400 mb-2">错误信息</div>
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <pre className="text-red-400 text-sm whitespace-pre-wrap font-mono">
                  {task.error_message}
                </pre>
              </div>
            </div>
          )}

          {/* 配置信息 */}
          {task.config && Object.keys(task.config).length > 0 && (
            <div className="mt-4">
              <div className="text-sm text-slate-400 mb-2">任务配置</div>
              <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono">
                  {JSON.stringify(task.config, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* 执行结果 */}
          {task.result && Object.keys(task.result).length > 0 && (
            <div className="mt-4">
              <div className="text-sm text-slate-400 mb-2">执行结果</div>
              <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg max-h-60 overflow-y-auto">
                <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono">
                  {JSON.stringify(task.result, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      ) : null
    },
    {
      key: 'logs',
      label: '执行日志',
      children: taskId ? <LogViewer taskId={taskId} /> : null
    }
  ];

  return (
    <GlassModal
      title="任务详情"
      open={open}
      onCancel={onClose}
      width={700}
      footer={null}
    >
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Spin tip="加载中..." />
        </div>
      ) : task ? (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          className="task-detail-tabs"
        />
      ) : (
        <div className="text-slate-500 text-center py-10">
          未找到任务信息
        </div>
      )}
    </GlassModal>
  );
};

export default TaskDetailModal;
