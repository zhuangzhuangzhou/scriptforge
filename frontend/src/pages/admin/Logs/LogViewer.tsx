import React, { useState, useEffect, useRef } from 'react';
import { Spin, Empty, Tag } from 'antd';
import { Terminal, Zap, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react';
import dayjs from 'dayjs';
import api from '../../../services/api';

interface LogDetail {
  status?: string;
  score?: number;
  validator_name?: string;
  error?: string;
}

interface LogEntry {
  id: string;
  stage: string;
  event: string;
  message: string;
  detail: LogDetail | null;
  created_at: string | null;
}

interface LogViewerProps {
  taskId: string;
}

const LogViewer: React.FC<LogViewerProps> = ({ taskId }) => {
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadLogs();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/admin/tasks/${taskId}/logs`, {
        params: { limit: 500 }
      });
      setLogs(response.data.logs);
      setTotal(response.data.total);
    } catch (error) {
      console.error('加载日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取事件图标
  const getEventIcon = (event: string) => {
    switch (event) {
      case 'stage_start':
      case 'step_start':
        return <Info size={14} className="text-cyan-400" />;
      case 'stage_completed':
      case 'step_completed':
        return <CheckCircle size={14} className="text-green-400" />;
      case 'stage_failed':
      case 'step_failed':
      case 'error':
        return <XCircle size={14} className="text-red-400" />;
      case 'validator_result':
      case 'llm_call':
        return <Zap size={14} className="text-purple-400" />;
      case 'warning':
        return <AlertTriangle size={14} className="text-amber-400" />;
      default:
        return <Terminal size={14} className="text-slate-400" />;
    }
  };

  // 获取事件样式
  const getEventStyle = (event: string) => {
    switch (event) {
      case 'stage_start':
      case 'step_start':
        return 'text-cyan-300';
      case 'stage_completed':
      case 'step_completed':
        return 'text-green-300';
      case 'stage_failed':
      case 'step_failed':
      case 'error':
        return 'text-red-300';
      case 'validator_result':
      case 'llm_call':
        return 'text-purple-300';
      case 'warning':
        return 'text-amber-300';
      default:
        return 'text-slate-300';
    }
  };

  // 格式化时间
  const formatTime = (timeStr: string | null) => {
    if (!timeStr) return '--:--:--';
    return dayjs(timeStr).format('HH:mm:ss');
  };

  // 阶段标签颜色
  const getStageColor = (stage: string) => {
    const colors: Record<string, string> = {
      breakdown: 'blue',
      script: 'purple',
      qa: 'green',
      consistency: 'cyan',
      init: 'default',
      cleanup: 'default'
    };
    return colors[stage] || 'default';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-60">
        <Spin tip="加载日志中..." />
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <Empty
        description="暂无执行日志"
        className="py-10"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <div className="log-viewer">
      {/* 日志统计 */}
      <div className="mb-3 flex items-center gap-4 text-sm">
        <span className="text-slate-400">
          共 <span className="text-cyan-400 font-mono">{total}</span> 条日志
        </span>
      </div>

      {/* 日志列表 */}
      <div
        ref={scrollRef}
        className="bg-slate-950 border border-slate-800 rounded-lg p-3 max-h-[500px] overflow-y-auto font-mono text-xs space-y-1"
      >
        {logs.map((log) => (
          <div
            key={log.id}
            className="flex items-start gap-2 py-1 hover:bg-slate-900/50 rounded px-1 transition-colors"
          >
            {/* 时间戳 */}
            <span className="text-slate-600 shrink-0 select-none">
              [{formatTime(log.created_at)}]
            </span>

            {/* 阶段标签 */}
            {log.stage && (
              <Tag
                color={getStageColor(log.stage)}
                className="shrink-0 text-[10px] leading-tight"
                style={{ margin: 0, padding: '0 4px' }}
              >
                {log.stage}
              </Tag>
            )}

            {/* 事件图标 */}
            <span className="shrink-0 mt-0.5">
              {getEventIcon(log.event)}
            </span>

            {/* 消息内容 */}
            <div className="flex-1 min-w-0">
              <span className={`break-words ${getEventStyle(log.event)}`}>
                {log.message}
              </span>

              {/* 详情展示 */}
              {log.detail && (
                <div className="mt-1 pl-2 border-l-2 border-slate-700">
                  {log.detail.status && (
                    <span className={`mr-2 ${
                      log.detail.status === 'passed' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {log.detail.status}
                    </span>
                  )}
                  {log.detail.score !== undefined && (
                    <span className="text-cyan-400 mr-2">
                      Score: {log.detail.score}
                    </span>
                  )}
                  {log.detail.validator_name && (
                    <span className="text-slate-500">
                      ({log.detail.validator_name})
                    </span>
                  )}
                  {log.detail.error && (
                    <div className="text-red-400 mt-1 whitespace-pre-wrap">
                      {log.detail.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LogViewer;
