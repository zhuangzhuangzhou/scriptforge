import { useState, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';

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

interface UseBreakdownLogsOptions {
  onStepStart?: (stepName: string, metadata?: any) => void;
  onStreamChunk?: (stepName: string, chunk: string) => void;
  onFormattedChunk?: (stepName: string, chunk: string) => void;
  onStepEnd?: (stepName: string, result?: any) => void;
  onProgress?: (progress: number, currentStep: number, totalSteps: number) => void;
  onRoundInfo?: (currentRound: number, totalRounds: number) => void;
  onError?: (error: string, errorCode?: string) => void;
  onWarning?: (warning: string) => void;
  onInfo?: (info: string) => void;
  onSuccess?: (message: string) => void;
  onComplete?: () => void;
  onBatchSwitch?: (info: {
    newTaskId: string;
    newBatchId: string;
    newBatchNumber: number;
  }) => void;
}

/**
 * Breakdown 流式日志 WebSocket Hook
 *
 * 功能：
 * - 实时接收大模型返回的流式数据
 * - 支持步骤开始、流式内容、步骤结束等消息类型
 * - 支持轮次信息（round_info）
 * - 自动处理任务完成和错误状态
 */
export const useBreakdownLogs = (
  taskId: string | null,
  options: UseBreakdownLogsOptions = {}
) => {
  const {
    onStepStart,
    onStreamChunk,
    onFormattedChunk,
    onStepEnd,
    onProgress,
    onRoundInfo,
    onError,
    onWarning,
    onInfo,
    onSuccess,
    onComplete,
    onBatchSwitch
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentRound, setCurrentRound] = useState(0);
  const [totalRounds, setTotalRounds] = useState(0);

  // 构建 WebSocket URL
  const wsUrl = taskId ? `/api/v1/ws/breakdown-logs/${taskId}` : null;

  const handleMessage = useCallback((data: StreamMessage) => {
    console.log('[BreakdownLogs] 收到消息:', data.type, data);

    switch (data.type) {
      case 'connected':
        setIsConnected(true);
        console.log('[BreakdownLogs] 已连接到日志流');
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
          if (current_step !== undefined && total_steps !== undefined) {
            onProgress?.(p || 0, current_step, total_steps);
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
        const errorCode = data.metadata?.error_code;
        onError?.(errorMsg, errorCode);
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
        // 质检维度检查结果，作为 info 处理
        if (data.content) {
          onInfo?.(data.content);
        }
        break;

      case 'task_complete':
        console.log('[BreakdownLogs] 任务完成');
        // 重置状态
        setCurrentStep('');
        setProgress(100);
        onComplete?.();
        break;

      case 'task_failed':
        console.log('[BreakdownLogs] 任务失败');
        // 重置状态
        setCurrentStep('');
        setProgress(0);
        onError?.(data.message || '任务执行失败');
        break;

      case 'batch_switch':
        console.log('[BreakdownLogs] 收到批次切换消息:', data.metadata);
        if (data.metadata?.new_task_id && data.metadata?.new_batch_id && data.metadata?.new_batch_number) {
          onBatchSwitch?.({
            newTaskId: data.metadata.new_task_id,
            newBatchId: data.metadata.new_batch_id,
            newBatchNumber: data.metadata.new_batch_number
          });
          // 显示批次切换信息
          onInfo?.(`批次 ${data.metadata.new_batch_number} 已开始拆解，正在切换...`);
        }
        break;

      default:
        console.warn('[BreakdownLogs] 未知消息类型:', data.type);
    }
  }, [onStepStart, onStreamChunk, onFormattedChunk, onStepEnd, onProgress, onRoundInfo, onError, onWarning, onInfo, onSuccess, onComplete, onBatchSwitch]);

  const { isConnected: wsConnected, lastMessage } = useWebSocket(wsUrl, {
    onMessage: (data) => handleMessage(data as StreamMessage),
    onError: (error) => {
      console.error('[BreakdownLogs] WebSocket 错误:', error);
      setIsConnected(false);
    },
    onClose: () => {
      console.log('[BreakdownLogs] WebSocket 关闭');
      setIsConnected(false);
    },
    onOpen: () => {
      console.log('[BreakdownLogs] WebSocket 打开');
      setIsConnected(true);
    },
    reconnect: true,
    reconnectInterval: 3000,
    maxReconnectAttempts: 3
  });

  return {
    isConnected: isConnected && wsConnected,
    currentStep,
    progress,
    currentRound,
    totalRounds,
    lastMessage
  };
};
