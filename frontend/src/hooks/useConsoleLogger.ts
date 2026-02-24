import { useState, useCallback, useEffect, useRef } from 'react';
import { TASK_STATUS } from '../constants/status';
import { breakdownApi } from '../services/api';

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'thinking' | 'llm_call' | 'stream' | 'formatted';
  message: string;
  detail?: any;
  finalized?: boolean; // 标记流式日志是否已完成
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
  onBatchSwitch?: (info: {
    newTaskId: string;
    newBatchId: string;
    newBatchNumber: number;
  }) => void;
}

export const useConsoleLogger = (
  taskId: string | null,
  options: UseConsoleLoggerOptions = {}
) => {
  const { enableWebSocket = true, pollInterval = 2000 } = options;

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [llmStats, setLlmStats] = useState<LLMCallStats>({ total: 0, stages: [] });
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queuedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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

  // 更新最后一个流式日志（追加模式，用于累积流式内容）
  // 注意：后端发送的是增量内容，所以这里使用追加模式
  const appendStreamLog = useCallback((chunk: string) => {
    setLogs(prev => {
      // 查找最后一个未完成的 stream 类型的日志（不要求在数组末尾）
      let lastStreamIndex = -1;
      for (let i = prev.length - 1; i >= 0; i -= 1) {
        if (prev[i].type === 'stream' && !prev[i].finalized) {
          lastStreamIndex = i;
          break;
        }
      }

      if (lastStreamIndex >= 0) {
        const updated = [...prev];
        updated[lastStreamIndex] = {
          ...updated[lastStreamIndex],
          message: updated[lastStreamIndex].message + chunk  // 追加增量内容
        };
        return updated;
      }

      // 如果没有未完成的流式日志，创建一个新的
      return [...prev, {
        id: `stream-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        type: 'stream',
        message: chunk,
        finalized: false
      }];
    });
  }, []);

  // 更新最后一个流式日志（覆盖模式，已废弃，请使用 appendStreamLog）
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
    setProgress(0);
    setCurrentStep('');
  }, []);

  // 结束当前流式日志（用于步骤结束时，确保下一步骤的内容不会追加到当前日志）
  const finalizeStreamLog = useCallback(() => {
    setLogs(prev => {
      // 标记最后一个未完成的 stream 为已完成
      let lastStreamIndex = -1;
      for (let i = prev.length - 1; i >= 0; i -= 1) {
        if (prev[i].type === 'stream' && !prev[i].finalized) {
          lastStreamIndex = i;
          break;
        }
      }

      if (lastStreamIndex >= 0) {
        const updated = [...prev];
        updated[lastStreamIndex] = {
          ...updated[lastStreamIndex],
          finalized: true
        };
        return updated;
      }
      return prev;
    });
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

          // 处理 logs 频道的消息（包含 content 字段）
          if (data.content) {
            // 根据消息类型显示不同的日志样式
            const messageType = data.type || 'info';
            if (messageType === 'info' || messageType === 'step_start') {
              // 步骤开始时，结束之前的流式日志
              finalizeStreamLog();
              addLog('info', data.content);
            } else if (messageType === 'success') {
              finalizeStreamLog();
              addLog('success', data.content);
            } else if (messageType === 'warning') {
              addLog('warning', data.content);
            } else if (messageType === 'error') {
              finalizeStreamLog();
              addLog('error', data.content);
            } else if (messageType === 'stream_chunk' || messageType === 'formatted_chunk') {
              // 流式内容使用追加模式，累积到同一个日志条目
              appendStreamLog(data.content);
            } else if (messageType === 'round_info') {
              finalizeStreamLog();
              addLog('info', data.content);
            } else if (messageType === 'step_end') {
              // 步骤结束时，结束流式日志
              finalizeStreamLog();
            }
          }

          // 处理 progress 频道的消息（包含 current_step 字段）
          if (data.current_step) {
            setCurrentStep(data.current_step);
            addLog('thinking', data.current_step);
          }

          // 提取进度百分比
          if (typeof data.progress === 'number') {
            setProgress(data.progress);
          }

          // 处理任务完成
          if (data.status === TASK_STATUS.COMPLETED) {
            addLog('success', '任务完成');
            // 获取 LLM 调用日志
            setTimeout(() => {
              fetchLLMCallLogs();
            }, 1000);
          }

          // 处理任务失败
          if (data.status === TASK_STATUS.FAILED) {
            // 传递详细错误信息
            addLog('error', data.error_message || '任务失败', {
              error_message: data.error_message,
              error_display: data.error_display
            });
          }

          // 🔧 修复: 处理批次切换消息
          if (data.type === 'batch_switch') {
            const { new_task_id, new_batch_id, new_batch_number } = data.metadata || {};
            addLog('info', `批次 ${new_batch_number} 已开始拆解，正在切换...`);

            // 触发回调通知父组件
            if (options.onBatchSwitch) {
              options.onBatchSwitch({
                newTaskId: new_task_id,
                newBatchId: new_batch_id,
                newBatchNumber: new_batch_number
              });
            }
            // 不关闭连接,让父组件处理切换
            return;
          }

          // 处理最终状态 - 延迟关闭,等待可能的 batch_switch 消息
          if (data.final_status) {
            setTimeout(() => {
              ws.close();
            }, 2000);  // 延迟 2 秒关闭
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
  }, [taskId, enableWebSocket, addLog, appendStreamLog, finalizeStreamLog, fetchLLMCallLogs]);

  // 轮询模式（WebSocket 失败时的降级方案）
  useEffect(() => {
    if (!taskId || isConnected) return;

    const pollStatus = async () => {
      try {
        const res = await breakdownApi.getTaskStatus(taskId);
        const data = res.data;

        // 检测 queued 状态超时
        if (data.status === TASK_STATUS.QUEUED) {
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
        if (data.status === TASK_STATUS.COMPLETED) {
          addLog('success', '任务完成');
          fetchLLMCallLogs();
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
          }
        }

        // 任务失败
        if (data.status === TASK_STATUS.FAILED) {
          // 优先使用 error_display（人性化错误信息），否则解析 error_message
          let errorMsg = '任务失败';
          if (data.error_display && typeof data.error_display === 'object') {
            errorMsg = data.error_display.description || data.error_display.message || errorMsg;
          } else if (data.error_message) {
            try {
              const errorData = typeof data.error_message === 'string' ? JSON.parse(data.error_message) : data.error_message;
              errorMsg = errorData.message || data.error_message;
            } catch {
              errorMsg = data.error_message;
            }
          }
          addLog('error', errorMsg, {
            error_message: data.error_message,
            error_display: data.error_display
          });
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
    progress,
    currentStep,
    addLog,
    appendStreamLog,
    updateStreamLog,
    clearLogs,
    finalizeStreamLog,
    fetchLLMCallLogs
  };
};
