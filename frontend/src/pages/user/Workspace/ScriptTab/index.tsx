import React, { useState, useEffect, useCallback } from 'react';
import {
  Layers, RefreshCw, CheckCircle2, Loader2,
  ThumbsUp, Download, FileEdit, Save, FileCheck, Search, AlertCircle,
  Play, ChevronRight
} from 'lucide-react';
import { scriptApi, breakdownApi, exportApi } from '../../../../services/api';
import type { EpisodeScript, PlotPoint } from '../../../../types';

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

  // 加载剧集列表（从拆解结果的 plot_points 中提取）
  const loadEpisodes = useCallback(async () => {
    if (!batchId) return;

    try {
      setLoading(true);
      const response = await breakdownApi.getBreakdownResults(batchId);
      const data = response.data;

      if (data.format_version === 2 && data.plot_points) {
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
        if (episodeList.length > 0 && !selectedEpisode) {
          setSelectedEpisode(episodeList[0].episode);
        }
      }
    } catch (err) {
      console.error('加载剧集列表失败:', err);
      setError('加载剧集列表失败');
    } finally {
      setLoading(false);
    }
  }, [batchId, selectedEpisode]);

  useEffect(() => {
    loadEpisodes();
  }, [loadEpisodes]);

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

  // 生成单集剧本
  const handleGenerateScript = async (episodeNumber: number) => {
    if (!breakdownId) {
      setError('请先完成剧情拆解');
      return;
    }

    try {
      setGenerating(episodeNumber);
      setError(null);

      const response = await scriptApi.startEpisodeScript(breakdownId, episodeNumber, {
        novelType
      });

      const taskId = response.data.task_id;

      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await scriptApi.getTaskStatus(taskId);
          const status = statusResponse.data;

          if (status.status === 'completed') {
            clearInterval(pollInterval);
            setGenerating(null);
            await loadEpisodeScript(episodeNumber);
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            setGenerating(null);
            setError(status.error_message || '剧本生成失败');
          }
        } catch {
          clearInterval(pollInterval);
          setGenerating(null);
          setError('获取任务状态失败');
        }
      }, 2000);

      // 更新列表状态
      setEpisodes(prev => prev.map(ep =>
        ep.episode === episodeNumber ? { ...ep, status: 'generating' } : ep
      ));

    } catch (err: any) {
      setGenerating(null);
      setError(err.response?.data?.detail || '启动剧本生成失败');
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

  // 渲染四段式结构
  const renderStructure = () => {
    if (!currentScript?.structure) return null;

    return (
      <div className="space-y-4">
        {(Object.keys(STRUCTURE_LABELS) as Array<keyof typeof STRUCTURE_LABELS>).map((key) => {
          const label = STRUCTURE_LABELS[key];
          const section = currentScript.structure[key];
          const wordCount = section?.word_count || 0;

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
                {section?.content ? (
                  <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
                    {section.content}
                  </div>
                ) : (
                  <div className="text-sm text-slate-600 italic">暂无内容</div>
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
            disabled={!breakdownId || generating !== null}
            className="w-full py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-800/50 text-slate-300 disabled:text-slate-600 border border-slate-700 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Layers size={14} /> 批量生成全部
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
                <textarea
                  className="w-full h-full min-h-[800px] bg-transparent resize-none outline-none border-none focus:ring-0 text-slate-300 whitespace-pre-wrap selection:bg-cyan-500/30 scrollbar-hide font-mono text-sm leading-relaxed"
                  value={currentScript.full_script}
                  readOnly
                />
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
