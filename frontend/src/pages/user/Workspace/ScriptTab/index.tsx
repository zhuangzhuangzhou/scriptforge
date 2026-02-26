import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { message, Modal } from 'antd';
import { XCircle, FileEdit, AlertCircle } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import ConfirmModal from '../../../../components/modals/ConfirmModal';
import ConsoleLogger from '../../../../components/ConsoleLogger';
import ScriptHistoryModal from './ScriptHistoryModal';
import ScriptViewModal from './ScriptViewModal';
import EpisodeList from './EpisodeList';
import ScriptDetail from './ScriptDetail';
import ExportModal from './ExportModal';
import { QAReportModal } from '../PlotTab/BreakdownDetail';
import { useConsoleLogger } from '../../../../hooks/useConsoleLogger';
import { useScriptPolling, useScriptQueue } from './hooks';
import { scriptApi, exportApi } from '../../../../services/api';
import { parseErrorMessage } from '../../../../utils/errorParser';
import type { EpisodeScript, ScriptStructure } from '../../../../types';

interface ScriptTabProps {
  projectId: string;
  projectName?: string;
  batchId?: string;
  breakdownId?: string;
  novelType?: string;
  onProgressUpdate?: (progress: {
    total: number;
    completed: number;
    in_progress: number;
    pending: number;
    failed: number;
  }) => void;
  onActionsReady?: (actions: {
    handleGenerateAll: () => void;
    handleContinueGenerate: () => void;
    handleRegenerateCurrent: () => void;
    handleRegenerateAll: () => void;
    handleStopBatchGenerate: () => void;
    handleStopGenerate: () => void;  // 停止单集生成
    isBatchProcessing: boolean;
    isGenerating: boolean;  // 单集生成状态
  }) => void;
}

const ScriptTab: React.FC<ScriptTabProps> = ({
  projectId,
  projectName,
  batchId,
  breakdownId,
  novelType,
  onProgressUpdate,
  onActionsReady
}) => {
  const [episodes, setEpisodes] = useState<Array<{ episode: number; status: string; breakdownId?: string; batchId?: string; script?: EpisodeScript }>>([]);
  const [selectedEpisode, setSelectedEpisode] = useState<number | null>(null);
  const [currentScript, setCurrentScript] = useState<EpisodeScript | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [consoleVisible, setConsoleVisible] = useState(false);

  // 无限滚动状态
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const PAGE_SIZE = 20;

  // 剧本历史弹窗状态
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [viewScriptModalOpen, setViewScriptModalOpen] = useState(false);
  const [historyScriptIds, setHistoryScriptIds] = useState<string[]>([]);
  const [currentHistoryIndex, setCurrentHistoryIndex] = useState(0);

  // 导出弹窗状态
  const [exportModalOpen, setExportModalOpen] = useState(false);

  // 错误弹窗状态
  const [errorModalOpen, setErrorModalOpen] = useState(false);
  const [errorInfo, setErrorInfo] = useState<{ code: string; message: string; suggestion?: string } | null>(null);

  // 质检报告弹窗状态
  const [qaReportModalOpen, setQAReportModalOpen] = useState(false);

  // 编辑模式状态
  const [editMode, setEditMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // 编辑内容状态
  const [editedStructure, setEditedStructure] = useState<ScriptStructure | null>(null);
  const [editedFullScript, setEditedFullScript] = useState<string>('');

  // 原始状态快照（用于回滚）
  const [originalState, setOriginalState] = useState<{ structure: ScriptStructure; full_script: string } | null>(null);

  // 取消确认弹窗状态
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);

  // 使用 ref 来追踪是否需要设置默认集数
  const selectedEpisodeRef = React.useRef(false);

  // 显示错误弹窗
  const showErrorModal = useCallback((error: any, defaultMessage: string = '操作失败') => {
    const parsed = parseErrorMessage(error);
    setErrorInfo({
      code: parsed.code,
      message: parsed.message || defaultMessage,
      suggestion: parsed.suggestion
    });
    setErrorModalOpen(true);
  }, []);

  // 单集生成 Hook
  const {
    taskId: currentTaskId,
    progress,
    isRunning: isGenerating,
    currentStep,
    currentEpisode: generatingEpisode,
    startGeneration,
    stopGeneration,
    setTaskId: setCurrentTaskId,
    setIsRunning,
    setEpisode,
    enablePolling
  } = useScriptPolling({
    onComplete: (episodeNumber) => {
      // 由 loadEpisodes 处理刷新
      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber ? { ...ep, status: 'completed' } : ep
      ));
    },
    onError: (error) => {
      setErrorInfo({
        code: error.code,
        message: error.message
      });
      setErrorModalOpen(true);
      setEpisodes(prev => prev.map(ep =>
        ep.status === 'in_progress' ? { ...ep, status: 'pending' } : ep
      ));
    },
    onProgress: () => {
      // 进度更新由 Hook 内部处理
    }
  });

  // 禁用 useScriptPolling 的轮询，因为我们使用 WebSocket
  useEffect(() => {
    enablePolling(false);
  }, [enablePolling]);

  // 批量生成 Hook（顺序执行队列）
  const {
    currentIndex: batchCurrentIndex,
    queue: batchQueue,
    progress: batchProgress,
    currentStep: batchCurrentStep,
    isProcessing: isBatchProcessing,  // 批量生成状态
    startQueue,
    stopQueue,
    enablePolling: enableQueuePolling
  } = useScriptQueue({
    novelType,
    onTaskComplete: (episodeNumber, index, total) => {
      console.log(`[ScriptTab] ✅ 第 ${episodeNumber} 集完成 (${index + 1}/${total})`);
      // 刷新该集数据
      refreshEpisode(episodeNumber);
    },
    onQueueComplete: () => {
      console.log('[ScriptTab] 🎉 所有剧本生成完成');
    },
    onError: (error, episodeNumber) => {
      console.error(`[ScriptTab] ❌ 第 ${episodeNumber} 集失败: ${error.message}`);
      setErrorInfo({
        code: error.code,
        message: `第 ${episodeNumber} 集: ${error.message}`
      });
      setErrorModalOpen(true);
    },
    onProgress: () => {
      // 进度更新
    }
  });

  // 注意：useScriptQueue 需要保留轮询功能，因为队列流转依赖轮询检测任务完成
  useEffect(() => {
    enableQueuePolling(true);  // 批量生成时启用轮询
  }, [enableQueuePolling]);

  // Console Logger Hook
  const {
    logs,
    llmStats,
    progress: wsProgress,
    currentStep: wsCurrentStep,
    addLog,
    clearLogs
  } = useConsoleLogger(currentTaskId, {
    enableWebSocket: true,
    pollInterval: 999999,
    taskType: 'script',
    onComplete: () => {
      // WebSocket 收到完成消息时，重置生成状态并刷新该集数据
      setIsRunning(false);
      setCurrentTaskId(null);
      // 刷新当前生成的那一集数据
      if (generatingEpisode) {
        refreshEpisode(generatingEpisode);
      }
    },
    onError: (error) => {
      // WebSocket 收到失败消息时，重置生成状态
      setIsRunning(false);
      setCurrentTaskId(null);
      setErrorInfo({
        code: error.code,
        message: error.message
      });
      setErrorModalOpen(true);
      setEpisodes(prev => prev.map(ep =>
        ep.status === 'in_progress' ? { ...ep, status: 'pending' } : ep
      ));
    }
  });

  // 加载剧集列表（使用聚合接口，支持无限滚动）
  const loadEpisodes = useCallback(async (page: number = 1, append: boolean = false) => {
    if (!projectId) return;

    try {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }

      const response = await scriptApi.getEpisodesSummary(projectId, page, PAGE_SIZE);
      const { episodes: episodeList, running_task, progress: progressData, pagination } = response.data;

      // 转换为前端格式
      const formattedEpisodes = episodeList.map((ep: any) => ({
        episode: ep.episode_number,
        status: ep.status,
        breakdownId: ep.breakdown_id,
        batchId: ep.batch_id,
        script: ep.script ? {
          id: ep.script.id,
          episode_number: ep.episode_number,
          title: ep.script.title,
          word_count: ep.script.word_count,
          status: ep.status,
          qa_status: ep.script.qa_status,
          qa_score: ep.script.qa_score,
          structure: undefined,
          full_script: undefined,
          scenes: [],
          characters: [],
          hook_type: '',
          qa_report: undefined
        } : undefined
      }));

      if (append) {
        setEpisodes(prev => [...prev, ...formattedEpisodes]);
      } else {
        setEpisodes(formattedEpisodes);
      }

      setCurrentPage(pagination.page);
      setHasMore(pagination.page < pagination.total_pages);

      // 更新进度信息
      if (onProgressUpdate) {
        onProgressUpdate(progressData);
      }

      // 恢复正在运行的任务（仅首次加载）
      if (!append && running_task) {
        console.log(`[ScriptTab] 检测到正在运行的任务: ${running_task.task_id.slice(0, 8)}, 第 ${running_task.episode_number} 集`);

        setCurrentTaskId(running_task.task_id);
        setIsRunning(true);
        setEpisode(running_task.episode_number);
        setConsoleVisible(true);

        addLog('info', `🔄 已恢复第 ${running_task.episode_number} 集的生成任务`);
      }

      // 默认选中第一集（仅首次加载）
      if (!append && !selectedEpisodeRef.current && formattedEpisodes.length > 0) {
        selectedEpisodeRef.current = true;
        setSelectedEpisode(formattedEpisodes[0].episode);
      }
    } catch (err) {
      console.error('加载剧集列表失败:', err);
      showErrorModal(err, '加载剧集列表失败');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // 加载更多
  const loadMore = useCallback(() => {
    if (hasMore && !loadingMore) {
      loadEpisodes(currentPage + 1, true);
    }
  }, [hasMore, loadingMore, currentPage, loadEpisodes]);

  // 刷新单集数据（生成完成后调用）
  const refreshEpisode = useCallback(async (episodeNumber: number) => {
    if (!projectId) return;

    const episode = episodes.find(ep => ep.episode === episodeNumber);
    if (!episode?.breakdownId) return;

    try {
      const response = await scriptApi.getEpisodeScript(episode.breakdownId, episodeNumber);
      const scriptData = response.data;

      // 更新列表中的该集数据
      setEpisodes(prev => prev.map(ep => {
        if (ep.episode !== episodeNumber) return ep;
        return {
          ...ep,
          status: 'completed',
          script: scriptData ? {
            id: scriptData.id,
            episode_number: episodeNumber,
            title: scriptData.title,
            word_count: scriptData.word_count,
            status: 'completed' as const,
            qa_status: scriptData.qa_status,
            qa_score: scriptData.qa_score,
          } as EpisodeScript : undefined
        };
      }));
    } catch (err) {
      console.error(`刷新第 ${episodeNumber} 集数据失败:`, err);
      // 失败时至少更新状态
      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber ? { ...ep, status: 'completed' } : ep
      ));
    }
  }, [projectId, episodes]);

  // 合并进度
  const effectiveProgress = wsProgress > 0 ? wsProgress : progress;
  const effectiveCurrentStep = wsCurrentStep || currentStep;

  // 判断是否正在生成（全局状态，用于 Console 等）
  const isAnyGenerating = isGenerating || isBatchProcessing;

  // 判断当前选中的剧集是否正在生成（用于 ScriptDetail 显示）
  const isCurrentEpisodeGenerating = useMemo(() => {
    // 单集生成：检查 generatingEpisode 是否为当前选中剧集
    if (isGenerating && generatingEpisode === selectedEpisode) {
      return true;
    }
    // 批量生成：检查当前队列项是否为当前选中剧集
    if (isBatchProcessing && batchQueue[batchCurrentIndex]?.episodeNumber === selectedEpisode) {
      return true;
    }
    return false;
  }, [isGenerating, generatingEpisode, selectedEpisode, isBatchProcessing, batchQueue, batchCurrentIndex]);

  // 监听 projectId 变化
  React.useEffect(() => {
    selectedEpisodeRef.current = false;
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadEpisodes();
    }
  }, [projectId, loadEpisodes]);

  // 加载单集剧本完整数据（包含 structure、full_script 等大字段）
  const loadEpisodeScript = useCallback(async (episodeNumber: number) => {
    if (!projectId) return;

    const episode = episodes.find(ep => ep.episode === episodeNumber);
    if (!episode?.script?.id) {
      setCurrentScript(null);
      return;
    }

    try {
      // 调用详情接口获取完整数据
      const response = await scriptApi.getScriptDetail(episode.script.id);
      const scriptData = response.data;

      setCurrentScript({
        id: scriptData.id,
        episode_number: scriptData.episode_number,
        title: scriptData.title,
        word_count: scriptData.word_count,
        status: scriptData.status as EpisodeScript['status'],
        qa_status: scriptData.qa_status,
        qa_score: scriptData.qa_score,
        structure: scriptData.content?.structure,
        full_script: scriptData.content?.full_script,
        scenes: scriptData.content?.scenes || [],
        characters: scriptData.content?.characters || [],
        hook_type: scriptData.content?.hook_type || '',
        qa_report: scriptData.qa_report
      });
    } catch (err) {
      console.error('加载剧本详情失败:', err);
      // 降级使用列表中的基本信息
      setCurrentScript(episode.script);
    }
  }, [projectId, episodes]);

  useEffect(() => {
    if (selectedEpisode && projectId) {
      loadEpisodeScript(selectedEpisode);
    }
  }, [selectedEpisode, projectId, loadEpisodeScript]);

  // 防误触退出
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // 导出剧本
  const handleExport = async (scope: 'current' | 'all' | 'merged', format: 'pdf' | 'docx') => {
    // 显示加载提示
    const loadingMsg = scope === 'merged'
      ? '正在合并导出所有剧集，请稍候...'
      : scope === 'all'
        ? '正在打包导出所有剧集，请稍候...'
        : '正在导出...';
    const hideLoading = message.loading(loadingMsg, 0);

    try {
      setExporting(true);

      if (scope === 'current') {
        // 导出当前集
        if (!currentScript?.id) {
          message.error('当前剧本不存在');
          return;
        }

        const response = await exportApi.exportSingle(currentScript.id, format);
        const mimeType = format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
        const blob = new Blob([response.data], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${projectName || '剧本'}_${currentScript.episode_number}集.${format}`;
        link.click();
        URL.revokeObjectURL(url);
        message.success('导出成功');
      } else if (scope === 'merged') {
        // 合并导出为一份文档
        if (!projectId) {
          message.error('项目信息缺失');
          return;
        }

        const response = await exportApi.exportBatch(projectId, 'docx', true);
        const blob = new Blob([response.data], {
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${projectName || '剧本'}_全集剧本.docx`;
        link.click();
        URL.revokeObjectURL(url);
        message.success('导出成功');
      } else {
        // 分集导出（返回 ZIP 文件）
        if (!projectId) {
          message.error('项目信息缺失');
          return;
        }

        const response = await exportApi.exportBatch(projectId, format, false);
        const blob = new Blob([response.data], { type: 'application/zip' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${projectName || '剧本'}_剧本导出.zip`;
        link.click();
        URL.revokeObjectURL(url);
        message.success('导出成功');
      }
    } catch (err: any) {
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        message.error('导出超时，请稍后重试或减少导出数量');
      } else {
        showErrorModal(err, '导出失败');
      }
    } finally {
      hideLoading();
      setExporting(false);
    }
  };

  // 保存剧本
  const handleSave = async () => {
    if (!currentScript?.id || !editedStructure) return;

    try {
      setIsSaving(true);

      const newContent = {
        structure: editedStructure,
        full_script: editedFullScript,
        scenes: currentScript.scenes || [],
        characters: currentScript.characters || [],
        hook_type: currentScript.hook_type || ''
      };

      await scriptApi.updateScript(currentScript.id, {
        content: newContent
      });

      const structureWordCount = Object.values(editedStructure).reduce(
        (sum, s) => sum + (s?.word_count || 0), 0
      );
      const fullScriptWordCount = editedFullScript.length;
      const totalWordCount = fullScriptWordCount > 0 ? fullScriptWordCount : structureWordCount;

      setCurrentScript({
        ...currentScript,
        structure: editedStructure,
        full_script: editedFullScript,
        word_count: totalWordCount
      });

      setHasUnsavedChanges(false);
      setEditMode(false);
      message.success('保存成功');
    } catch (err: any) {
      if (originalState) {
        setEditedStructure(originalState.structure);
        setEditedFullScript(originalState.full_script);
      }
      message.error(err.response?.data?.detail || '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  // 取消编辑
  const handleCancelEdit = () => {
    if (hasUnsavedChanges) {
      setCancelConfirmOpen(true);
      return;
    }
    doCancelEdit();
  };

  // 执行取消编辑
  const doCancelEdit = () => {
    setCancelConfirmOpen(false);
    setEditMode(false);
    setEditedStructure(null);
    setEditedFullScript('');
    setHasUnsavedChanges(false);
    setOriginalState(null);
  };

  // 进入编辑模式
  const handleEnterEditMode = () => {
    if (!currentScript) return;

    if (!currentScript.structure) {
      message.error('剧本结构数据缺失，无法编辑');
      return;
    }

    const structureCopy: ScriptStructure = {
      opening: { ...currentScript.structure.opening },
      development: { ...currentScript.structure.development },
      climax: { ...currentScript.structure.climax },
      hook: { ...currentScript.structure.hook }
    };

    setEditedStructure(structureCopy);
    setEditedFullScript(currentScript.full_script || '');
    setOriginalState({
      structure: structureCopy,
      full_script: currentScript.full_script || ''
    });
    setEditMode(true);
  };

  // 处理四段式结构内容变更
  const handleStructureChange = (key: keyof ScriptStructure, content: string) => {
    if (!editedStructure) return;

    const wordCount = content.length;
    const updatedStructure = {
      ...editedStructure,
      [key]: {
        content,
        word_count: wordCount
      }
    };

    setEditedStructure(updatedStructure);

    // 同步更新完整剧本：将四段式内容拼接
    const fullScript = [
      `【起】开场冲突\n${updatedStructure.opening.content}\n`,
      `【承】推进发展\n${updatedStructure.development.content}\n`,
      `【转】反转高潮\n${updatedStructure.climax.content}\n`,
      `【钩】悬念结尾\n${updatedStructure.hook.content}`
    ].join('\n');

    setEditedFullScript(fullScript);
    setHasUnsavedChanges(true);
  };

  // 处理完整剧本内容变更
  const handleFullScriptChange = (content: string) => {
    setEditedFullScript(content);
    setHasUnsavedChanges(true);
  };

  // 生成单集剧本
  const handleGenerateScript = async (episodeNumber: number) => {
    if (!projectId) {
      message.error('项目信息缺失');
      return;
    }

    const episode = episodes.find(ep => ep.episode === episodeNumber);
    if (!episode?.breakdownId) {
      message.error('未找到拆解结果');
      return;
    }

    try {
      clearLogs();
      setConsoleVisible(true);

      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber ? { ...ep, status: 'in_progress' } : ep
      ));

      await startGeneration(episode.breakdownId, episodeNumber, { novelType });
      addLog('info', `🎬 已启动第 ${episodeNumber} 集剧本生成任务`);

    } catch (err: any) {
      const parsed = parseErrorMessage(err);
      const errorMsg = parsed.message || '启动剧本生成失败';
      addLog('error', `❌ ${errorMsg}`);

      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber ? { ...ep, status: 'pending' } : ep
      ));

      if (parsed.suggestion || parsed.code !== 'UNKNOWN_ERROR') {
        setErrorInfo({
          code: parsed.code,
          message: errorMsg,
          suggestion: parsed.suggestion
        });
        setErrorModalOpen(true);
      }
    }
  };

  // 批量生成剧本（顺序执行：完成一集再开始下一集）
  const handleBatchGenerate = async () => {
    if (!projectId || episodes.length === 0) {
      message.error('没有可生成的剧集');
      return;
    }

    const pendingEpisodes = episodes.filter(ep => ep.status === 'pending' && ep.breakdownId);
    if (pendingEpisodes.length === 0) {
      message.info('所有剧集已生成');
      return;
    }

    clearLogs();
    setConsoleVisible(true);

    // 构建队列项
    const queueItems = pendingEpisodes.map(ep => ({
      breakdownId: ep.breakdownId!,
      episodeNumber: ep.episode
    }));

    addLog('info', `🎬 开始批量生成 ${queueItems.length} 集剧本`);
    addLog('info', `待生成剧集: ${queueItems.map(q => q.episodeNumber).join(', ')}`);

    // 使用队列顺序执行
    startQueue(queueItems);
  };

  // 停止批量生成
  const handleStopBatchGenerate = async () => {
    await stopQueue();
    addLog('warning', '⚠️ 已停止批量生成');
  };

  // 继续生成：从第一个待生成的剧集开始
  const handleContinueGenerate = async () => {
    if (!projectId || episodes.length === 0) {
      message.error('没有可生成的剧集');
      return;
    }

    const pendingEpisodes = episodes.filter(ep => ep.status === 'pending');
    if (pendingEpisodes.length === 0) {
      message.info('所有剧集已生成');
      return;
    }

    // 找到第一个待生成的剧集
    const firstPending = pendingEpisodes[0];
    setSelectedEpisode(firstPending.episode);

    // 开始生成
    if (firstPending.breakdownId) {
      await handleGenerateScript(firstPending.episode);
    } else {
      message.error('该剧集没有关联的拆解数据');
    }
  };

  // 重新生成当前集：重新生成当前选中的剧集
  const handleRegenerateCurrent = async () => {
    if (!projectId || !selectedEpisode) {
      message.error('请先选择要重新生成的剧集');
      return;
    }

    const episode = episodes.find(ep => ep.episode === selectedEpisode);
    if (!episode?.breakdownId) {
      message.error('该剧集没有关联的拆解数据');
      return;
    }

    clearLogs();
    setConsoleVisible(true);

    addLog('info', `🔄 开始重新生成第 ${selectedEpisode} 集剧本`);

    // 重新生成当前集
    await handleGenerateScript(selectedEpisode);
  };

  // 重新生成所有：重新生成所有剧集（包括已完成的）
  const handleRegenerateAll = async () => {
    if (!projectId || episodes.length === 0) {
      message.error('没有可生成的剧集');
      return;
    }

    clearLogs();
    setConsoleVisible(true);

    const queueItems = episodes
      .filter(ep => ep.breakdownId)
      .map(ep => ({
        breakdownId: ep.breakdownId!,
        episodeNumber: ep.episode
      }));

    if (queueItems.length === 0) {
      message.error('没有有效的待生成剧集');
      return;
    }

    setEpisodes(prev => prev.map(ep => ({ ...ep, status: 'in_progress' })));

    addLog('info', `🔄 开始重新生成所有 ${queueItems.length} 集剧本`);
    addLog('info', `待生成剧集: ${queueItems.map(q => q.episodeNumber).join(', ')}`);

    startQueue(queueItems);
  };

  // 暴露操作函数给父组件
  useEffect(() => {
    if (onActionsReady) {
      onActionsReady({
        handleGenerateAll: handleBatchGenerate,
        handleContinueGenerate,
        handleRegenerateCurrent,
        handleRegenerateAll,
        handleStopBatchGenerate,
        handleStopGenerate: stopGeneration,  // 停止单集生成
        isBatchProcessing,
        isGenerating  // 单集生成状态
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodes, projectId, selectedEpisode, isBatchProcessing, isGenerating]);


  // 无项目信息时的提示
  if (!projectId) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950">
        <div className="text-center text-slate-500">
          <FileEdit size={64} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">项目信息缺失</p>
          <p className="text-sm mt-2">请返回项目列表重新进入</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex gap-0 overflow-hidden bg-slate-950">
      {/* 取消编辑确认弹窗 */}
      <ConfirmModal
        open={cancelConfirmOpen}
        onCancel={() => setCancelConfirmOpen(false)}
        onConfirm={doCancelEdit}
        title="确认取消编辑"
        content="有未保存的更改，确定要取消吗？取消后所有更改将丢失。"
        confirmText="确定取消"
        confirmType="danger"
        iconType="warning"
      />

      {/* 错误详情弹窗 */}
      <Modal
        open={errorModalOpen}
        onCancel={() => setErrorModalOpen(false)}
        footer={null}
        centered
        width={400}
        closeIcon={<XCircle size={18} className="text-slate-500 hover:text-white transition-colors" />}
        styles={{
          mask: { backgroundColor: 'rgba(0, 0, 0, 0.4)', backdropFilter: 'blur(2px)' },
          content: {
            backgroundColor: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '16px',
            padding: '0',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }
        }}
      >
        <div className="text-center p-6">
          <div className="mx-auto w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mb-4">
            <XCircle size={32} className="text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">操作失败</h3>
          <p className="text-sm text-slate-300 mb-4">{errorInfo?.message}</p>
          {errorInfo?.suggestion && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 mb-4">
              <div className="flex items-start gap-2">
                <AlertCircle size={16} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-amber-300 text-left">{errorInfo.suggestion}</p>
              </div>
            </div>
          )}
          <button
            onClick={() => setErrorModalOpen(false)}
            className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm rounded-lg border border-slate-700 transition-colors"
          >
            关闭
          </button>
        </div>
      </Modal>

      {/* 左侧栏：剧集列表 */}
      <EpisodeList
        episodes={episodes}
        selectedEpisode={selectedEpisode}
        onSelectEpisode={setSelectedEpisode}
        loading={loading}
        hasMore={hasMore}
        onLoadMore={loadMore}
        loadingMore={loadingMore}
      />

      {/* 右侧主内容区 */}
      <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
        <div className="flex-1 overflow-y-auto p-0">
          <ScriptDetail
            currentScript={currentScript}
            selectedEpisode={selectedEpisode}
            onGenerateScript={handleGenerateScript}
            onStopGenerate={stopGeneration}
            isGenerating={isCurrentEpisodeGenerating}
            progress={effectiveProgress}
            onViewHistory={() => setHistoryModalOpen(true)}
            onExport={() => setExportModalOpen(true)}
            onEdit={handleEnterEditMode}
            editMode={editMode}
            onSaveEdit={handleSave}
            onCancelEdit={handleCancelEdit}
            hasUnsavedChanges={hasUnsavedChanges}
            editedStructure={editedStructure}
            editedFullScript={editedFullScript}
            onStructureChange={handleStructureChange}
            onFullScriptChange={handleFullScriptChange}
          />
        </div>
      </div>

      {/* Console Logger */}
      <ConsoleLogger
        logs={logs}
        llmStats={llmStats}
        visible={consoleVisible}
        isProcessing={isAnyGenerating}
        progress={effectiveProgress}
        currentStep={effectiveCurrentStep}
        episodeNumber={generatingEpisode || selectedEpisode || 0}
        onClose={() => setConsoleVisible(false)}
      />

      {/* 质检报告弹窗 */}
      <AnimatePresence>
        {qaReportModalOpen && currentScript?.qa_report && (
          <QAReportModal
            report={{
              status: currentScript.qa_report.status,
              score: currentScript.qa_report.score,
              dimensions: Object.entries(currentScript.qa_report.dimensions).map(([key, value]) => ({
                name: key,
                pass: value.score >= 60,
                score: value.score,
                issues: value.issues
              })),
              issues: currentScript.qa_report.fix_instructions?.map(fi => fi.issue) || [],
              suggestions: currentScript.qa_report.fix_instructions?.map(fi => fi.suggestion) || [],
              fix_instructions: currentScript.qa_report.fix_instructions
            }}
            onClose={() => setQAReportModalOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* 剧本历史弹窗 */}
      {historyModalOpen && selectedEpisode && (
        <ScriptHistoryModal
          episodeNumber={selectedEpisode}
          projectId={projectId}
          onClose={() => setHistoryModalOpen(false)}
          onViewScript={(scriptId, allIds) => {
            setHistoryScriptIds(allIds || [scriptId]);
            setCurrentHistoryIndex(allIds?.indexOf(scriptId) || 0);
            setHistoryModalOpen(false);
            setViewScriptModalOpen(true);
          }}
          onSetCurrent={async (scriptId) => {
            try {
              await scriptApi.setCurrentScript(projectId, selectedEpisode!, scriptId);
              message.success('已设置为当前版本');
              // 重新加载剧集列表以更新当前剧本
              await loadEpisodes();
              // 重新加载当前剧本详情
              if (selectedEpisode) {
                const episode = episodes.find(ep => ep.episode === selectedEpisode);
                if (episode?.script) {
                  setCurrentScript(episode.script);
                }
              }
            } catch (err: any) {
              showErrorModal(err, '设置当前版本失败');
            }
          }}
        />
      )}

      {/* 剧本查看弹窗 */}
      {viewScriptModalOpen && historyScriptIds.length > 0 && (
        <ScriptViewModal
          scriptId={historyScriptIds[currentHistoryIndex]}
          allScriptIds={historyScriptIds}
          onClose={() => setViewScriptModalOpen(false)}
          onPrevious={currentHistoryIndex > 0 ? () => setCurrentHistoryIndex(currentHistoryIndex - 1) : undefined}
          onNext={currentHistoryIndex < historyScriptIds.length - 1 ? () => setCurrentHistoryIndex(currentHistoryIndex + 1) : undefined}
        />
      )}

      {/* 导出弹窗 */}
      {exportModalOpen && currentScript && (
        <ExportModal
          onClose={() => setExportModalOpen(false)}
          onExport={handleExport}
          currentEpisode={currentScript.episode_number}
          totalEpisodes={episodes.length}
        />
      )}
    </div>
  );
};

export default ScriptTab;
