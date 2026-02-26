import { useState, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { TASK_STATUS } from '../constants/status';

interface BreakdownProgress {
  task_id: string;
  status: string;
  progress: number;
  current_step: string;
  error_message?: string;
  retry_count?: number;
}

interface StreamMessage {
  type: 'connected' | 'step_start' | 'stream_chunk' | 'formatted_chunk' | 'step_end' | 'error' | 'progress' | 'task_complete' | 'task_failed' | 'info' | 'warning' | 'success' | 'qa_check' | 'round_info' | 'batch_switch';
  task_id: string;
  step_name?: string;
  content?: string;
  timestamp?: string;
  metadata?: {
    progress?: number;
    current_step?: number;
    total_steps?: number;
    current_round?: number;
    total_rounds?: number;
    final?: boolean;
    error_code?: string;
    new_task_id?: string;
    new_batch_id?: string;
    new_batch_number?: number;
    auto_switch?: boolean;
    [key: string]: any;
  };
  status?: string;
  message?: string;
}

interface UseBreakdownWebSocketOptions {
  // 原有回调
  onProgress?: (progress: BreakdownProgress) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
  fallbackToPolling?: boolean;
  // 扩展回调（来自 useBreakdownLogs）
  onStepStart?: (stepName: string, metadata?: any) => void;
  onStreamChunk?: (stepName: string, chunk: string) => void;
  onFormattedChunk?: (stepName: string, chunk: string) => void;
  onStepEnd?: (stepName: string, result?: any) => void;
  onRoundInfo?: (currentRound: number, totalRounds: number) => void;
  onWarning?: (warning: string) => void;
  onInfo?: (info: string) => void;
  onSuccess?: (message: string) => void;
  onBatchSwitch?: (info: {
    newTaskId: string;
    newBatchId: string;
    newBatchNumber: number;
  }) => void;
  onClose?: () => void;
}

/**
 * Breakdown 任务 WebSocket Hook (扩展版)
 *
 * 功能：
 * - 实时接收任务进度
 * - 实时接收大模型返回的流式数据
 * - 支持步骤开始、流式内容、步骤结束等消息类型
 * - 支持轮次信息（round_info）
 * - 支持批次切换（batch_switch）
 * - 自动处理完成/失败状态
 * - 支持降级到轮询
 */
export const useBreakdownWebSocket = (
  taskId: string | null,
  options: UseBreakdownWebSocketOptions = {}
) => {
  const {
    onProgress,
    onComplete,
    onError,
    fallbackToPolling = true,
    onStepStart,
    onStreamChunk,
    onFormattedChunk,
    onStepEnd,
    onRoundInfo,
    onWarning,
    onInfo,
    onSuccess,
    onBatchSwitch,
    onClose
  } = options;

  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [status, setStatus] = useState<string>('');
  const [usePolling, setUsePolling] = useState(false);
  const [currentRound, setCurrentRound] = useState(0);
  const [totalRounds, setTotalRounds] = useState(0);

  // 构建 WebSocket URL（统一使用 /ws/breakdown）
  const wsUrl = taskId ? `/api/v1/ws/breakdown/${taskId}` : null;

  // 处理来自 logs 频道的消息
  const handleLogMessage = useCallback((data: StreamMessage) => {
    console.log('[useBreakdownWebSocket] 收到日志消息:', data.type, data);

    switch (data.type) {
      case 'connected':
        console.log('[useBreakdownWebSocket] 已连接到日志流');
        break;

      case 'step_start':
        if (data.step_name) {
          setCurrentStep(data.step_name);
          onStepStart?.(data.step_name, data.metadata);
        }
        break;

      case 'stream_chunk':
        if (data.content) {
          onStreamChunk?.(data.step_name || '', data.content);
        }
        break;

      case 'formatted_chunk':
        if (data.content) {
          onFormattedChunk?.(data.step_name || '', data.content);
        }
        break;

      case 'step_end':
        if (data.step_name) {
          onStepEnd?.(data.step_name, data.metadata);
        }
        break;

      case 'progress':
        if (data.metadata) {
          const { progress: p, current_step, total_steps } = data.metadata;
          if (p !== undefined) {
            setProgress(p);
          }
          // 同时触发原有的 onProgress 回调
          if (current_step !== undefined && total_steps !== undefined && taskId) {
            const progressData: BreakdownProgress = {
              task_id: taskId,
              status: 'in_progress',
              progress: p || 0,
              current_step: `Step ${current_step}/${total_steps}`
            };
            onProgress?.(progressData);
          }
        }
        break;

      case 'round_info':
        if (data.metadata) {
          const { current_round: cr, total_rounds: tr } = data.metadata;
          if (cr !== undefined) {
            setCurrentRound(cr);
          }
          if (tr !== undefined) {
            setTotalRounds(tr);
          }
          if (cr !== undefined && tr !== undefined) {
            onRoundInfo?.(cr, tr);
          }
        }
        break;

      case 'error': {
        const errorMsg = data.content || '任务执行出错';
        // 优先使用原有的 onError 回调格式
        onError?.(errorMsg);
        break;
      }

      case 'warning':
        if (data.content) {
          onWarning?.(data.content);
        }
        break;

      case 'info':
        if (data.content) {
          onInfo?.(data.content);
        }
        break;

      case 'success':
        if (data.content) {
          onSuccess?.(data.content);
        }
        break;

      case 'qa_check':
        if (data.content) {
          onInfo?.(data.content);
        }
        break;

      case 'task_complete':
        console.log('[useBreakdownWebSocket] 任务完成');
        setCurrentStep('');
        setProgress(100);
        onComplete?.();
        break;

      case 'task_failed':
        console.log('[useBreakdownWebSocket] 任务失败');
        setCurrentStep('');
        setProgress(0);
        onError?.(data.message || '任务执行失败');
        break;

      case 'batch_switch':
        console.log('[useBreakdownWebSocket] 收到批次切换消息:', data.metadata);
        if (data.metadata?.new_task_id && data.metadata?.new_batch_id && data.metadata?.new_batch_number) {
          onBatchSwitch?.({
            newTaskId: data.metadata.new_task_id,
            newBatchId: data.metadata.new_batch_id,
            newBatchNumber: data.metadata.new_batch_number
          });
          onInfo?.(`批次 ${data.metadata.new_batch_number} 已开始拆解，正在切换...`);
        }
        break;

      default:
        console.log('[useBreakdownWebSocket] 未知消息类型:', data);
    }
  }, [onStepStart, onStreamChunk, onFormattedChunk, onStepEnd, onRoundInfo, onError, onWarning, onInfo, onSuccess, onComplete, onBatchSwitch, onProgress, taskId]);

  const { isConnected, lastMessage } = useWebSocket(wsUrl, {
    onMessage: (data) => {
      const message = data as any;

      // 判断消息类型：progress 频道发送的是 BreakdownProgress 格式，logs 频道发送的是 StreamMessage 格式
      // 通过 type 字段区分
      if (message.type) {
        // 日志频道消息
        handleLogMessage(message as StreamMessage);
        return;
      }

      // 处理任务进度消息（来自 progress 频道）
      console.log('[useBreakdownWebSocket] 收到进度消息:', message);

      if (message.task_id) {
        const progressData: BreakdownProgress = {
          task_id: message.task_id,
          status: message.status || '',
          progress: message.progress || 0,
          current_step: message.current_step || '',
          error_message: message.error_message,
          retry_count: 0
        };

        console.log('[useBreakdownWebSocket] 更新进度:', {
          progress: progressData.progress,
          currentStep: progressData.current_step,
          status: progressData.status
        });

        setProgress(progressData.progress);
        setCurrentStep(progressData.current_step);
        setStatus(progressData.status);

        onProgress?.(progressData);

        // 任务完成
        if (message.status === TASK_STATUS.COMPLETED) {
          onComplete?.();
        }

        // 任务失败
        if (message.status === TASK_STATUS.FAILED) {
          let errorMsg = '任务执行失败，请稍后重试';
          let errorSuggestion = '';
          if (message.error_message) {
            try {
              const errorData = typeof message.error_message === 'string' ? JSON.parse(message.error_message) : message.error_message;
              errorMsg = errorData.message || errorData.description || message.error_message;
              errorSuggestion = errorData.suggestion || '';
            } catch {
              errorMsg = message.error_message;
            }
          }
          if (errorSuggestion) {
            errorMsg = `${errorMsg}\n\n💡 建议: ${errorSuggestion}`;
          }
          onError?.(errorMsg);
        }
      }

      // 处理最终状态消息
      if (message.status === 'done') {
        if (message.final_status === TASK_STATUS.COMPLETED) {
          onComplete?.();
        } else if (message.final_status === TASK_STATUS.FAILED) {
          onError?.(message.message || '任务失败');
        }
      }

      // 处理错误消息
      if (message.error) {
        console.error('[WebSocket] 错误:', message.error);
        if (fallbackToPolling && (
          message.code === 'TASK_NOT_FOUND' ||
          message.code === 'CONNECTION_TIMEOUT' ||
          message.code === 'INTERNAL_ERROR'
        )) {
          console.log(`[WebSocket] 错误 (${message.code})，降级到轮询模式`);
          setUsePolling(true);
        }
      }
    },
    onError: (error) => {
      console.error('[WebSocket] 连接错误:', error);
      if (fallbackToPolling) {
        console.log('[WebSocket] 连接失败，降级到轮询模式');
        setUsePolling(true);
      }
    },
    onClose: () => {
      console.log('[WebSocket] 连接关闭');
      if (fallbackToPolling && !isConnected) {
        console.log('[WebSocket] 连接异常关闭，降级到轮询模式');
        setUsePolling(true);
      }
      onClose?.();
    },
    reconnect: true,
    reconnectInterval: 3000,
    maxReconnectAttempts: 3
  });

  return {
    isConnected,
    progress,
    currentStep,
    status,
    usePolling,
    currentRound,
    totalRounds,
    lastMessage
  };
};
