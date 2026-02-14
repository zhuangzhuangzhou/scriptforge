import { useState } from 'react';
import { useWebSocket } from './useWebSocket';

interface BreakdownProgress {
  task_id: string;
  status: string;
  progress: number;
  current_step: string;
  error_message?: string;
  retry_count?: number;
}

interface BreakdownWebSocketMessage {
  task_id?: string;
  status?: string;
  progress?: number;
  current_step?: string;
  error_message?: string;
  final_status?: string;
  message?: string;
  error?: string;
  code?: string;
}

interface UseBreakdownWebSocketOptions {
  onProgress?: (progress: BreakdownProgress) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
  fallbackToPolling?: boolean;
}

/**
 * Breakdown 任务 WebSocket Hook
 *
 * 功能：
 * - 实时接收任务进度
 * - 自动处理完成/失败状态
 * - 支持降级到轮询
 */
export const useBreakdownWebSocket = (
  taskId: string | null,
  options: UseBreakdownWebSocketOptions = {}
) => {
  const { onProgress, onComplete, onError, fallbackToPolling = true } = options;
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [status, setStatus] = useState<string>('');
  const [usePolling, setUsePolling] = useState(false);

  // 构建 WebSocket URL
  const wsUrl = taskId ? `/api/v1/ws/breakdown/${taskId}` : null;

  const { isConnected, lastMessage } = useWebSocket(wsUrl, {
    onMessage: (data) => {
      const message = data as BreakdownWebSocketMessage;

      console.log('[useBreakdownWebSocket] 收到消息:', message);

      // 处理任务进度消息
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
        if (message.status === 'completed') {
          onComplete?.();
        }

        // 任务失败
        if (message.status === 'failed') {
          // 优先使用 error_display（人性化错误信息），否则解析 error_message
          let errorMsg = '任务失败';
          if (message.error_message) {
            try {
              const errorData = typeof message.error_message === 'string' ? JSON.parse(message.error_message) : message.error_message;
              errorMsg = errorData.message || errorData.description || message.error_message;
            } catch {
              errorMsg = message.error_message;
            }
          }
          onError?.(errorMsg);
        }
      }

      // 处理最终状态消息
      if (message.status === 'done') {
        if (message.final_status === 'completed') {
          onComplete?.();
        } else if (message.final_status === 'failed') {
          onError?.(message.message || '任务失败');
        }
      }

      // 处理错误消息
      if (message.error) {
        console.error('[WebSocket] 错误:', message.error);
        // 更广泛的降级条件：任务未找到、连接超时等
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
      // 连接异常关闭时也考虑降级
      if (fallbackToPolling && !isConnected) {
        console.log('[WebSocket] 连接异常关闭，降级到轮询模式');
        setUsePolling(true);
      }
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
    lastMessage
  };
};
