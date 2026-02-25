import React, { useState } from 'react';
import {
  FileEdit, Loader2, Play, Eye as EyeIcon, Edit3, Download,
  History, BarChart3, CheckCircle, XCircle, Clock, AlertCircle,
  Save, X as XIcon
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { EpisodeScript, ScriptStructure } from '../../../../types';

interface ScriptDetailProps {
  currentScript: EpisodeScript | null;
  selectedEpisode: number | null;
  onGenerateScript: (episode: number) => void;
  isGenerating: boolean;
  progress: number;
  onViewHistory?: () => void;
  onExport?: () => void;
  onEdit?: () => void;
  editMode?: boolean;
  onSaveEdit?: () => void;
  onCancelEdit?: () => void;
  hasUnsavedChanges?: boolean;
  editedStructure?: ScriptStructure | null;
  editedFullScript?: string;
  onStructureChange?: (key: keyof ScriptStructure, content: string) => void;
  onFullScriptChange?: (content: string) => void;
}

// 四段式结构标签
const STRUCTURE_LABELS = {
  opening: { name: '起', desc: '开场冲突', color: 'cyan', target: '100-150字' },
  development: { name: '承', desc: '推进发展', color: 'blue', target: '150-200字' },
  climax: { name: '转', desc: '反转高潮', color: 'purple', target: '200-250字' },
  hook: { name: '钩', desc: '悬念结尾', color: 'amber', target: '100-150字' }
} as const;

const ScriptDetail: React.FC<ScriptDetailProps> = ({
  currentScript,
  selectedEpisode,
  onGenerateScript,
  isGenerating,
  progress,
  onViewHistory,
  onExport,
  onEdit,
  editMode = false,
  onSaveEdit,
  onCancelEdit,
  hasUnsavedChanges = false,
  editedStructure,
  editedFullScript,
  onStructureChange,
  onFullScriptChange
}) => {
  const [viewMode, setViewMode] = useState<'structure' | 'full'>('structure');

  // 未选择剧集
  if (!selectedEpisode) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-700 gap-4 opacity-30">
        <FileEdit size={64} />
        <p className="text-sm tracking-widest uppercase font-black">选择一个剧集</p>
      </div>
    );
  }

  // 生成中状态
  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
        <div className="w-20 h-20 rounded-2xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 animate-pulse">
          <Loader2 size={32} className="text-cyan-400 animate-spin" />
        </div>
        <p className="text-sm font-bold text-cyan-400">AI 正在生成剧本...</p>
        <div className="w-64">
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-600 text-center mt-2">{progress}%</p>
        </div>
      </div>
    );
  }

  // 待生成状态
  if (!currentScript) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
        <div className="w-20 h-20 rounded-2xl bg-slate-800/50 flex items-center justify-center border border-slate-700">
          <Play size={32} className="text-slate-500" />
        </div>
        <p className="text-sm font-bold">点击"开始生成"创建剧本</p>
        <p className="text-xs text-slate-700">将为第 {selectedEpisode} 集生成剧本</p>
        <button
          onClick={() => onGenerateScript(selectedEpisode)}
          className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-sm rounded-lg border border-cyan-500/30 transition-colors flex items-center gap-2"
        >
          <Play size={16} />
          开始生成
        </button>
      </div>
    );
  }

  // 剧本内容展示
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 标题栏 */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-200">{currentScript.title}</h2>
          <div className="flex items-center gap-2">
            {/* 编辑模式提示 */}
            {editMode && (
              <div className="flex items-center gap-2 text-amber-400 text-xs bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-1.5">
                <AlertCircle size={14} />
                <span>{hasUnsavedChanges ? '有未保存的更改' : '编辑模式'}</span>
              </div>
            )}

            {/* 编辑模式操作按钮 */}
            {editMode && (
              <>
                <button
                  onClick={onCancelEdit}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={onSaveEdit}
                  disabled={!hasUnsavedChanges}
                  className="px-3 py-1.5 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-medium rounded-lg border border-cyan-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  <Save size={14} />
                  保存
                </button>
              </>
            )}

            {/* 视图切换 */}
            {!editMode && (
              <div className="bg-slate-800 rounded-lg p-0.5 flex items-center gap-0.5">
                <button
                  onClick={() => setViewMode('structure')}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    viewMode === 'structure'
                      ? 'bg-cyan-500/20 text-cyan-300'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
           >
                  四段式
                </button>
                <button
                  onClick={() => setViewMode('full')}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    viewMode === 'full'
                      ? 'bg-cyan-500/20 text-cyan-300'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  完整剧本
                </button>
              </div>
            )}

            {/* 操作按钮 */}
            {!editMode && (
              <>
                {onEdit && (
                  <button
                    onClick={onEdit}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
                    title="编辑"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                )}
                {onExport && (
                  <button
                    onClick={onExport}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
                    title="导出"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                )}
                {onViewHistory && (
                  <button
                    onClick={onViewHistory}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
                    title="历史记录"
                  >
                    <History className="w-4 h-4" />
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* 剧本信息卡片（左右结构） */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <div className="flex items-center justify-between gap-6">
            {/* 左侧：字数统计 */}
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-xs text-slate-400 mb-1">总字数</p>
                <p className="text-2xl font-bold text-white">{currentScript.word_count || 0}</p>
              </div>
              <div className="w-px h-10 bg-slate-700/50"></div>
              <div className="text-center">
                <p className="text-xs text-slate-400 mb-1">场景数</p>
                <p className="text-2xl font-bold text-cyan-400">{currentScript.scenes?.length || 0}</p>
              </div>
              <div className="w-px h-10 bg-slate-700/50"></div>
              <div className="text-center">
                <p className="text-xs text-slate-400 mb-1">角色数</p>
                <p className="text-2xl font-bold text-purple-400">{currentScript.characters?.length || 0}</p>
              </div>
              <div className="w-px h-10 bg-slate-700/50"></div>
              <div className="text-center">
                <p className="text-xs text-slate-400 mb-1">悬念类型</p>
                <p className="text-lg font-bold text-amber-400 truncate">{currentScript.hook_type || '-'}</p>
              </div>
            </div>

            {/* 右侧：质检信息 */}
            {currentScript.qa_status && (
              <>
                <div className="w-px h-12 bg-slate-700/50"></div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-purple-400" />
                    <span className="text-sm font-semibold text-slate-300">质检</span>
                  </div>
                  {currentScript.qa_score !== undefined && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-slate-400">分数:</span>
                      <span className={`text-lg font-black ${
                        currentScript.qa_score >= 80
                          ? 'text-green-400'
                          : currentScript.qa_score >= 60
                          ? 'text-yellow-400'
                          : 'text-red-400'
                      }`}>
                        {currentScript.qa_score}
                      </span>
                    </div>
                  )}
                  <div className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                    currentScript.qa_status === 'PASS'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : currentScript.qa_status === 'FAIL'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                  }`}>
                    {currentScript.qa_status === 'PASS' && <CheckCircle className="w-3 h-3" />}
                    {currentScript.qa_status === 'FAIL' && <XCircle className="w-3 h-3" />}
                    {currentScript.qa_status === 'pending' && <Clock className="w-3 h-3" />}
                    {currentScript.qa_status === 'PASS' ? '通过' : currentScript.qa_status === 'FAIL' ? '未通过' : '待质检'}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 四段式结构视图 */}
        {viewMode === 'structure' && currentScript.structure && (
          <div className="space-y-2">
            {(Object.keys(STRUCTURE_LABELS) as Array<keyof typeof STRUCTURE_LABELS>).map((key) => {
              const label = STRUCTURE_LABELS[key];
              const content = editMode && editedStructure
                ? editedStructure[key as keyof ScriptStructure]
                : currentScript.structure?.[key as keyof ScriptStructure];
              const wordCount = content?.word_count || 0;

              return (
                <div
                  key={key}
                  className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-black text-${label.color}-400`}>
                        {label.name}
                      </span>
                      <span className="text-xs text-slate-400">{label.desc}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-500">{label.target}</span>
                      <span className={`font-semibold ${
                        wordCount >= 100 && wordCount <= 250
                          ? 'text-green-400'
                          : 'text-amber-400'
                      }`}>
                        {wordCount} 字
                      </span>
                    </div>
                  </div>
                  {editMode ? (
                    <textarea
                      value={content?.content || ''}
                      onChange={(e) => onStructureChange?.(key as keyof ScriptStructure, e.target.value)}
                      className="w-full min-h-[120px] bg-slate-900/50 text-slate-300 text-sm leading-relaxed p-3 rounded-lg border border-slate-700 focus:border-cyan-500 focus:outline-none resize-y"
                      placeholder="输入内容..."
                    />
                  ) : (
                    <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {content?.content || '暂无内容'}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 完整剧本视图 */}
        {viewMode === 'full' && (
          <div className="bg-slate-900/30 p-4 rounded-lg border border-slate-800/50">
            {editMode ? (
              <textarea
                value={editedFullScript || currentScript.full_script || ''}
                onChange={(e) => onFullScriptChange?.(e.target.value)}
                className="w-full min-h-[500px] bg-slate-900/50 text-slate-300 text-sm leading-relaxed p-3 rounded-lg border border-slate-700 focus:border-cyan-500 focus:outline-none resize-y font-sans"
                placeholder="输入完整剧本..."
              />
            ) : (
              <pre className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap font-sans">
                {currentScript.full_script || '暂无内容'}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ScriptDetail;
