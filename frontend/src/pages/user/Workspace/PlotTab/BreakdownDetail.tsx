import React from 'react';
import { Layers, Play, Loader2, X, Activity, Swords, Lightbulb, Clock } from 'lucide-react';
import { Batch, PlotBreakdown } from '../../../../types';

interface BreakdownDetailProps {
  selectedBatch: Batch | null;
  breakdownResult: PlotBreakdown | null;
  breakdownLoading: boolean;
  breakdownProgress: number;
  onStartBreakdown?: (batchId: string) => void;
}

const BreakdownDetail: React.FC<BreakdownDetailProps> = ({
  selectedBatch,
  breakdownResult,
  breakdownLoading,
  breakdownProgress,
  onStartBreakdown
}) => {
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
      <div className="space-y-6 max-w-4xl mx-auto p-8">
        {/* Consistency Score */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Activity size={16} className="text-emerald-400" />
              一致性评分
            </h3>
            <div className="text-2xl font-black text-emerald-400">
              {breakdownResult.consistency_score || 0}
              <span className="text-sm text-slate-500 ml-1">/ 100</span>
            </div>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500"
              style={{ width: `${breakdownResult.consistency_score || 0}%` }}
            />
          </div>
        </div>

        {/* Conflicts */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <Swords size={16} className="text-red-400" />
            核心冲突
            <span className="bg-red-500/10 text-red-400 text-[10px] px-2 py-0.5 rounded-full border border-red-500/20">
              {breakdownResult.conflicts?.length || 0}
            </span>
          </h3>
          <div className="space-y-3">
            {breakdownResult.conflicts?.map((conflict, idx) => (
              <div key={idx} className="bg-slate-950 border border-slate-800 rounded-lg p-4">
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

        {/* Plot Hooks */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <Lightbulb size={16} className="text-amber-400" />
            剧情钩子
            <span className="bg-amber-500/10 text-amber-400 text-[10px] px-2 py-0.5 rounded-full border border-amber-500/20">
              {breakdownResult.plot_hooks?.length || 0}
            </span>
          </h3>
          <div className="flex flex-wrap gap-2">
            {breakdownResult.plot_hooks?.map((hook, idx) => (
              <div key={idx} className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                <span className="text-xs text-amber-400">{hook.hook}</span>
                {hook.episode && (
                  <span className="text-[10px] text-amber-600 ml-2">EP.{hook.episode}</span>
                )}
              </div>
            ))}
          </div>
        </div>
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
