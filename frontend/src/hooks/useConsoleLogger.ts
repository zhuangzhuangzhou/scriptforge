import { useState, useCallback, useEffect, useRef } from 'react';
import { breakdownApi } from '../services/api';

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'thinking' | 'llm_call' | 'stream';
  message: string;
  detail?: any;
}

export interface LLMCallStats {
  total: number;
  stages: Array<{
    stage: string;
    validator: string;
    status: string;
    score?: number;
    timestamp?: string;
  }>;
}

interface UseConsoleLoggerOptions {
  enableWebSocket?: boolean;
  pollInterval?: number;
}

export const useConsoleLogger = (
  taskId: string | null,
  options: UseConsoleLoggerOptions = {}
) => {
  const { enableWebSocket = true, pollInterval = 2000 } = options;

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [llmStats, setLlmStats] = useState<LLMCallStats>({ total: 0, stages: [] });
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const queuedTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const taskStartTimeRef = useRef<number | null>(null);

  // 添加日志
  const addLog = useCallback((
    type: LogEntry['type'],
    message: string,
    detail?: any
  ) => {
    const newLog: LogEntry = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date().toLocaleTimeString(),
      type,
      message,
      detail
    };
    setLogs(prev => [...prev, newLog]);
  }, []);

  // 更新最后一个流式日志（用于累积流式内容）
  const updateStreamLog = useCallback((message: string) => {
    setLogs(prev => {
      // 查找最后一个 stream 类型的日志
      const lastIndex = prev.length - 1;

      if (lastIndex >= 0 && prev[lastIndex].type === 'stream') {
        // 更新最后一个流式日志
        const updated = [...prev];
        updated[lastIndex] = {
          ...updated[lastIndex],
          message
        };
        return updated;
      } else {
        // 如果没有流式日志，创建一个新的
        return [...prev, {
          id: `stream-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          type: 'stream',
          message
        }];
      }
    });
  }, []);

  // 清空日志
  const clearLogs = useCallback(() => {
    setLogs([]);
    setLlmStats({ total: 0, stages: [] });
  }, []);

  // 获取 LLM 调用日志
  const fetchLLMCallLogs = useCallback(async () => {
    if (!taskId) return;

    try {
      const res = await breakdownApi.getTaskLogs(taskId);
      const data = res.data;

      // 更新 LLM 统计
      setLlmStats(data.llm_calls);

      // 添加 LLM 调用日志到控制台
      if (data.execution_logs && Array.isArray(data.execution_logs)) {
        data.execution_logs.forEach((log: any) => {
          if (log.event === 'validator_result' && log.detail) {
            addLog(
              'llm_call',
              `LLM 调用: ${log.stage} - ${log.detail?.validator_name || '未知验证器'}`,
              log.detail
            );
          }
        });
      }
    } catch (error) {
      console.error('获取 LLM 日志失败:', error);
    }
  }, [taskId, addLog]);

  // WebSocket 连接
  useEffect(() => {
    if (!taskId || !enableWebSocket) return;

    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/ws/breakdown/${taskId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        addLog('info', `已连接到任务 ${taskId.slice(0, 8)}...`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // 处理进度更新
          if (data.current_step) {
            addLog('thinking', data.current_step);
          }

          // 处理任务完成
          if (data.status === 'completed') {
            addLog('success', '任务完成');
            // 获取 LLM 调用日志
            setTimeout(() => {
              fetchLLMCallLogs();
            }, 1000);
          }

          // 处理任务失败
          if (data.status === 'failed') {
            addLog('error', data.error_message || '任务失败');
          }

          // 处理最终状态
          if (data.final_status) {
            ws.close();
          }
        } catch (error) {
          console.error('解析 WebSocket 消息失败:', error);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
        addLog('warning', 'WebSocket 连接失败，切换到轮询模式');
      };

      ws.onclose = () => {
        setIsConnected(false);
      };

      return () => {
        ws.close();
      };
    } catch (error) {
      console.error('WebSocket 连接错误:', error);
      addLog('warning', 'WebSocket 不可用，使用轮询模式');
    }
  }, [taskId, enableWebSocket, addLog, fetchLLMCallLogs]);

  // 轮询模式（WebSocket 失败时的降级方案）
  useEffect(() => {
    if (!taskId || isConnected) return;

    const pollStatus = async () => {
      try {
        const res = await breakdownApi.getTaskStatus(taskId);
        const data = res.data;

        // 检测 queued 状态超时
        if (data.status === 'queued') {
          if (!taskStartTimeRef.current) {
            taskStartTimeRef.current = Date.now();
          } else {
            const elapsedTime = Date.now() - taskStartTimeRef.current;
            // 超过 30 秒仍在 queued 状态，显示警告
            if (elapsedTime > 30000 && !queuedTimeoutRef.current) {
              queuedTimeoutRef.current = setTimeout(() => {
                addLog('warning', '⚠️ 任务长时间处于排队状态');
                addLog('error', '可能原因：Celery Worker 未运行');
                addLog('info', '解决方案：请启动 Celery Worker 服务');
              }, 0);
            }
          }
        } else {
          // 状态改变，清除超时检测
          taskStartTimeRef.current = null;
          if (queuedTimeoutRef.current) {
            clearTimeout(queuedTimeoutRef.current);
            queuedTimeoutRef.current = null;
          }
        }

        // 更新进度
        if (data.current_step) {
          addLog('thinking', data.current_step);
        }

        // 任务完成
        if (data.status === 'completed') {
          addLog('success', '任务完成');
          fetchLLMCallLogs();
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
          }
        }

        // 任务失败
        if (data.status === 'failed') {
          addLog('error', data.error_message || '任务失败');
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
          }
        }
      } catch (error) {
        console.error('轮询任务状态失败:', error);
      }
    };

    // 立即执行一次
    pollStatus();

    // 设置定时轮询
    pollTimerRef.current = setInterval(pollStatus, pollInterval);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [taskId, isConnected, pollInterval, addLog, fetchLLMCallLogs]);

  return {
    logs,
    llmStats,
    isConnected,
    addLog,
    updateStreamLog,
    clearLogs,
    fetchLLMCallLogs
  };
};
