import React, { useState } from 'react';
import {
  Layers, Play, Loader2, X, Activity, Swords, Lightbulb, Clock,
  Film, ChevronDown, Users, MapPin, Heart, Table as TableIcon, Grid
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Batch, PlotBreakdown, Episode } from '../../../../types';

interface BreakdownDetailProps {
  selectedBatch: Batch | null;
  breakdownResult: PlotBreakdown | null;
  breakdownLoading: boolean;
  breakdownProgress: number;
  onStartBreakdown?: (batchId: string) => void;
}

interface EpisodeCardProps {
  episode: Episode;
  isExpanded: boolean;
  onToggle: () => void;
}

// 新增：表格行组件
interface EpisodeTableRowProps {
  episode: Episode;
  status: 'used' | 'unused';
  scriptLink?: string;
  onStatusChange?: (episodeId: number, status: 'used' | 'unused') => void;
}

const EpisodeTableRow: React.FC<EpisodeTableRowProps> = ({
  episode,
  status,
  scriptLink,
  onStatusChange
}) => {
  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-800/30 transition-colors">
      <td className="px-4 py-3 text-center">
        <span className="text-cyan-400 font-semibold">{episode.episode_number}</span>
      </td>
      <td className="px-4 py-3">
        <span className="text-slate-300 text-sm">
          第 {episode.chapter_range[0]}-{episode.chapter_range[1]} 章
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="text-sm text-slate-300 line-clamp-2">
          {episode.main_conflict}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="text-sm text-slate-300 line-clamp-2">
          {episode.plot_hooks && episode.plot_hooks.length > 0
            ? episode.plot_hooks[0].hook
            : '-'}
        </div>
      </td>
      <td className="px-4 py-3 text-center">
        <button
          onClick={() => onStatusChange?.(episode.episode_number, status === 'used' ? 'unused' : 'used')}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            status === 'used'
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-slate-600/20 text-slate-400 border border-slate-600/30'
          }`}
        >
          {status === 'used' ? '已用' : '未用'}
        </button>
      </td>
      <td className="px-4 py-3 text-center">
        {scriptLink ? (
          <a
            href={scriptLink}
            className="text-cyan-400 hover:text-cyan-300 text-sm underline"
          >
            Episode-{String(episode.episode_number).padStart(3, '0')}
          </a>
        ) : (
          <span className="text-slate-500 text-sm">未生成</span>
        )}
      </td>
    </tr>
  );
};

const EpisodeCard: React.FC<EpisodeCardProps> = ({ episode, isExpanded, onToggle }) => {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      {/* 标题栏 - 可点击折叠/展开 */}
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-cyan-400">
            第{episode.episode_number}集 - {episode.title}
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            主要冲突：{episode.main_conflict}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            章节范围：第{episode.chapter_range[0]}-{episode.chapter_range[1]}章
          </p>
        </div>
        <ChevronDown
          className={`w-5 h-5 text-slate-400 transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </div>

      {/* 详情区域 - 可折叠 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-4 space-y-4 overflow-hidden"
          >
            {/* 关键场景 */}
            {episode.key_scenes && episode.key_scenes.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-purple-400 flex items-center gap-2 mb-2">
                  <Film className="w-4 h-4" />
                  关键场景
                </h4>
                <div className="flex flex-wrap gap-2">
                  {episode.key_scenes.map((scene, idx) => (
                    <span key={idx} className="text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded border border-purple-500/30">
                      {scene}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 冲突点 */}
            {episode.conflicts && episode.conflicts.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-red-400 flex items-center gap-2 mb-2">
                  <Swords className="w-4 h-4" />
                  冲突点 ({episode.conflicts.length})
                </h4>
                <div className="space-y-2">
                  {episode.conflicts.map((conflict, idx) => (
                    <div key={idx} className="bg-slate-900/50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-slate-200">{conflict.title}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-500">紧张度</span>
                          <div className="w-16 bg-slate-700 rounded-full h-1.5">
                            <div
                              className="bg-gradient-to-r from-yellow-500 to-red-500 h-1.5 rounded-full"
                              style={{ width: `${conflict.tension}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-red-400 font-mono">{conflict.tension}</span>
                        </div>
                      </div>
                      {conflict.description && (
                        <p className="text-xs text-slate-400">{conflict.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 剧情钩子 */}
            {episode.plot_hooks && episode.plot_hooks.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-amber-400 flex items-center gap-2 mb-2">
                  <Lightbulb className="w-4 h-4" />
                  剧情钩子 ({episode.plot_hooks.length})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {episode.plot_hooks.map((hook, idx) => (
                    <div key={idx} className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                      <span className="text-xs text-amber-400">{hook.hook}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 角色 */}
            {episode.characters && episode.characters.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-cyan-400 flex items-center gap-2 mb-2">
                  <Users className="w-4 h-4" />
                  角色 ({episode.characters.length})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {episode.characters.map((char, idx) => (
                    <div key={idx} className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-cyan-300">{char.name}</span>
                        {char.role && (
                          <span className="text-xs text-cyan-500">{char.role}</span>
                        )}
                      </div>
                      {char.description && (
                        <p className="text-xs text-slate-400 mt-1">{char.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 场景 */}
            {episode.scenes && episode.scenes.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-purple-400 flex items-center gap-2 mb-2">
                  <MapPin className="w-4 h-4" />
                  场景 ({episode.scenes.length})
                </h4>
                <div className="space-y-2">
                  {episode.scenes.map((scene, idx) => (
                    <div key={idx} className="bg-slate-900/50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-slate-200">{scene.title}</span>
                        {scene.location && (
                          <span className="text-xs text-slate-500">{scene.location}</span>
                        )}
                      </div>
                      {scene.description && (
                        <p className="text-xs text-slate-400">{scene.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 情感 */}
            {episode.emotions && episode.emotions.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-pink-400 flex items-center gap-2 mb-2">
                  <Heart className="w-4 h-4" />
                  情感 ({episode.emotions.length})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {episode.emotions.map((emotion, idx) => (
                    <div key={idx} className="bg-pink-500/10 border border-pink-500/20 rounded-lg px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-pink-300">{emotion.emotion}</span>
                        <span className="text-xs text-pink-500">强度: {emotion.intensity}/10</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const BreakdownDetail: React.FC<BreakdownDetailProps> = ({
  selectedBatch,
  breakdownResult,
  breakdownLoading,
  breakdownProgress,
  onStartBreakdown
}) => {
  const [expandedEpisodes, setExpandedEpisodes] = useState<Set<number>>(new Set([1])); // 默认展开第一集
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card'); // 视图模式
  const [episodeStatus, setEpisodeStatus] = useState<Record<number, 'used' | 'unused'>>({}); // 剧集状态

  const toggleEpisode = (episodeNumber: number) => {
    setExpandedEpisodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(episodeNumber)) {
        newSet.delete(episodeNumber);
      } else {
        newSet.add(episodeNumber);
      }
      return newSet;
    });
  };

  const handleStatusChange = (episodeId: number, status: 'used' | 'unused') => {
    setEpisodeStatus(prev => ({
      ...prev,
      [episodeId]: status
    }));
    // TODO: 调用 API 更新状态
  };

  // 未选择批次
  if (!selectedBatch) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-700 gap-4 opacity-30">
        <Layers size={64} />
        <p className="text-sm tracking-widest uppercase font-black">Select a batch</p>
      </div>
    );
  }

  // 待拆解状态
  if (selectedBatch.breakdown_status === 'pending') {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
        <div className="w-20 h-20 rounded-2xl bg-slate-800/50 flex items-center justify-center border border-slate-700">
          <Play size={32} className="text-slate-500" />
        </div>
        <p className="text-sm font-bold">点击"开始拆解"启动 AI 分析</p>
        <p className="text-xs text-slate-700">将分析第 {selectedBatch.start_chapter}-{selectedBatch.end_chapter} 章的剧情结构</p>
      </div>
    );
  }

  // 排队状态
  if (selectedBatch.breakdown_status === 'queued') {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
        <div className="w-20 h-20 rounded-2xl bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
          <Clock size={32} className="text-amber-500" />
        </div>
        <p className="text-sm font-bold text-amber-500">任务已排队</p>
        <p className="text-xs text-slate-700">等待执行中...</p>
      </div>
    );
  }

  // 拆解中状态
  if (selectedBatch.breakdown_status === 'processing') {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
        <div className="w-20 h-20 rounded-2xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 animate-pulse">
          <Loader2 size={32} className="text-cyan-400 animate-spin" />
        </div>
        <p className="text-sm font-bold text-cyan-400">AI 正在分析剧情...</p>
        <div className="w-64">
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
              style={{ width: `${breakdownProgress}%` }}
            />
          </div>
          <p className="text-xs text-slate-600 text-center mt-2">{breakdownProgress}%</p>
        </div>
      </div>
    );
  }

  // 加载结果中
  if (breakdownLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <Loader2 size={32} className="animate-spin text-cyan-500" />
        <p className="text-xs text-slate-500 mt-3">加载拆解结果...</p>
      </div>
    );
  }

  // 拆解完成但无结果（数据异常）
  if (selectedBatch.breakdown_status === 'completed' && !breakdownResult) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
        <div className="w-20 h-20 rounded-2xl bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
          <Activity size={32} className="text-amber-400" />
        </div>
        <p className="text-sm font-bold text-amber-400">拆解结果加载异常</p>
        <p className="text-xs text-slate-700">批次状态已完成，但未找到拆解结果</p>
        <p className="text-xs text-slate-600 mb-2">可能是数据同步延迟或系统异常</p>
        <div className="flex gap-3">
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg transition-colors border border-slate-700"
          >
            刷新页面
          </button>
          {onStartBreakdown && (
            <button
              onClick={() => onStartBreakdown(selectedBatch.id)}
              className="px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs rounded-lg transition-colors border border-amber-500/30"
            >
              重新拆解
            </button>
          )}
        </div>
      </div>
    );
  }

  // 拆解完成且有结果
  if (selectedBatch.breakdown_status === 'completed' && breakdownResult) {
    return (
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* 视图切换按钮 */}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-200">拆解结果</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('card')}
              className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                viewMode === 'card'
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-700/50'
              }`}
            >
              <Grid className="w-4 h-4" />
              卡片视图
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                viewMode === 'table'
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-700/50'
              }`}
            >
              <TableIcon className="w-4 h-4" />
              表格视图
            </button>
          </div>
        </div>

        {/* 一致性评分卡片 */}
        {breakdownResult.consistency_score !== undefined && breakdownResult.consistency_score !== null && (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2">
                <Activity className="w-5 h-5" />
                一致性评分
              </h3>
              <div className="text-2xl font-black text-emerald-400">
                {breakdownResult.consistency_score}
                <span className="text-sm text-slate-500 ml-1">/ 100</span>
              </div>
            </div>
            <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                style={{ width: `${breakdownResult.consistency_score}%` }}
              />
            </div>
          </div>
        )}

        {/* 剧集规划概览卡片 */}
        {breakdownResult.episodes && breakdownResult.episodes.length > 0 && (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-purple-400 flex items-center gap-2 mb-3">
              <Film className="w-5 h-5" />
              剧集规划
            </h3>
            <p className="text-slate-300">
              共 <span className="text-cyan-400 font-semibold">{breakdownResult.episodes.length}</span> 集
            </p>
            {breakdownResult.episodes.length > 0 && (
              <p className="text-sm text-slate-400 mt-1">
                涵盖第{breakdownResult.episodes[0]?.chapter_range[0]}-
                {breakdownResult.episodes[breakdownResult.episodes.length - 1]?.chapter_range[1]}章
              </p>
            )}
          </div>
        )}

        {/* 剧集详情 - 根据视图模式切换 */}
        {breakdownResult.episodes && breakdownResult.episodes.length > 0 ? (
          viewMode === 'card' ? (
            // 卡片视图
            breakdownResult.episodes.map((episode) => (
              <EpisodeCard
                key={episode.episode_number}
                episode={episode}
                isExpanded={expandedEpisodes.has(episode.episode_number)}
                onToggle={() => toggleEpisode(episode.episode_number)}
              />
            ))
          ) : (
            // 表格视图
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-900/50">
                  <tr className="border-b border-slate-700/50">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      原文章节
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      核心冲突
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      情绪钩子
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      状态
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      对应剧本
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {breakdownResult.episodes.map((episode) => (
                    <EpisodeTableRow
                      key={episode.episode_number}
                      episode={episode}
                      status={episodeStatus[episode.episode_number] || 'unused'}
                      scriptLink={undefined} // TODO: 从后端获取剧本链接
                      onStatusChange={handleStatusChange}
                    />
                  ))}
                </tbody>
              </table>

              {/* 表格视图提示 */}
              <div className="px-4 py-3 bg-slate-900/30 border-t border-slate-700/50">
                <p className="text-xs text-slate-500">
                  💡 提示：点击状态可以切换"已用/未用"标记。生成剧本后会自动显示链接。
                </p>
              </div>
            </div>
          )
        ) : (
          /* 无剧集规划时显示传统视图 */
          <>
            {/* 核心冲突 */}
            {breakdownResult.conflicts && breakdownResult.conflicts.length > 0 && (
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-red-400 flex items-center gap-2 mb-4">
                  <Swords className="w-5 h-5" />
                  核心冲突
                  <span className="bg-red-500/10 text-red-400 text-xs px-2 py-0.5 rounded-full border border-red-500/20">
                    {breakdownResult.conflicts.length}
                  </span>
                </h3>
                <div className="space-y-3">
                  {breakdownResult.conflicts.map((conflict, idx) => (
                    <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-bold text-white">{conflict.title}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-500">紧张度</span>
                          <div className="w-16 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-yellow-500 to-red-500"
                              style={{ width: `${conflict.tension}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-red-400 font-mono">{conflict.tension}</span>
                        </div>
                      </div>
                      {conflict.description && (
                        <p className="text-xs text-slate-400">{conflict.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 剧情钩子 */}
            {breakdownResult.plot_hooks && breakdownResult.plot_hooks.length > 0 && (
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-amber-400 flex items-center gap-2 mb-4">
                  <Lightbulb className="w-5 h-5" />
                  剧情钩子
                  <span className="bg-amber-500/10 text-amber-400 text-xs px-2 py-0.5 rounded-full border border-amber-500/20">
                    {breakdownResult.plot_hooks.length}
                  </span>
                </h3>
                <div className="flex flex-wrap gap-2">
                  {breakdownResult.plot_hooks.map((hook, idx) => (
                    <div key={idx} className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                      <span className="text-xs text-amber-400">{hook.hook}</span>
                      {hook.episode && (
                        <span className="text-[10px] text-amber-600 ml-2">EP.{hook.episode}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // 失败状态
  return (
    <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
      <div className="w-20 h-20 rounded-2xl bg-red-500/10 flex items-center justify-center border border-red-500/20">
        <X size={32} className="text-red-400" />
      </div>
      <p className="text-sm font-bold text-red-400">拆解失败</p>
      <p className="text-xs text-slate-700">请点击"重新拆解"重试</p>
    </div>
  );
};

export default BreakdownDetail;
