import { useState, useCallback, useEffect, useRef } from 'react';
import { breakdownApi } from '../../../../../services/api';

interface BatchProgress {
  total: number;
  completed: number;
  in_progress: number;
  pending: number;
  failed: number;
  overall_progress: number;
  status_summary: {
    pending: number;
    queued: number;
    running: number;
    retrying: number;
    completed: number;
    failed: number;
  };
  task_details: any[];
  last_updated: string;
}

interface UseBatchProgressOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
  onAllCompleted?: () => void;
}

export const useBatchProgress = (
  projectId: string | null,
  options: UseBatchProgressOptions = {}
) => {
  const { autoRefresh = false, refreshInterval = 5000, onAllCompleted } = options;

  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 清理定时器
  const clearRefreshInterval = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 获取批量进度
  const refreshProgress = useCallback(async () => {
    if (!projectId) return;

    setIsLoading(true);
    try {
      const res = await breakdownApi.getBatchProgress(projectId);
      const data = res.data;
      setBatchProgress(data);

      // 检查是否全部完成
      if (data.pending === 0 && data.in_progress === 0 && data.completed > 0) {
        clearRefreshInterval();
        onAllCompleted?.();
      }

      return data;
    } catch (error) {
      console.error('获取批量进度失败:', error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [projectId, clearRefreshInterval, onAllCompleted]);

  // 开始自动刷新
  const startAutoRefresh = useCallback(() => {
    clearRefreshInterval();
    refreshProgress();
    intervalRef.current = setInterval(refreshProgress, refreshInterval);
  }, [clearRefreshInterval, refreshProgress, refreshInterval]);

  // 停止自动刷新
  const stopAutoRefresh = useCallback(() => {
    clearRefreshInterval();
  }, [clearRefreshInterval]);

  // 自动刷新
  useEffect(() => {
    if (autoRefresh && projectId) {
      startAutoRefresh();
    }

    return () => {
      clearRefreshInterval();
    };
  }, [autoRefresh, projectId, startAutoRefresh, clearRefreshInterval]);

  return {
    batchProgress,
    isLoading,
    refreshProgress,
    startAutoRefresh,
    stopAutoRefresh
  };
};
