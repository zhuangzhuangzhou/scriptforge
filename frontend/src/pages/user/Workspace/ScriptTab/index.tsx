import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw, CheckCircle2, Loader2,
  ThumbsUp, Download, FileEdit, Save, FileCheck, Search, AlertCircle,
  Eye, Edit3, Play, XCircle
} from 'lucide-react';
import { message, Modal } from 'antd';
import ConfirmModal from '../../../../components/modals/ConfirmModal';
import ConsoleLogger from '../../../../components/ConsoleLogger';
import { useConsoleLogger } from '../../../../hooks/useConsoleLogger';
import { scriptApi, exportApi, breakdownApi } from '../../../../services/api';
import type { EpisodeScript, ScriptStructure } from '../../../../types';

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
  projectId,
  batchId,
  breakdownId,
  novelType
}) => {
  const [episodes, setEpisodes] = useState<Array<{ episode: number; status: string; breakdownId?: string; batchId?: string; script?: EpisodeScript }>>([]);
  const [selectedEpisode, setSelectedEpisode] = useState<number | null>(null);
  const [currentScript, setCurrentScript] = useState<EpisodeScript | null>(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'structure' | 'full'>('structure');
  const [exporting, setExporting] = useState(false);
  const [approving, setApproving] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [consoleVisible, setConsoleVisible] = useState(false);
  const refreshIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  // Console Logger Hook (监听任务完成事件)
  const {
    logs,
    llmStats,
    addLog,
    clearLogs
  } = useConsoleLogger(currentTaskId, {
    enableWebSocket: true,
    pollInterval: 2000
  });

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

  // 错误弹窗状态
  const [errorModalOpen, setErrorModalOpen] = useState(false);
  const [errorInfo, setErrorInfo] = useState<{ code: string; message: string; suggestion?: string } | null>(null);

  // 解析错误信息（参考 Plot 页面逻辑）
  const parseError = (errorData: any): { code: string; message: string; suggestion?: string } => {
    let errorCode = 'UNKNOWN_ERROR';
    let errorMessage = '操作失败';
    let errorSuggestion = '';

    // 优先使用 error_display（人性化错误信息）
    if (errorData.error_display && typeof errorData.error_display === 'object') {
      errorCode = errorData.error_display.code || errorCode;
      errorMessage = errorData.error_display.description || errorData.error_display.message || errorMessage;
      errorSuggestion = errorData.error_display.suggestion || '';
    } else if (errorData.error_message) {
      // 回退到解析 error_message
      const errorMsg = errorData.error_message;
      try {
        const parsed = typeof errorMsg === 'string' ? JSON.parse(errorMsg) : errorMsg;
        errorCode = parsed.code || errorCode;
        errorMessage = parsed.message || errorMsg;
      } catch {
        errorMessage = errorMsg;
      }
    } else if (errorData.detail) {
      // 直接使用 detail
      errorMessage = errorData.detail;
    }

    return { code: errorCode, message: errorMessage, suggestion: errorSuggestion };
  };

  // 显示错误弹窗
  const showErrorModal = useCallback((error: any, defaultMessage: string = '操作失败') => {
    const parsed = parseError(error.response?.data || error || {});
    setErrorInfo({
      code: parsed.code,
      message: parsed.message || defaultMessage,
      suggestion: parsed.suggestion
    });
    setErrorModalOpen(true);
  }, []);

  // 加载剧集列表（合并已生成的剧本和待生成的拆解结果）
  const loadEpisodes = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);

      // 并行请求：获取剧本和拆解结果
      const [scriptsResponse, breakdownsResponse] = await Promise.all([
        scriptApi.getProjectScripts(projectId),
        breakdownApi.getProjectBreakdowns(projectId)
      ]);

      const scripts = scriptsResponse.data || [];
      const breakdowns = breakdownsResponse.data?.items || breakdownsResponse.data || [];

      // 使用 Map 存储剧集信息（key: episode, value: 剧集数据）
      const episodeMap = new Map<number, any>();

      // 1. 从已生成的剧本中提取剧集
      scripts.forEach((script: any) => {
        episodeMap.set(script.episode_number, {
          episode: script.episode_number,
          status: 'completed',
          breakdownId: script.plot_breakdown_id,
          script: {
            id: script.id,
            episode_number: script.episode_number,
            title: script.title,
            word_count: script.word_count,
            status: script.status,
            qa_status: script.qa_status,
            qa_score: script.qa_score,
            structure: script.content?.structure,
            full_script: script.content?.full_script,
            scenes: script.content?.scenes || [],
            characters: script.content?.characters || [],
            hook_type: script.content?.hook_type,
            qa_report: script.qa_report
          }
        });
      });

      // 2. 从拆解结果中提取待生成的剧集
      breakdowns.forEach((breakdown: any) => {
        if (breakdown.plot_points && Array.isArray(breakdown.plot_points)) {
          // 提取所有唯一的 episode 编号
          const episodes = new Set<number>();
          breakdown.plot_points.forEach((pp: any) => {
            if (pp.episode && pp.episode > 0) {
              episodes.add(pp.episode);
            }
          });

          // 为每个 episode 创建条目（如果尚未生成剧本）
          episodes.forEach(ep => {
            if (!episodeMap.has(ep)) {
              episodeMap.set(ep, {
                episode: ep,
                status: 'pending',
                breakdownId: breakdown.id,
                batchId: breakdown.batch_id
              });
            }
          });
        }
      });

      // 转换为数组并排序
      const episodeList = Array.from(episodeMap.values())
        .sort((a, b) => a.episode - b.episode);

      setEpisodes(episodeList);

      // 默认选中第一集
      if (!selectedEpisodeRef.current && episodeList.length > 0) {
        selectedEpisodeRef.current = true;
        setSelectedEpisode(episodeList[0].episode);
      }
    } catch (err) {
      console.error('加载剧集列表失败:', err);
      showErrorModal(err, '加载剧集列表失败');
    } finally {
      setLoading(false);
    }
  }, [projectId, showErrorModal]);

  // 监听日志变化，检测任务完成
  useEffect(() => {
    if (!currentTaskId || !generating) return;

    // 检查最后一条日志是否是成功或失败
    const lastLog = logs[logs.length - 1];
    if (!lastLog) return;

    if (lastLog.type === 'success' && lastLog.message.includes('完成')) {
      // 任务成功完成
      setGenerating(null);
      setCurrentTaskId(null);
      message.success(`第 ${generating} 集剧本生成完成`);
      // 重新加载剧集列表
      loadEpisodes();
    } else if (lastLog.type === 'error') {
      // 任务失败 - 使用日志中的详细错误信息
      setGenerating(null);
      setCurrentTaskId(null);

      // 从日志中提取详细错误信息
      const errorDetail = lastLog.detail || {};
      const parsed = parseError(errorDetail);
      const errorMsg = parsed.message || '剧本生成失败';

      message.error(errorMsg);

      // 显示错误弹窗
      setErrorInfo({
        code: parsed.code,
        message: errorMsg,
        suggestion: parsed.suggestion
      });
      setErrorModalOpen(true);
    }
  }, [logs, currentTaskId, generating, loadEpisodes]);

  // 使用 ref 来追踪是否需要设置默认集数
  const selectedEpisodeRef = React.useRef(false);

  // 监听 projectId 变化，重置 ref
  React.useEffect(() => {
    selectedEpisodeRef.current = false;
  }, [projectId]);

  useEffect(() => {
    // 在 projectId 存在时加载
    if (projectId) {
      loadEpisodes();
    }
  }, [projectId, loadEpisodes]);

  // 加载单集剧本（从已加载的 episodes 列表中查找）
  const loadEpisodeScript = useCallback(async (episodeNumber: number) => {
    if (!projectId) return;

    // 从已加载的 episodes 列表中查找
    const episode = episodes.find(ep => ep.episode === episodeNumber);
    if (episode?.script) {
      setCurrentScript(episode.script);
    } else {
      setCurrentScript(null);
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

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, []);

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
      showErrorModal(err, '导出失败');
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
      showErrorModal(err, '审核失败');
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

  // 生成单集剧本
  const handleGenerateScript = async (episodeNumber: number) => {
    if (!projectId) {
      message.error('项目信息缺失');
      return;
    }

    // 从 episodes 列表中获取该剧集的 breakdownId
    const episode = episodes.find(ep => ep.episode === episodeNumber);
    if (!episode?.breakdownId) {
      message.error('未找到拆解结果');
      return;
    }

    try {
      setGenerating(episodeNumber);
      clearLogs(); // 清空之前的日志
      setConsoleVisible(true); // 显示控制台

      // 启动剧本生成任务
      const response = await scriptApi.startEpisodeScript(
        episode.breakdownId,
        episodeNumber,
        { novelType }
      );

      const taskId = response.data.task_id;
      setCurrentTaskId(taskId);
      addLog('info', `🎬 已启动第 ${episodeNumber} 集剧本生成任务`);
      addLog('info', `任务 ID: ${taskId.slice(0, 8)}...`);

      // 更新列表状态
      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber ? { ...ep, status: 'generating' } : ep
      ));

      // useConsoleLogger Hook 会自动处理轮询和 WebSocket 连接
      // 任务完成后会通过 useEffect 监听日志变化来处理

    } catch (err: any) {
      setGenerating(null);
      setCurrentTaskId(null);
      const parsed = parseError(err.response?.data || err || {});
      const errorMsg = parsed.message || '启动剧本生成失败';
      addLog('error', `❌ ${errorMsg}`);
      message.error(errorMsg);

      // 如果有建议，显示错误弹窗
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

  // 批量生成剧本
  const handleBatchGenerate = async () => {
    if (!projectId || episodes.length === 0) {
      message.error('没有可生成的剧集');
      return;
    }

    // 筛选待生成的剧集
    const pendingEpisodes = episodes.filter(ep => ep.status === 'pending');
    if (pendingEpisodes.length === 0) {
      message.info('所有剧集已生成');
      return;
    }

    // 按 breakdownId 分组
    const breakdownGroups = new Map<string, number[]>();
    for (const ep of pendingEpisodes) {
      if (ep.breakdownId) {
        if (!breakdownGroups.has(ep.breakdownId)) {
          breakdownGroups.set(ep.breakdownId, []);
        }
        breakdownGroups.get(ep.breakdownId)!.push(ep.episode);
      }
    }

    try {
      clearLogs(); // 清空之前的日志
      setConsoleVisible(true); // 显示控制台

      const allTaskIds: string[] = [];

      for (const [breakdownId, episodeNumbers] of breakdownGroups) {
        const response = await scriptApi.startBatchScripts(
          breakdownId,
          episodeNumbers,
          { novelType }
        );
        allTaskIds.push(...response.data.task_ids);
      }

      addLog('info', `🎬 已启动 ${allTaskIds.length} 个剧本生成任务`);
      addLog('info', `待生成剧集: ${pendingEpisodes.map(ep => ep.episode).join(', ')}`);
      message.success(`已启动 ${allTaskIds.length} 个剧本生成任务`);

      // 更新列表状态
      setEpisodes(prev => prev.map(ep =>
        pendingEpisodes.some(p => p.episode === ep.episode)
          ? { ...ep, status: 'generating' }
          : ep
      ));

      // 定期刷新列表（批量生成时）
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      refreshIntervalRef.current = setInterval(() => {
        loadEpisodes();
      }, 5000);

      // 10 分钟后停止刷新
      setTimeout(() => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
          refreshIntervalRef.current = null;
        }
      }, 600000);

    } catch (err: any) {
      const parsed = parseError(err.response?.data || err || {});
      const errorMsg = parsed.message || '启动批量生成失败';
      addLog('error', `❌ ${errorMsg}`);
      message.error(errorMsg);

      // 如果有建议，显示错误弹窗
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
        footer={[
          <button
            key="close"
            onClick={() => setErrorModalOpen(false)}
            className="px-4 py-2 bg-slate-700:bg-slate- hover600 text-white rounded-lg transition-colors"
          >
            关闭
          </button>
        ]}
        title={
          <div className="flex items-center gap-2 text-red-400">
            <XCircle size={20} />
            <span>操作失败</span>
          </div>
        }
        centered
        width={480}
      >
        <div className="space-y-4">
          {/* 错误信息 */}
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <div className="text-sm text-slate-300">{errorInfo?.message}</div>
          </div>

          {/* 错误代码 */}
          {errorInfo?.code && errorInfo.code !== 'UNKNOWN_ERROR' && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="font-mono">错误代码:</span>
              <span className="font-mono px-2 py-0.5 bg-slate-800 rounded">{errorInfo.code}</span>
            </div>
          )}

          {/* 建议 */}
          {errorInfo?.suggestion && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <div className="text-xs text-amber-400 font-medium mb-1">建议</div>
              <div className="text-sm text-slate-300">{errorInfo.suggestion}</div>
            </div>
          )}
        </div>
      </Modal>

      {/* LEFT COLUMN: Episodes List */}
      <div className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl">
        {/* 生成控制区域 */}
        <div className="p-4 border-b border-slate-800 space-y-3 bg-slate-900/50">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
            剧本生成
          </h3>

          <button
            onClick={() => selectedEpisode && handleGenerateScript(selectedEpisode)}
            disabled={
              !selectedEpisode ||
              generating !== null ||
              episodes.find(ep => ep.episode === selectedEpisode)?.status !== 'pending'
            }
            className="w-full py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:from-slate-700 disabled:to-slate-700 text-white rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all"
          >
            {generating === selectedEpisode ? (
              <>
                <Loader2 size={16} className="animate-spin" /> 生成中...
              </>
            ) : (
              <>
                <Play size={16} /> 生成当前集
              </>
            )}
          </button>

          <button
            onClick={handleBatchGenerate}
            disabled={
              !projectId ||
              generating !== null ||
              episodes.filter(ep => ep.status === 'pending').length === 0
            }
            className="w-full py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-800/50 text-slate-300 disabled:text-slate-600 border border-slate-700 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Play size={14} /> 批量生成全部
          </button>
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
                      {ep.script?.title || `第 ${ep.episode} 集`}
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
                      <span className="px-1.5 py-0.5 bg-amber-500/10 text-amber-500 text-[9px] font-black rounded border border-amber-500/20">
                        待生成
                      </span>
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
          ) : (
            /* 未选择剧集或待生成 */
            !selectedEpisode ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4 opacity-30">
                <FileEdit size={64} />
                <p className="text-sm tracking-widest uppercase">请选择一个剧集</p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4">
                <FileEdit size={64} className="opacity-30" />
                <p className="text-lg font-medium">第 {selectedEpisode} 集剧本待生成</p>
                <button
                  onClick={() => handleGenerateScript(selectedEpisode)}
                  disabled={generating !== null}
                  className="mt-4 px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg font-bold flex items-center gap-2 transition-all hover:scale-105 disabled:opacity-50"
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
            )
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

      {/* Console Logger */}
      <ConsoleLogger
        logs={logs}
        llmStats={llmStats}
        visible={consoleVisible}
        isProcessing={generating !== null}
        onClose={() => setConsoleVisible(false)}
      />
    </div>
  );
};

export default ScriptTab;
