import { useState, useCallback, useRef } from 'react';
import { scriptApi } from '../../../../../services/api';
import { message } from 'antd';
import { TASK_STATUS } from '../../../../../constants/status';

interface QueueItem {
  breakdownId: string;
  episodeNumber: number;
}

interface UseScriptQueueOptions {
  onTaskComplete?: (episodeNumber: number, index: number, total: number) => void;
  onQueueComplete?: () => void;
  onError?: (error: { code: string; message: string }, episodeNumber: number) => void;
  onProgress?: (progress: number, currentStep: string) => void;
  pollInterval?: number;
  novelType?: string;
}

export const useScriptQueue = (options: UseScriptQueueOptions = {}) => {
  const {
    onTaskComplete,
    onQueueComplete,
    onError,
    onProgress,
    pollInterval = 2000,
    novelType
  } = options;

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const enablePollingRef = useRef<boolean>(true);  // 默认启用轮询（批量生成需要）

  // 清理轮询
  const clearPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 处理单个任务
  const processTask = useCallback(async (
    item: QueueItem,
    queueList: QueueItem[],
    index: number
  ) => {
    try {
      setProgress(0);
      setCurrentStep(`正在生成第 ${item.episodeNumber} 集...`);

      const res = await scriptApi.startEpisodeScript(
        item.breakdownId,
        item.episodeNumber,
        { novelType }
      );
      const taskId = res.data.task_id;
      setCurrentTaskId(taskId);

      // 如果未启用轮询，直接返回（依赖 WebSocket 监控）
      if (!enablePollingRef.current) {
        console.log('[useScriptQueue] 轮询已禁用，依赖 WebSocket 监控进度');
        return;
      }

      // 启动轮询（仅在 WebSocket 失败时使用）
      clearPolling();
      intervalRef.current = setInterval(async () => {
        try {
          const res = await scriptApi.getTaskStatus(taskId);
          const data = res.data;

          setProgress(data.progress || 0);

          if (data.current_step) {
            setCurrentStep(data.current_step);
            onProgress?.(data.progress || 0, data.current_step);
          }

          if (data.status === TASK_STATUS.COMPLETED) {
            clearPolling();
            setCurrentTaskId(null);
            onTaskComplete?.(item.episodeNumber, index, queueList.length);

            // 处理下一个
            const nextIndex = index + 1;
            if (nextIndex < queueList.length) {
              setCurrentIndex(nextIndex);
              // 递归调用处理下一个任务
              processTask(queueList[nextIndex], queueList, nextIndex);
            } else {
              // 队列完成
              setIsProcessing(false);
              setQueue([]);
              setCurrentIndex(0);
              setProgress(0);
              setCurrentStep('');
              message.success('所有剧本生成完成');
              onQueueComplete?.();
            }
          } else if (data.status === TASK_STATUS.FAILED) {
            clearPolling();
            setCurrentTaskId(null);
            setIsProcessing(false);

            // 优先使用 error_display（人性化错误信息），否则解析 error_message
            let errorCode = 'UNKNOWN_ERROR';
            let errorMessage = '剧本生成失败';

            if (data.error_display && typeof data.error_display === 'object') {
              errorCode = data.error_display.code || errorCode;
              errorMessage = data.error_display.description || data.error_display.message || errorMessage;
            } else {
              const errorMsg = data.error_message || '剧本生成失败';
              try {
                const errorData = typeof errorMsg === 'string' ? JSON.parse(errorMsg) : errorMsg;
                errorCode = errorData.code || errorCode;
                errorMessage = errorData.message || errorMsg;
              } catch {
                errorMessage = errorMsg;
              }
            }

            message.error(`第 ${item.episodeNumber} 集: ${errorMessage}`);
            onError?.({ code: errorCode, message: errorMessage }, item.episodeNumber);
          }
        } catch (err) {
          clearPolling();
          setCurrentTaskId(null);
          setIsProcessing(false);
        }
      }, pollInterval);
    } catch (err: any) {
      setIsProcessing(false);
      const errorMsg = err.response?.data?.detail || '启动剧本生成失败';
      message.error(errorMsg);
      onError?.({ code: 'START_FAILED', message: errorMsg }, item.episodeNumber);
    }
  }, [clearPolling, onTaskComplete, onQueueComplete, onError, onProgress, pollInterval, novelType]);

  // 启动队列
  const startQueue = useCallback((items: QueueItem[]) => {
    if (items.length === 0) {
      message.info('没有待生成的剧集');
      return;
    }

    setQueue(items);
    setCurrentIndex(0);
    setIsProcessing(true);
    setProgress(0);
    setCurrentStep('');

    message.info(`开始批量生成 ${items.length} 集剧本`);

    // 开始处理第一个
    processTask(items[0], items, 0);
  }, [processTask]);

  // 取消队列
  const cancelQueue = useCallback(() => {
    clearPolling();
    setQueue([]);
    setCurrentIndex(0);
    setIsProcessing(false);
    setCurrentTaskId(null);
    setProgress(0);
    setCurrentStep('');
  }, [clearPolling]);

  // 停止当前任务并取消队列
  const stopQueue = useCallback(async () => {
    if (currentTaskId) {
      try {
        await scriptApi.stopTask(currentTaskId);
      } catch (err) {
        console.error('停止任务失败:', err);
      }
    }
    cancelQueue();
    message.info('已停止批量生成');
  }, [currentTaskId, cancelQueue]);

  // 稳定的 enablePolling 函数
  const enablePolling = useCallback((enable: boolean) => {
    enablePollingRef.current = enable;
  }, []);

  return {
    queue,
    currentIndex,
    isProcessing,
    currentTaskId,
    progress,
    currentStep,
    startQueue,
    cancelQueue,
    stopQueue,
    currentItem: queue[currentIndex] || null,
    enablePolling  // 控制是否启用轮询
  };
};
