import { useState, useCallback, useRef, useEffect } from 'react';
import { scriptApi } from '../../../../../services/api';
import { message } from 'antd';
import { TASK_STATUS } from '../../../../../constants/status';

interface UseScriptPollingOptions {
  onComplete?: (episodeNumber: number) => void;
  onError?: (error: { code: string; message: string }) => void;
  onProgress?: (progress: number, currentStep: string) => void;
  pollInterval?: number;
}

export const useScriptPolling = (options: UseScriptPollingOptions = {}) => {
  const { onComplete, onError, onProgress, pollInterval = 2000 } = options;

  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const episodeRef = useRef<number | null>(null);

  // 清理轮询
  const clearPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 开始轮询
  const startPolling = useCallback((newTaskId: string, episodeNumber: number) => {
    clearPolling();
    episodeRef.current = episodeNumber;

    intervalRef.current = setInterval(async () => {
      try {
        const res = await scriptApi.getTaskStatus(newTaskId);
        const data = res.data;

        setProgress(data.progress || 0);

        if (data.current_step) {
          setCurrentStep(data.current_step);
          onProgress?.(data.progress || 0, data.current_step);
        }

        if (data.status === TASK_STATUS.COMPLETED) {
          clearPolling();
          setTaskId(null);
          setIsRunning(false);
          message.success(`第 ${episodeNumber} 集剧本生成完成`);
          onComplete?.(episodeNumber);
        } else if (data.status === TASK_STATUS.FAILED) {
          clearPolling();
          setTaskId(null);
          setIsRunning(false);

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

          message.error(errorMessage);
          onError?.({ code: errorCode, message: errorMessage });
        }
      } catch (err) {
        clearPolling();
        setTaskId(null);
        setIsRunning(false);
      }
    }, pollInterval);
  }, [clearPolling, onComplete, onError, onProgress, pollInterval]);

  // 启动剧本生成
  const startGeneration = useCallback(async (
    breakdownId: string,
    episodeNumber: number,
    options?: { modelConfigId?: string; novelType?: string }
  ) => {
    try {
      setIsRunning(true);
      setProgress(0);
      setCurrentStep('');

      const res = await scriptApi.startEpisodeScript(breakdownId, episodeNumber, options);
      const newTaskId = res.data.task_id;

      setTaskId(newTaskId);
      message.info(`已启动第 ${episodeNumber} 集剧本生成`);

      // 开始轮询
      startPolling(newTaskId, episodeNumber);

      return res.data;
    } catch (err: any) {
      setIsRunning(false);
      const errorMsg = err.response?.data?.detail || '启动剧本生成失败';
      message.error(errorMsg);
      onError?.({ code: 'START_FAILED', message: errorMsg });
      throw err;
    }
  }, [startPolling, onError]);

  // 取消生成（仅停止轮询，不调用后端）
  const cancelGeneration = useCallback(() => {
    clearPolling();
    setTaskId(null);
    setIsRunning(false);
    setProgress(0);
    setCurrentStep('');
  }, [clearPolling]);

  // 停止生成（调用后端 API 停止任务）
  const stopGeneration = useCallback(async () => {
    if (!taskId) return;

    try {
      await scriptApi.stopTask(taskId);

      clearPolling();
      setTaskId(null);
      setIsRunning(false);
      setProgress(0);
      setCurrentStep('');

      message.success('剧本生成任务已停止');
    } catch (err: any) {
      console.error('停止任务失败:', err);
      message.error(err.response?.data?.detail || '停止任务失败');
    }
  }, [taskId, clearPolling]);

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
    currentEpisode: episodeRef.current,
    startGeneration,
    cancelGeneration,
    stopGeneration
  };
};
