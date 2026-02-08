import { useState, useCallback, useRef } from 'react';
import { breakdownApi } from '../../../../../services/api';
import { message } from 'antd';

interface UseBreakdownQueueOptions {
  onTaskComplete?: (batchId: string, index: number, total: number) => void;
  onQueueComplete?: () => void;
  onError?: (error: { code: string; message: string }, batchId: string) => void;
  onProgress?: (progress: number, currentStep: string) => void;
  pollInterval?: number;
}

export const useBreakdownQueue = (options: UseBreakdownQueueOptions = {}) => {
  const {
    onTaskComplete,
    onQueueComplete,
    onError,
    onProgress,
    pollInterval = 2000
  } = options;

  const [queue, setQueue] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 清理轮询
  const clearPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 处理单个任务的轮询
  const pollTaskStatus = useCallback((
    taskId: string,
    batchId: string,
    queueList: string[],
    index: number
  ) => {
    clearPolling();

    intervalRef.current = setInterval(async () => {
      try {
        const res = await breakdownApi.getTaskStatus(taskId);
        const data = res.data;

        setProgress(data.progress || 0);

        if (data.current_step) {
          onProgress?.(data.progress || 0, data.current_step);
        }

        if (data.status === 'completed') {
          clearPolling();
          setCurrentTaskId(null);
          onTaskComplete?.(batchId, index, queueList.length);

          // 处理下一个
          const nextIndex = index + 1;
          if (nextIndex < queueList.length) {
            setCurrentIndex(nextIndex);
            processTask(queueList[nextIndex], queueList, nextIndex);
          } else {
            // 队列完成
            setIsProcessing(false);
            setQueue([]);
            setCurrentIndex(0);
            message.success('所有批次拆解完成');
            onQueueComplete?.();
          }
        } else if (data.status === 'failed') {
          clearPolling();
          setCurrentTaskId(null);
          setIsProcessing(false);

          const errorMsg = data.error_message || '拆解失败';
          let errorCode = 'UNKNOWN_ERROR';
          let errorMessage = errorMsg;

          try {
            const errorData = typeof errorMsg === 'string' ? JSON.parse(errorMsg) : errorMsg;
            errorCode = errorData.code || errorCode;
            errorMessage = errorData.message || errorMsg;
          } catch {
            // 保持原始错误信息
          }

          message.error(errorMessage);
          onError?.({ code: errorCode, message: errorMessage }, batchId);
        }
      } catch (err) {
        clearPolling();
        setCurrentTaskId(null);
        setIsProcessing(false);
      }
    }, pollInterval);
  }, [clearPolling, onTaskComplete, onQueueComplete, onError, onProgress, pollInterval]);

  // 处理单个任务
  const processTask = useCallback(async (
    batchId: string,
    queueList: string[],
    index: number
  ) => {
    try {
      const res = await breakdownApi.startBreakdown(batchId);
      const taskId = res.data.task_id;
      setCurrentTaskId(taskId);
      pollTaskStatus(taskId, batchId, queueList, index);
    } catch (err: any) {
      setIsProcessing(false);
      const errorMsg = err.response?.data?.detail || '启动拆解失败';
      message.error(errorMsg);
      onError?.({ code: 'START_FAILED', message: errorMsg }, batchId);
    }
  }, [pollTaskStatus, onError]);

  // 启动队列
  const startQueue = useCallback((batchIds: string[]) => {
    if (batchIds.length === 0) {
      message.info('没有待拆解的批次');
      return;
    }

    setQueue(batchIds);
    setCurrentIndex(0);
    setIsProcessing(true);
    setProgress(0);

    // 开始处理第一个
    processTask(batchIds[0], batchIds, 0);
  }, [processTask]);

  // 取消队列
  const cancelQueue = useCallback(() => {
    clearPolling();
    setQueue([]);
    setCurrentIndex(0);
    setIsProcessing(false);
    setCurrentTaskId(null);
    setProgress(0);
  }, [clearPolling]);

  return {
    queue,
    currentIndex,
    isProcessing,
    currentTaskId,
    progress,
    startQueue,
    cancelQueue,
    currentBatchId: queue[currentIndex] || null
  };
};
