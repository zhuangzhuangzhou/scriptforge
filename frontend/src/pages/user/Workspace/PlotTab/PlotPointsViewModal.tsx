import React from 'react';
import { X, List, CheckCircle, XCircle, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { PlotBreakdown, PlotPoint } from '../../../../types';

interface PlotPointsViewModalProps {
  breakdown: PlotBreakdown | null;
  loading: boolean;
  onClose: () => void;
  onPrevious?: () => void;
  onNext?: () => void;
  hasPrevious?: boolean;
  hasNext?: boolean;
  currentIndex?: number;
  totalCount?: number;
}

const PlotPointsViewModal: React.FC<PlotPointsViewModalProps> = ({
  breakdown,
  loading,
  onClose,
  onPrevious,
  onNext,
  hasPrevious = false,
  hasNext = false,
  currentIndex,
  totalCount
}) => {
  if (!breakdown && !loading) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-7xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col"
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <List className="w-4 h-4 text-cyan-400" />
              历史剧情点详情
              {currentIndex !== undefined && totalCount !== undefined && (
                <span className="text-xs text-slate-500 font-normal">
                  ({totalCount - currentIndex}/{totalCount})
                </span>
              )}
            </h3>
            {breakdown && (
              <div className="flex items-center gap-3 text-xs">
                {/* 质检评分 */}
                {breakdown.qa_score !== undefined && (
                  <>
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">评分:</span>
                      <span className={`text-sm font-black ${
                        breakdown.qa_score >= 80
                          ? 'text-green-400'
                          : breakdown.qa_score >= 60
                          ? 'text-amber-400'
                          : 'text-red-400'
                      }`}>
                        {breakdown.qa_score}
                      </span>
                    </div>
                    <span className="text-slate-600">|</span>
                  </>
                )}
                <span className="text-slate-400">
                  共 <span className="text-cyan-400 font-semibold">{breakdown.plot_points?.length || 0}</span> 个
                </span>
                <span className="text-slate-600">|</span>
                <span className="text-slate-400">
                  已用 <span className="text-green-400 font-semibold">
          {breakdown.plot_points?.filter(p => p.status === 'used').length || 0}
                  </span>
                </span>
                <span className="text-slate-600">|</span>
                <span className="text-slate-400">
                  未用 <span className="text-slate-400 font-semibold">
                    {breakdown.plot_points?.filter(p => p.status === 'unused').length || 0}
                  </span>
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* 上一个/下一个切换按钮 */}
            <button
              onClick={onPrevious}
              disabled={!hasPrevious}
              className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="上一个"
            >
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            </button>
            <button
              onClick={onNext}
              disabled={!hasNext}
              className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="下一个"
            >
              <ChevronRight className="w-4 h-4 text-slate-400" />
            </button>
            <div className="w-px h-4 bg-slate-700 mx-1" />
            <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors">
              <X className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm text-slate-400 mt-3">加载中...</p>
            </div>
          ) : breakdown?.plot_points && breakdown.plot_points.length > 0 ? (
            <div className="bg-slate-800/50 border-b border-slate-700/50">
              <table className="w-full">
                <thead className="bg-slate-900/50 sticky top-0">
                  <tr className="border-b border-slate-700/50">
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider w-16">
                      序号
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider w-20">
                      集数
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider w-40">
                      场景
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider w-32">
                      角色
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      剧情
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider w-24">
                      钩子
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider w-20">
                      状态
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {breakdown.plot_points.map((point: PlotPoint, index: number) => (
                    <tr key={index} className="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-slate-400">{index + 1}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs font-medium text-purple-400">第{point.episode}集</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-slate-300">{point.scene}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-cyan-400">
                          {Array.isArray(point.characters) ? point.characters.join('、') : point.characters}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-slate-300 line-clamp-2">{point.event}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-block px-2 py-0.5 bg-amber-500/20 text-amber-300 text-[10px] rounded border border-amber-500/30">
                          {point.hook_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {point.status === 'used' ? (
                          <CheckCircle className="w-4 h-4 text-green-400 mx-auto" />
                        ) : (
                          <XCircle className="w-4 h-4 text-slate-500 mx-auto" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12">
              <List className="w-8 h-8 text-slate-600" />
              <p className="text-sm text-slate-500 mt-3">暂无剧情点数据</p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default PlotPointsViewModal;
