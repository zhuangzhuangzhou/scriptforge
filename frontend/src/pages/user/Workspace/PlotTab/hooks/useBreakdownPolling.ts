import { useState, useCallback, useRef, useEffect } from 'react';
import { breakdownApi } from '../../../../../services/api';
import { message } from 'antd';

interface UseBreakdownPollingOptions {
  onComplete?: (batchId: string) => void;
  onError?: (error: { code: string; message: string }) => void;
  onProgress?: (progress: number, currentStep: string) => void;
  pollInterval?: number;
}

export const useBreakdownPolling = (options: UseBreakdownPollingOptions = {}) => {
  const { onComplete, onError, onProgress, pollInterval = 2000 } = options;

  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const batchIdRef = useRef<string | null>(null);

  // 清理轮询
  const clearPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 开始轮询
  const startPolling = useCallback((newTaskId: string, batchId: string) => {
    clearPolling();
    batchIdRef.current = batchId;

    intervalRef.current = setInterval(async () => {
      try {
        const res = await breakdownApi.getTaskStatus(newTaskId);
        const data = res.data;

        setProgress(data.progress || 0);

        if (data.current_step) {
          setCurrentStep(data.current_step);
          onProgress?.(data.progress || 0, data.current_step);
        }

        if (data.status === 'completed') {
          clearPolling();
          setTaskId(null);
          setIsRunning(false);
          message.success('拆解完成');
          onComplete?.(batchId);
        } else if (data.status === 'failed') {
          clearPolling();
          setTaskId(null);
          setIsRunning(false);

          // 解析错误信息
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

          onError?.({ code: errorCode, message: errorMessage });
        }
      } catch (err) {
        clearPolling();
        setTaskId(null);
        setIsRunning(false);
      }
    }, pollInterval);
  }, [clearPolling, onComplete, onError, onProgress, pollInterval]);

  // 启动拆解任务
  const startBreakdown = useCallback(async (
    batchId: string,
    config?: {
      selectedSkills?: string[];
      adaptMethodKey?: string;
      qualityRuleKey?: string;
      outputStyleKey?: string;
    }
  ) => {
    try {
      setIsRunning(true);
      setProgress(0);
      setCurrentStep('');

      const res = await breakdownApi.startBreakdown(batchId, config);
      const newTaskId = res.data.task_id;

      setTaskId(newTaskId);
      message.info('拆解任务已启动');

      // 开始轮询
      startPolling(newTaskId, batchId);

      return res.data;
    } catch (err: any) {
      setIsRunning(false);
      const errorMsg = err.response?.data?.detail || '启动拆解失败';
      message.error(errorMsg);
      onError?.({ code: 'START_FAILED', message: errorMsg });
      throw err;
    }
  }, [startPolling, onError]);

  // 取消拆解
  const cancelBreakdown = useCallback(() => {
    clearPolling();
    setTaskId(null);
    setIsRunning(false);
    setProgress(0);
    setCurrentStep('');
  }, [clearPolling]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      clearPolling();
    };
  }, [clearPolling]);

  return {
    taskId,
    progress,
    isRunning,
    currentStep,
    startBreakdown,
    cancelBreakdown
  };
};
