import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Layers, RefreshCw, CheckCircle2, Loader2,
  ThumbsUp, Download, FileEdit, Save, FileCheck, Search, AlertCircle,
  Play, ChevronRight, Eye, Edit3, Terminal
} from 'lucide-react';
import { message } from 'antd';
import ConfirmModal from '../../../../components/modals/ConfirmModal';
import ConsoleLogger, { LogEntry } from '../../../../components/ConsoleLogger';
import { useBreakdownLogs } from '../../../../hooks/useBreakdownLogs';
import { scriptApi, breakdownApi, exportApi } from '../../../../services/api';
import type { EpisodeScript, PlotPoint, ScriptStructure } from '../../../../types';
import { TASK_STATUS } from '../../../../constants/status';

interface ScriptTabProps {
  projectId: string;
  batchId?: string;
  breakdownId?: string;
  novelType?: string;
}

// 四段式结构标签
const STRUCTURE_LABELS = {
  opening: { name: '起', desc: '开场冲突', color: 'cyan', target: '100-150字' },
  development: { name: '承', desc: '推进发展', color: 'blue', target: '150-200字' },
  climax: { name: '转', desc: '反转高潮', color: 'purple', target: '200-250字' },
  hook: { name: '钩', desc: '悬念结尾', color: 'amber', target: '100-150字' }
} as const;

const ScriptTab: React.FC<ScriptTabProps> = ({
  batchId,
  breakdownId,
  novelType
}) => {
  const [episodes, setEpisodes] = useState<Array<{ episode: number; status: string; script?: EpisodeScript }>>([]);
  const [selectedEpisode, setSelectedEpisode] = useState<number | null>(null);
  const [currentScript, setCurrentScript] = useState<EpisodeScript | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'structure' | 'full'>('structure');
  const [exporting, setExporting] = useState(false);
  const [approving, setApproving] = useState(false);

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

  // 日志类型
  type LogType = 'info' | 'success' | 'warning' | 'error' | 'thinking' | 'llm_call' | 'stream' | 'formatted';

  // 创建日志条目的辅助函数
  const createLog = (type: LogType, message: string): LogEntry => ({
    id: `log-${Date.now()}-${Math.random()}`,
    timestamp: new Date().toLocaleTimeString(),
    type,
    message
  });

  // 日志相关状态
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentStep, setCurrentStep] = useState('');
  const [progress, setProgress] = useState(0);
  const logsRef = useRef<LogEntry[]>([]);
  // 使用 useState 而不是 useRef，以便在 taskId 变化时触发 WebSocket 重连
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  // 使用 BreakdownLogs Hook 接收 WebSocket 日志
  const { isConnected } = useBreakdownLogs(
    currentTaskId,
    {
      onStepStart: (stepName) => {
        setCurrentStep(stepName);
        logsRef.current = [...logsRef.current, createLog('thinking', `🚀 ${stepName}`)];
        setLogs([...logsRef.current]);
      },
      onStreamChunk: (_stepName, chunk) => {
        // 查找最后一个 stream 类型的日志
        const lastStreamIndex = logsRef.current.findIndex((log, idx) => log.type === 'stream' && idx === logsRef.current.length - 1);
        if (lastStreamIndex >= 0) {
          const updated = [...logsRef.current];
          updated[lastStreamIndex] = { ...updated[lastStreamIndex], message: updated[lastStreamIndex].message + chunk };
          logsRef.current = updated;
          setLogs([...logsRef.current]);
        } else {
          logsRef.current = [...logsRef.current, createLog('stream', chunk)];
          setLogs([...logsRef.current]);
        }
      },
      onFormattedChunk: (_stepName, chunk) => {
        logsRef.current = [...logsRef.current, createLog('formatted', chunk)];
        setLogs([...logsRef.current]);
      },
      onStepEnd: (_stepName, result) => {
        logsRef.current = [...logsRef.current, createLog('success', '✅ 步骤完成')];
        setLogs([...logsRef.current]);
      },
      onProgress: (p) => {
        setProgress(p);
      },
      onInfo: (info) => {
        logsRef.current = [...logsRef.current, createLog('info', info)];
        setLogs([...logsRef.current]);
      },
      onSuccess: (msg) => {
        logsRef.current = [...logsRef.current, createLog('success', msg)];
        setLogs([...logsRef.current]);
      },
      onWarning: (msg) => {
        logsRef.current = [...logsRef.current, createLog('warning', msg)];
        setLogs([...logsRef.current]);
      },
      onError: (errMsg) => {
        logsRef.current = [...logsRef.current, createLog('error', errMsg)];
        setLogs([...logsRef.current]);
      },
      onComplete: () => {
        logsRef.current = [...logsRef.current, createLog('success', '🎉 剧本生成完成！')];
        setLogs([...logsRef.current]);
        setCurrentStep('');
        setProgress(100);
        // 加载生成的剧本
        if (selectedEpisode) {
          loadEpisodeScript(selectedEpisode);
        }
      }
    }
  );

  // 加载剧集列表（从拆解结果的 plot_points 中提取）
  const loadEpisodes = useCallback(async () => {
    if (!batchId) return;

    try {
      setLoading(true);
      const response = await breakdownApi.getBreakdownResults(batchId);
      const data = response.data;

      if (data.plot_points) {
        // 从 plot_points 中提取集数
        const episodeSet = new Set<number>();
        (data.plot_points as PlotPoint[]).forEach(pp => {
          if (pp.episode) episodeSet.add(pp.episode);
        });

        const episodeList = Array.from(episodeSet).sort((a, b) => a - b).map(ep => ({
          episode: ep,
          status: 'pending'
        }));

        setEpisodes(episodeList);
        // 只有在没有选中任何集数时才设置默认选中第一集
        // 使用 ref 来追踪是否需要设置默认值，避免循环触发
        if (!selectedEpisodeRef.current && episodeList.length > 0) {
          selectedEpisodeRef.current = true; // 标记已设置
          setSelectedEpisode(episodeList[0].episode);
        }
      }
    } catch (err) {
      console.error('加载剧集列表失败:', err);
      setError('加载剧集列表失败');
    } finally {
      setLoading(false);
    }
  }, [batchId]);

  // 使用 ref 来追踪是否需要设置默认集数
  const selectedEpisodeRef = React.useRef(false);

  // 监听 batchId 变化，重置 ref
  React.useEffect(() => {
    selectedEpisodeRef.current = false;
  }, [batchId]);

  useEffect(() => {
    // 只在 batchId 变化时加载，不需要依赖 loadEpisodes
    if (batchId) {
      loadEpisodes();
    }
  }, [batchId, loadEpisodes]);

  // 加载单集剧本
  const loadEpisodeScript = useCallback(async (episodeNumber: number) => {
    if (!breakdownId) return;

    try {
      const response = await scriptApi.getEpisodeScript(breakdownId, episodeNumber);
      setCurrentScript(response.data);
      // 更新列表中的状态
      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber
          ? { ...ep, status: 'completed', script: response.data }
          : ep
      ));
    } catch {
      // 剧本不存在，保持 pending 状态
      setCurrentScript(null);
    }
  }, [breakdownId]);

  useEffect(() => {
    if (selectedEpisode && breakdownId) {
      loadEpisodeScript(selectedEpisode);
    }
  }, [selectedEpisode, breakdownId, loadEpisodeScript]);

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

  // 批量生成状态
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ completed: 0, total: 0 });

  // 批量生成剧本
  const handleBatchGenerate = async () => {
    if (!breakdownId || episodes.length === 0) {
      message.error('没有可生成的剧集');
      setError('没有可生成的剧集');
      return;
    }

    // 筛选待生成的剧集
    const pendingEpisodes = episodes.filter(ep => ep.status === 'pending').map(ep => ep.episode);
    if (pendingEpisodes.length === 0) {
      message.info('所有剧集已生成');
      return;
    }

    try {
      setError(null);
      setBatchGenerating(true);
      setBatchProgress({ completed: 0, total: pendingEpisodes.length });

      const response = await scriptApi.startBatchScripts(breakdownId, pendingEpisodes, {
        novelType
      });

      message.success(`已启动 ${response.data.total} 个剧本生成任务`);

      // 更新列表状态
      setEpisodes(prev => prev.map(ep =>
        pendingEpisodes.includes(ep.episode) ? { ...ep, status: 'generating' } : ep
      ));

      // 开始轮询所有任务状态
      const taskIds = response.data.task_ids;
      const completedTasks = new Set<string>();

      const batchPollInterval = setInterval(async () => {
        let completedCount = 0;

        for (const taskId of taskIds) {
          if (completedTasks.has(taskId)) {
            completedCount++;
            continue;
          }

          try {
            const statusResponse = await scriptApi.getTaskStatus(taskId);
            const status = statusResponse.data;

            if (status.status === TASK_STATUS.COMPLETED) {
              completedTasks.add(taskId);
              completedCount++;
            } else if (status.status === TASK_STATUS.FAILED) {
              completedTasks.add(taskId);
              completedCount++;
              console.error(`任务 ${taskId} 失败:`, status.error_message);
            }
          } catch (err) {
            console.error(`轮询任务 ${taskId} 状态失败:`, err);
          }
        }

        // 更新进度
        setBatchProgress({ completed: completedCount, total: taskIds.length });

        // 所有任务完成
        if (completedCount === taskIds.length) {
          clearInterval(batchPollInterval);
          setBatchGenerating(false);
          message.success(`批量生成完成！共生成 ${taskIds.length} 集剧本`);
          // 刷新剧集列表
          loadEpisodes();
        }
      }, 3000);

    } catch (err: any) {
      setBatchGenerating(false);
      const errorMsg = err.response?.data?.detail || '启动批量生成失败';
      setError(errorMsg);
      message.error(errorMsg);
    }
  };

  // 生成单集剧本
  const handleGenerateScript = async (episodeNumber: number) => {
    if (!breakdownId) {
      message.error('请先完成剧情拆解');
      setError('请先完成剧情拆解');
      return;
    }

    try {
      // 清空之前的日志
      logsRef.current = [];
      setLogs([]);
      setCurrentStep('');
      setProgress(0);
      setError(null);
      setGenerating(episodeNumber);

      const response = await scriptApi.startEpisodeScript(breakdownId, episodeNumber, {
        novelType
      });

      const taskId = response.data.task_id;
      // 设置 taskId 以触发 WebSocket 连接
      setCurrentTaskId(taskId);

      // 添加初始日志
      logsRef.current = [createLog('info', `🎬 开始生成第 ${episodeNumber} 集剧本...`)];
      setLogs([createLog('info', `🎬 开始生成第 ${episodeNumber} 集剧本...`)]);

      message.success(`已启动第 ${episodeNumber} 集剧本生成任务`);

      // 轮询任务状态（仅在 WebSocket 未连接时作为降级方案）
      const pollInterval = setInterval(async () => {
        // 如果 WebSocket 已连接，停止轮询
        if (isConnected) {
          clearInterval(pollInterval);
          return;
        }

        try {
          const statusResponse = await scriptApi.getTaskStatus(taskId);
          const status = statusResponse.data;

          if (status.status === TASK_STATUS.COMPLETED) {
            clearInterval(pollInterval);
            logsRef.current = [...logsRef.current, createLog('success', '🎉 剧本生成完成！')];
            setLogs([...logsRef.current]);
            setGenerating(null);
            message.success(`第 ${episodeNumber} 集剧本生成完成`);
            await loadEpisodeScript(episodeNumber);
          } else if (status.status === TASK_STATUS.FAILED) {
            clearInterval(pollInterval);
            const errorMsg = status.error_message || '剧本生成失败';
            logsRef.current = [...logsRef.current, createLog('error', errorMsg)];
            setLogs([...logsRef.current]);
            setGenerating(null);
            setError(errorMsg);
            message.error(errorMsg);
          } else if (status.current_step) {
            // 更新进度（仅在 WebSocket 未连接时）
            setCurrentStep(status.current_step);
            if (status.progress) {
              setProgress(status.progress);
            }
          }
        } catch {
          // 忽略轮询错误
        }
      }, 3000); // 降级方案使用较长的轮询间隔

      // 更新列表状态
      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber ? { ...ep, status: 'generating' } : ep
      ));

    } catch (err: any) {
      setGenerating(null);
      const errorMsg = err.response?.data?.detail || '启动剧本生成失败';
      setError(errorMsg);
      message.error(errorMsg);
    }
  };

  // 导出剧本
  const handleExport = async () => {
    if (!currentScript?.id) return;
    try {
      setExporting(true);
      const response = await exportApi.exportSingle(currentScript.id, 'pdf');
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${currentScript.title || `第${currentScript.episode_number}集`}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.response?.data?.detail || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  // 审核通过
  const handleApprove = async () => {
    if (!currentScript?.id) return;
    try {
      setApproving(true);
      await scriptApi.approveScript(currentScript.id);
      setCurrentScript({ ...currentScript, status: 'approved' });
      setEpisodes(prev => prev.map(ep =>
        ep.episode === currentScript.episode_number
          ? { ...ep, script: { ...ep.script!, status: 'approved' } }
          : ep
      ));
    } catch (err: any) {
      setError(err.response?.data?.detail || '审核失败');
    } finally {
      setApproving(false);
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

      // 计算总字数（根据内容结构选择计数方式）
      const structureWordCount = Object.values(editedStructure).reduce(
        (sum, s) => sum + (s?.word_count || 0), 0
      );
      const fullScriptWordCount = editedFullScript.length;

      // 如果有完整剧本，使用完整剧本字数；否则使用结构化字数
      const totalWordCount = fullScriptWordCount > 0 ? fullScriptWordCount : structureWordCount;

      // 更新本地状态
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
      // 回滚到原始状态
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

  // 渲染四段式结构
  const renderStructure = () => {
    if (!currentScript?.structure) return null;

    return (
      <div className="space-y-4">
        {(Object.keys(STRUCTURE_LABELS) as Array<keyof typeof STRUCTURE_LABELS>).map((key) => {
          const label = STRUCTURE_LABELS[key];
          const section = currentScript.structure[key];
          const editedSection = editedStructure?.[key];
          const wordCount = editMode ? (editedSection?.word_count || 0) : (section?.word_count || 0);

          return (
            <div key={key} className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
              {/* 段落标题 */}
              <div className={`px-4 py-3 bg-${label.color}-500/10 border-b border-slate-700/50 flex items-center justify-between`}>
                <div className="flex items-center gap-3">
                  <span className={`w-8 h-8 rounded-lg bg-${label.color}-500/20 text-${label.color}-400 flex items-center justify-center font-bold text-lg`}>
                    {label.name}
                  </span>
                  <div>
                    <div className={`text-sm font-bold text-${label.color}-400`}>{label.desc}</div>
                    <div className="text-xs text-slate-500">目标: {label.target}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-mono ${wordCount > 0 ? 'text-slate-300' : 'text-slate-600'}`}>
                    {wordCount} 字
                  </span>
                  {wordCount > 0 && (
                    <CheckCircle2 size={16} className="text-green-500" />
                  )}
                </div>
              </div>

              {/* 段落内容 */}
              <div className="p-4">
                {editMode ? (
                  // 编辑模式 - Textarea
                  <textarea
                    className="w-full h-32 bg-slate-900/50 border border-slate-700 rounded-lg p-3
                               text-slate-300 text-sm leading-relaxed resize-none
                               focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none font-mono"
                    value={editedSection?.content || ''}
                    onChange={(e) => {
                      const newContent = e.target.value;
                      const newWordCount = newContent.trim().length;
                      setEditedStructure(prev => prev ? {
                        ...prev,
                        [key]: { content: newContent, word_count: newWordCount }
                      } : null);
                      setHasUnsavedChanges(true);
                    }}
                    placeholder={`请输入${label.desc}...`}
                  />
                ) : (
                  // 预览模式 - 只读展示
                  section?.content ? (
                    <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
                      {section.content}
                    </div>
                  ) : (
                    <div className="text-sm text-slate-600 italic">暂无内容</div>
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // 无拆解结果时的提示
  if (!batchId) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950">
        <div className="text-center text-slate-500">
          <FileEdit size={64} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">请先选择一个批次</p>
          <p className="text-sm mt-2">完成剧情拆解后即可生成剧本</p>
        </div>
      </div>
    );
  }

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

  {/* Console Logger - 在生成剧本时显示 */}
  {(generating || batchGenerating) && (
    <div className="fixed bottom-4 right-4 z-50">
      {batchGenerating ? (
        // 批量生成进度显示
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-xl w-80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-white">批量生成进度</span>
            <span className="text-xs text-slate-400">{batchProgress.completed}/{batchProgress.total}</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2">
            <div
              className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${(batchProgress.completed / batchProgress.total) * 100}%` }}
            />
          </div>
          <button
            onClick={() => setBatchGenerating(false)}
            className="mt-3 w-full py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 rounded"
          >
            关闭
          </button>
        </div>
      ) : (
        <ConsoleLogger
          logs={logs}
          visible={generating !== null}
          isProcessing={generating !== null}
          progress={progress}
          currentStep={currentStep}
          onClose={() => {}}
        />
      )}
    </div>
  )}

  return (
    <div className="h-full flex gap-0 overflow-hidden bg-slate-950">
      {/* LEFT COLUMN: Controls & List */}
      <div className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl">
        {/* Generator Controls */}
        <div className="p-4 border-b border-slate-800 space-y-3 bg-slate-900/50">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">剧本生成控制</h3>

          <button
            onClick={() => selectedEpisode && handleGenerateScript(selectedEpisode)}
            disabled={!selectedEpisode || generating !== null || !breakdownId}
            className="w-full py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:from-slate-700 disabled:to-slate-700 text-white rounded-lg font-bold shadow-lg shadow-green-900/20 text-sm flex items-center justify-center gap-2 transition-all hover:scale-[1.02] disabled:hover:scale-100"
          >
            {generating ? (
              <>
                <Loader2 size={16} className="animate-spin" /> 生成中...
              </>
            ) : (
              <>
                <Play size={16} /> 生成当前集剧本
              </>
            )}
          </button>

          <button
            onClick={handleBatchGenerate}
            disabled={!breakdownId || generating !== null || batchGenerating}
            className="w-full py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-800/50 text-slate-300 disabled:text-slate-600 border border-slate-700 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {batchGenerating ? (
              <>
                <Loader2 size={14} className="animate-spin" /> 生成中 {batchProgress.completed}/{batchProgress.total}
              </>
            ) : (
              <>
                <Layers size={14} /> 批量生成全部
              </>
            )}
          </button>

          {error && (
            <div className="p-2 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400 flex items-center gap-2">
              <AlertCircle size={14} />
              {error}
            </div>
          )}
        </div>

        {/* Episodes List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="px-4 py-3 flex items-center justify-between text-xs text-slate-500 bg-slate-900/50 sticky top-0 z-10 backdrop-blur border-b border-slate-800">
            <span>剧集列表 ({loading ? '-' : episodes.length})</span>
            <button onClick={loadEpisodes} className="hover:text-white transition-colors">
              <RefreshCw size={12} />
            </button>
          </div>

          {/* 加载中显示骨架屏 */}
          {loading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4 animate-pulse">
                  <div className="flex items-center justify-between mb-2">
                    <div className="h-3 w-16 bg-slate-700/50 rounded" />
                    <div className="h-2 w-12 bg-slate-700/30 rounded" />
                  </div>
                  <div className="h-3 w-3/4 bg-slate-700/30 rounded" />
                </div>
              ))}
            </div>
          ) : episodes.length === 0 ? (
            <div className="text-center py-8 text-slate-600 text-sm">
              <p>暂无剧集</p>
              <p className="text-xs mt-1">请先完成剧情拆解</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/30">
              {episodes.map(ep => (
                <div
                  key={ep.episode}
                  onClick={() => setSelectedEpisode(ep.episode)}
                  className={`px-4 py-4 cursor-pointer transition-all flex items-center justify-between group ${selectedEpisode === ep.episode
                    ? 'bg-cyan-500/10 border-l-2 border-l-cyan-500 shadow-inner'
                    : 'hover:bg-slate-800 border-l-2 border-l-transparent'
                    }`}
                >
                  <div className="min-w-0 pr-2">
                    <div className={`text-[10px] font-bold uppercase transition-colors ${selectedEpisode === ep.episode ? 'text-cyan-400' : 'text-slate-500'}`}>
                      第 {ep.episode} 集
                    </div>
                    <div className={`text-xs truncate mt-1 ${selectedEpisode === ep.episode ? 'text-white font-medium' : 'text-slate-400'}`}>
                      {ep.script?.title || '待生成'}
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-2">
                    {ep.status === 'completed' && (
                      <span className="px-1.5 py-0.5 bg-green-500/10 text-green-500 text-[9px] font-black rounded border border-green-500/20">
                        OK
                      </span>
                    )}
                    {ep.status === 'generating' && (
                      <Loader2 size={12} className="animate-spin text-blue-400" />
                    )}
                    {ep.status === 'pending' && (
                      <ChevronRight size={14} className="text-slate-600 group-hover:text-slate-400" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* MIDDLE COLUMN: Script Content */}
      <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
        {/* Toolbar */}
        <div className="h-14 border-b border-slate-800 bg-slate-900 flex items-center justify-between px-6 shrink-0 z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold text-white tracking-widest uppercase truncate max-w-[300px]">
              {currentScript ? (
                <>
                  第 {currentScript.episode_number} 集
                  <span className="text-slate-500 mx-2">/</span>
                  <span className="text-slate-400">{currentScript.title}</span>
                </>
              ) : selectedEpisode ? (
                `第 ${selectedEpisode} 集`
              ) : (
                '选择剧集'
              )}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            {/* 视图切换 */}
            <div className="flex bg-slate-800 rounded-lg p-0.5 mr-2">
              <button
                onClick={() => setViewMode('structure')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${viewMode === 'structure' ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-400 hover:text-white'}`}
              >
                四段式
              </button>
              <button
                onClick={() => setViewMode('full')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${viewMode === 'full' ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-400 hover:text-white'}`}
              >
                完整剧本
              </button>
            </div>
            {/* 编辑/预览切换 */}
            <div className="flex bg-slate-800 rounded-lg p-0.5 mr-2">
              <button
                onClick={() => setEditMode(false)}
                disabled={!currentScript}
                className={`px-3 py-1 text-xs rounded-md ${!editMode ? 'bg-green-500/20 text-green-400' : 'text-slate-400 hover:text-white'} disabled:opacity-50`}
              >
                <Eye size={14} className="inline mr-1"/> 预览
              </button>
              <button
                onClick={handleEnterEditMode}
                disabled={!currentScript}
                className={`px-3 py-1 text-xs rounded-md ${editMode ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-400 hover:text-white'} disabled:opacity-50`}
              >
                <Edit3 size={14} className="inline mr-1"/> 编辑
              </button>
            </div>
            <button className="p-2 text-slate-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-all" title="Like"><ThumbsUp size={16} /></button>
            <div className="w-px h-4 bg-slate-800 mx-1"></div>
            <button
              onClick={handleExport}
              disabled={!currentScript?.id || exporting}
              className="flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all disabled:opacity-50"
            >
              {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} 导出
            </button>
            {currentScript && currentScript.status !== 'approved' && (
              <button
                onClick={handleApprove}
                disabled={approving}
                className="flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold text-green-400 bg-green-500/10 border border-green-500/30 rounded-lg hover:bg-green-500/20 transition-all ml-2 shadow-sm disabled:opacity-50"
              >
                {approving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} 审核通过
              </button>
            )}
            {currentScript?.status === 'approved' && (
              <span className="ml-2 px-3 py-1.5 text-[11px] font-bold text-green-400 bg-green-500/10 border border-green-500/30 rounded-lg">
                <CheckCircle2 size={14} className="inline mr-1" /> 已通过
              </span>
            )}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8">
          {currentScript ? (
            viewMode === 'structure' ? (
              <div className="max-w-3xl mx-auto">
                {/* 剧本元信息 */}
                <div className="mb-6 p-4 bg-slate-800/30 rounded-xl border border-slate-700/50">
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-white">{currentScript.word_count}</div>
                      <div className="text-xs text-slate-500">总字数</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-cyan-400">{currentScript.scenes?.length || 0}</div>
                      <div className="text-xs text-slate-500">场景数</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-purple-400">{currentScript.characters?.length || 0}</div>
                      <div className="text-xs text-slate-500">角色数</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-amber-400 truncate">{currentScript.hook_type || '-'}</div>
                      <div className="text-xs text-slate-500">悬念类型</div>
                    </div>
                  </div>
                </div>

                {/* 四段式结构 */}
                {renderStructure()}
              </div>
            ) : (
              /* 完整剧本视图 */
              <div className="max-w-3xl mx-auto bg-slate-900 border border-slate-800 shadow-2xl min-h-full p-8 md:p-12 rounded-xl md:rounded-2xl">
                {editMode ? (
                  // 编辑模式 - 可编辑的 Textarea
                  <textarea
                    className="w-full h-full min-h-[800px] bg-slate-900/50 border border-slate-700 rounded-lg p-4
                               text-slate-300 font-mono text-sm leading-relaxed resize-none
                               focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none whitespace-pre-wrap"
                    value={editedFullScript}
                    onChange={(e) => {
                      setEditedFullScript(e.target.value);
                      setHasUnsavedChanges(true);
                    }}
                    placeholder="请输入完整剧本内容..."
                  />
                ) : (
                  // 预览模式 - 只读展示
                  <textarea
                    className="w-full h-full min-h-[800px] bg-transparent resize-none outline-none border-none focus:ring-0 text-slate-300 whitespace-pre-wrap selection:bg-cyan-500/30 scrollbar-hide font-mono text-sm leading-relaxed"
                    value={currentScript.full_script}
                    readOnly
                  />
                )}
              </div>
            )
          ) : selectedEpisode ? (
            /* 未生成剧本 */
            <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4">
              <FileEdit size={64} className="opacity-30" />
              <p className="text-lg font-medium">第 {selectedEpisode} 集剧本待生成</p>
              <button
                onClick={() => handleGenerateScript(selectedEpisode)}
                disabled={generating !== null}
                className="mt-4 px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg font-bold flex items-center gap-2 transition-all hover:scale-105"
              >
                {generating === selectedEpisode ? (
                  <>
                    <Loader2 size={18} className="animate-spin" /> 生成中...
                  </>
                ) : (
                  <>
                    <Play size={18} /> 开始生成
                  </>
                )}
              </button>
            </div>
          ) : (
            /* 未选择剧集 */
            <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4 opacity-30">
              <FileEdit size={64} />
              <p className="text-sm tracking-widest uppercase">请选择一个剧集</p>
            </div>
          )}
        </div>

        {/* Editor Footer */}
        {currentScript && (
          <div className="h-8 bg-slate-900 border-t border-slate-800 flex items-center justify-between px-4 text-[10px] text-slate-500 shrink-0 font-mono">
            <div className="flex items-center gap-4">
              <span>STAT: {currentScript.word_count} WORDS</span>
              <span>ENCODING: UTF-8</span>
            </div>
            <span className="flex items-center gap-1.5 text-green-500"><Save size={10} /> SAVED</span>
          </div>
        )}

        {/* 编辑模式底部操作栏 */}
        {editMode && (
          <div className="h-14 bg-slate-900 border-t border-slate-800 flex items-center justify-between px-6 shrink-0">
            <div className="flex items-center gap-2 text-amber-400 text-sm">
              <AlertCircle size={14} />
              <span>编辑模式 - {hasUnsavedChanges ? '有未保存的更改' : '无未保存的更改'}</span>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleCancelEdit}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-bold text-white bg-gradient-to-r from-cyan-600 to-blue-600 rounded-lg flex items-center gap-2 disabled:opacity-50 hover:from-cyan-500 hover:to-blue-500 transition-all"
              >
                {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                保存更改
              </button>
            </div>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN: QC Report */}
      <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col z-10 shadow-2xl">
        <div className="p-4 border-b border-slate-800 flex items-center gap-2 bg-slate-900/50 backdrop-blur">
          <FileCheck size={16} className="text-green-400" />
          <h3 className="font-bold text-white text-xs uppercase tracking-wider">质量检查报告</h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
          {currentScript?.qa_report ? (
            <>
              {/* 总分 */}
              <div className={`p-4 rounded-xl border ${currentScript.qa_report.status === 'PASS'
                ? 'bg-green-500/5 border-green-500/20'
                : 'bg-red-500/5 border-red-500/20'
                }`}>
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center font-black text-xl ${currentScript.qa_report.status === 'PASS'
                    ? 'bg-green-500 text-white'
                    : 'bg-red-500 text-white'
                    }`}>
                    {currentScript.qa_report.score}
                  </div>
                  <div>
                    <div className={`text-sm font-bold ${currentScript.qa_report.status === 'PASS' ? 'text-green-400' : 'text-red-400'}`}>
                      {currentScript.qa_report.status === 'PASS' ? '质检通过' : '质检未通过'}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{currentScript.qa_report.summary}</div>
                  </div>
                </div>
              </div>

              {/* 各维度评分 */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase">维度评分</h4>
                {Object.entries(currentScript.qa_report.dimensions).map(([key, dim]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">{key}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${dim.score >= 8 ? 'bg-green-500' : dim.score >= 6 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          style={{ width: `${dim.score * 10}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-slate-300 w-6">{dim.score}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* 修正建议 */}
              {currentScript.qa_report.fix_instructions?.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-400 uppercase">修正建议</h4>
                  {currentScript.qa_report.fix_instructions.map((fix, idx) => (
                    <div key={idx} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                      <div className="text-xs text-amber-400 font-medium">{fix.target}</div>
                      <div className="text-xs text-slate-400 mt-1">{fix.issue}</div>
                      <div className="text-xs text-slate-300 mt-2">{fix.suggestion}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : currentScript ? (
            <div className="text-center text-slate-600 mt-20">
              <CheckCircle2 size={48} className="mx-auto mb-4 opacity-20" />
              <p className="text-xs uppercase font-bold">暂无质检报告</p>
            </div>
          ) : (
            <div className="text-center text-slate-600 mt-20 opacity-20">
              <Search size={48} className="mx-auto mb-4" />
              <p className="text-xs uppercase font-bold">等待剧本生成...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScriptTab;
