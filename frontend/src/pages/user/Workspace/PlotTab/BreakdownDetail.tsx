import React, { useState, useEffect } from 'react';
import {
  Layers, Play, Loader2, X, Activity, Swords, Lightbulb, Clock,
  Film, Users, CheckCircle, XCircle, BarChart3, List, History
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Batch, PlotBreakdown, PlotPoint, QAReport } from '../../../../types';
import { BATCH_STATUS, TASK_STATUS } from '../../../../constants/status';
import { breakdownApi } from '../../../../services/api';
import BreakdownDetailModal from './BreakdownDetailModal';

interface BreakdownDetailProps {
  selectedBatch: Batch | null;
  breakdownResult: PlotBreakdown | null;
  breakdownLoading: boolean;
  breakdownProgress: number;
  onStartBreakdown?: (batchId: string) => void;
  taskId?: string | null;
  onStopBreakdown?: () => void;
  onViewMethod?: (methodId: string) => void;
}

// 剧情点表格行组件
interface PlotPointTableRowProps {
  point: PlotPoint;
  onStatusChange?: (pointId: number, status: 'used' | 'unused') => void;
}

// 质检报告弹窗组件
interface QAReportModalProps {
  report: QAReport | null | undefined;
  onClose: () => void;
}

const QAReportModal: React.FC<QAReportModalProps> = ({ report, onClose }) => {
  if (!report) return null;

  // 兼容数组和对象两种 dimensions 格式
  const dimensionsArray = Array.isArray(report.dimensions)
    ? report.dimensions
    : report.dimensions && typeof report.dimensions === 'object'
    ? Object.entries(report.dimensions).map(([key, value]) => ({ name: key, ...value }))
    : [];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl"
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            质检报告详情
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-4 overflow-y-auto max-h-[60vh] space-y-4">
          {/* 整体评分 */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  report.status === 'PASS'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  <span className="text-xl font-black">{report.score}</span>
                </div>
                <div>
                  <p className="text-xs text-slate-400">质检总分</p>
                  <p className="text-[10px] text-slate-500">满分 100 分</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* 自动修正次数 */}
                {report.auto_fix_attempts !== undefined && report.auto_fix_attempts > 0 && (
                  <div className={`px-2 py-1 rounded-full text-[10px] font-medium ${
                    report.auto_fix_success
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}>
                    已修正 {report.auto_fix_attempts} 次
                  </div>
                )}
                <div className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                  report.status === 'PASS'
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {report.status === 'PASS' ? '质检通过' : '质检未通过'}
                </div>
              </div>
            </div>
          </div>

          {/* 各维度得分 */}
          {dimensionsArray.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                <BarChart3 className="w-3.5 h-3.5" />
                各维度评分
              </h4>
              <div className="grid gap-3">
                {dimensionsArray.map((dimension: any, idx: number) => (
                  <div key={idx} className="bg-slate-800/30 border border-slate-700/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-slate-200">{dimension.name}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                          dimension.passed || dimension.pass
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {dimension.passed || dimension.pass ? '通过' : '未通过'}
                        </span>
                        <span className="text-sm font-bold text-cyan-400">{dimension.score}</span>
                      </div>
                    </div>
                    {/* 进度条 */}
                    <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          dimension.score >= 80
                            ? 'bg-green-500'
                            : dimension.score >= 60
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${dimension.score}%` }}
                      />
                    </div>
                    {/* 详情 */}
                    {dimension.details && (
                      <p className="mt-2 text-[10px] text-slate-400">{dimension.details}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 问题列表 */}
          {report.issues && report.issues.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                <XCircle className="w-3.5 h-3.5 text-red-400" />
                问题列表
              </h4>
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 space-y-1.5">
                {report.issues.map((issue: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-red-300">
                    <span className="text-red-500 font-mono text-[10px] mt-0.5">{idx + 1}.</span>
                    <span>{typeof issue === 'string' ? issue : issue.description || JSON.stringify(issue)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 改进建议 */}
          {report.suggestions && report.suggestions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                改进建议
              </h4>
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 space-y-1.5">
                {report.suggestions.map((suggestion: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-amber-300">
                    <span className="text-amber-500 font-mono text-[10px] mt-0.5">{idx + 1}.</span>
                    <span>{typeof suggestion === 'string' ? suggestion : suggestion.action || JSON.stringify(suggestion)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 修复指引 */}
          {report.fix_instructions && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-blue-400 flex items-center gap-2 mb-2">
                <CheckCircle className="w-3.5 h-3.5" />
                修复指引
              </h4>
              {Array.isArray(report.fix_instructions) ? (
                <div className="space-y-1.5">
                  {report.fix_instructions.map((inst: any, idx: number) => (
                    <div key={idx} className="text-xs text-blue-300">
                      <span className="font-mono text-[10px] text-blue-500">{idx + 1}.</span>{' '}
                      {typeof inst === 'string' ? inst : inst.action || JSON.stringify(inst)}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-blue-300 leading-relaxed">{report.fix_instructions}</p>
              )}
            </div>
          )}
        </div>

        {/* 底部 */}
        <div className="flex justify-end gap-3 p-4 border-t border-slate-700 bg-slate-900/50">
          <button
            onClick={onClose}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700 transition-colors"
          >
            关闭
          </button>
        </div>
      </motion.div>
    </div>
  );
};

// 剧情点表格行组件
const PlotPointTableRow: React.FC<PlotPointTableRowProps> = ({
  point
}) => {
  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-800/30 transition-colors">
      {/* 序号 */}
      <td className="px-3 py-3.5 text-center">
        <span className="text-cyan-400 font-semibold text-xs">{point.id}</span>
      </td>
      {/* 集数 */}
      <td className="px-3 py-3.5 text-center">
        <span className="text-xs text-slate-300">第 {point.episode} 集</span>
      </td>
      {/* 场景 */}
      <td className="px-3 py-3.5">
        <span className="text-xs text-slate-300 line-clamp-2">{point.scene}</span>
      </td>
      {/* 角色 */}
      <td className="px-3 py-3.5">
        <div className="flex flex-wrap gap-1 max-w-[150px]">
          {point.characters && point.characters.length > 0 ? (
            point.characters.map((char, idx) => (
              <span key={idx} className="text-[10px] px-1.5 py-0.5 bg-cyan-500/20 text-cyan-300 rounded border border-cyan-500/30 truncate max-w-[80px]" title={char}>
                {char}
              </span>
            ))
          ) : (
            <span className="text-slate-500 text-xs">-</span>
          )}
        </div>
      </td>
      {/* 事件 */}
      <td className="px-3 py-3.5">
        <span className="text-xs text-slate-300 line-clamp-2">{point.event}</span>
      </td>
      {/* 钩子类型 */}
      <td className="px-3 py-3.5">
        <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/20 text-amber-300 rounded border border-amber-500/30">
          {point.hook_type}
        </span>
      </td>
      {/* 状态（纯展示） */}
      <td className="px-3 py-3.5 text-center">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
          point.status === 'used'
            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
            : 'bg-slate-600/20 text-slate-400 border border-slate-600/30'
        }`}>
          {point.status === 'used' ? '已用' : '未用'}
        </span>
      </td>
    </tr>
  );
};

const BreakdownDetail: React.FC<BreakdownDetailProps> = ({
  selectedBatch,
  breakdownResult,
  breakdownLoading,
  breakdownProgress,
  onStartBreakdown,
  taskId,
  onStopBreakdown,
  onViewMethod
}) => {
  const [plotPointStatus, setPlotPointStatus] = useState<Record<number, 'used' | 'unused'>>({}); // 剧情点状态
  const [qaReportModalOpen, setQaReportModalOpen] = useState(false); // 质检报告弹窗
  const [detailModalOpen, setDetailModalOpen] = useState(false); // 拆解详情弹窗
  const [currentTaskStatus, setCurrentTaskStatus] = useState<string | null>(null); // 当前任务状态

  // 获取当前批次任务状态（仅在页面加载时调用一次，用于连接WebSocket）
  useEffect(() => {
    const fetchCurrentTask = async () => {
      if (!selectedBatch) {
        setCurrentTaskStatus(null);
        return;
      }

      // 任务已完成，不需要获取
      if (selectedBatch.breakdown_status === BATCH_STATUS.COMPLETED) {
        setCurrentTaskStatus(null);
        return;
      }

      try {
        const response = await breakdownApi.getBatchCurrentTask(selectedBatch.id);
        const taskStatus = response.data?.status;
        const taskId = response.data?.task_id;

        // 如果没有正在运行的任务，不需要连接WebSocket
        if (!taskId) {
          setCurrentTaskStatus(null);
          return;
        }

        setCurrentTaskStatus(taskStatus || null);
      } catch (error) {
        console.error('获取任务状态失败:', error);
        setCurrentTaskStatus(null);
      }
    };

    // 页面加载时只调用一次
    fetchCurrentTask();
  }, [selectedBatch?.id]); // 只在batch变化时触发

  // 更新剧情点状态
  const handlePlotPointStatusChange = async (pointId: number, status: 'used' | 'unused') => {
    // 先乐观更新本地状态
    setPlotPointStatus(prev => ({
      ...prev,
      [pointId]: status
    }));

    try {
      await breakdownApi.updatePlotPointStatus(selectedBatch!.id, pointId, status);
    } catch (error) {
      console.error('更新剧情点状态失败:', error);
      // 回滚本地状态
      setPlotPointStatus(prev => ({
        ...prev,
        [pointId]: status === 'used' ? 'unused' : 'used'
      }));
    }
  };

  // 判断是否有拆解结果（plot_points）
  const hasBreakdownResult = !!breakdownResult?.plot_points;

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
  if (selectedBatch.breakdown_status === BATCH_STATUS.PENDING) {
    // 检查是否有取消中的任务
    if (currentTaskStatus === TASK_STATUS.CANCELLING) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-4">
          <div className="w-20 h-20 rounded-2xl bg-orange-500/10 flex items-center justify-center border border-orange-500/20 animate-pulse">
            <Loader2 size={32} className="text-orange-400 animate-spin" />
          </div>
          <p className="text-sm font-bold text-orange-400">任务正在取消中...</p>
          <p className="text-xs text-slate-700">请稍候，撤销完成后可重新开始</p>
        </div>
      );
    }

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

  // 拆解中状态（包括排队中，对用户来说都是"拆解中"）
  if (selectedBatch.breakdown_status === BATCH_STATUS.PROCESSING || selectedBatch.breakdown_status === BATCH_STATUS.QUEUED) {
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
        {/* 停止按钮 */}
        {taskId && onStopBreakdown && (
          <button
            onClick={onStopBreakdown}
            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs rounded-lg border border-red-500/30 transition-colors flex items-center gap-2"
          >
            <X size={14} />
            停止拆解
          </button>
        )}
      </div>
    );
  }

  // 加载结果中
  if (breakdownLoading) {
    return (
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* 骨架屏 */}
        <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-6 animate-pulse">
          <div className="h-6 w-48 bg-slate-700/50 rounded mb-4" />
          <div className="space-y-3">
            <div className="h-4 w-full bg-slate-700/30 rounded" />
            <div className="h-4 w-5/6 bg-slate-700/30 rounded" />
            <div className="h-4 w-4/6 bg-slate-700/30 rounded" />
          </div>
        </div>
        <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-6 animate-pulse">
          <div className="h-5 w-36 bg-slate-700/50 rounded mb-4" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-24 bg-slate-700/30 rounded" />
            <div className="h-24 bg-slate-700/30 rounded" />
          </div>
        </div>
      </div>
    );
  }

  // 拆解完成但无结果（数据异常）- 只有在不是加载中且没有结果时才显示异常
  if (selectedBatch.breakdown_status === BATCH_STATUS.COMPLETED && !breakdownLoading && !breakdownResult) {
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

  // 剧情点表格视图
  if (hasBreakdownResult && breakdownResult?.plot_points) {
    return (
      <>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* 标题栏 */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-200">剧情拆解结果</h2>
            {/* 查看拆解详情按钮 */}
            <button
              onClick={() => setDetailModalOpen(true)}
              className="p-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg border border-slate-600 transition-colors"
              title="拆解历史"
            >
              <History className="w-4 h-4" />
            </button>
          </div>

          {/* 质检信息卡片 */}
          {breakdownResult.qa_status && (
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-purple-400 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  质检结果
                  {/* 自动修正次数标签 */}
                  {breakdownResult.qa_report?.auto_fix_attempts !== undefined &&
                   breakdownResult.qa_report.auto_fix_attempts > 0 && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      breakdownResult.qa_report.auto_fix_success
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}>
                      已修正 {breakdownResult.qa_report.auto_fix_attempts} 次
                    </span>
                  )}
                </h3>
                <div className="flex items-center gap-3">
                  {/* 质检分数 */}
                  {breakdownResult.qa_score !== undefined && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-slate-400">分数:</span>
                      <span className={`text-sm font-black ${
                        breakdownResult.qa_score >= 80
                          ? 'text-green-400'
                          : breakdownResult.qa_score >= 60
                          ? 'text-yellow-400'
                          : 'text-red-400'
                      }`}>
                        {breakdownResult.qa_score}
                      </span>
                    </div>
                  )}
                  {/* 质检状态 */}
                  <div className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                    breakdownResult.qa_status === 'PASS'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : breakdownResult.qa_status === 'FAIL'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                  }`}>
                    {breakdownResult.qa_status === 'PASS' && <CheckCircle className="w-3 h-3" />}
                    {breakdownResult.qa_status === 'FAIL' && <XCircle className="w-3 h-3" />}
                    {breakdownResult.qa_status === 'pending' && <Clock className="w-3 h-3" />}
                    {breakdownResult.qa_status === 'PASS' ? '通过' : breakdownResult.qa_status === 'FAIL' ? '未通过' : '待质检'}
                  </div>
                  {/* 查看报告按钮 */}
                  {breakdownResult.qa_report && (
                    <button
                      onClick={() => setQaReportModalOpen(true)}
                      className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded-lg border border-slate-600 transition-colors"
                    >
                      查看报告
                    </button>
                  )}
                  {/* 手动重新生成按钮 - 当自动修正失败后显示 */}
                  {breakdownResult.qa_status === 'FAIL' &&
                   breakdownResult.qa_report?.auto_fix_attempts !== undefined &&
                   breakdownResult.qa_report.auto_fix_attempts >= 3 &&
                   !breakdownResult.qa_report.auto_fix_success &&
                   onStartBreakdown && (
                    <button
                      onClick={() => onStartBreakdown(selectedBatch!.id)}
                      className="px-2 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs rounded-lg border border-amber-500/30 transition-colors flex items-center gap-1"
                    >
                      <Play className="w-3 h-3" />
                      重新生成
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 剧情点统计 */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-cyan-400 flex items-center gap-2">
                <List className="w-4 h-4" />
                剧情点列表
              </h3>
              <div className="flex items-center gap-3 text-xs">
                <span className="text-slate-400">
                  共 <span className="text-cyan-400 font-semibold">{breakdownResult.plot_points.length}</span> 个
                </span>
                <span className="text-slate-600">|</span>
                <span className="text-slate-400">
                  已用 <span className="text-green-400 font-semibold">
                    {breakdownResult.plot_points.filter(p => p.status === 'used').length}
                  </span>
                </span>
                <span className="text-slate-600">|</span>
                <span className="text-slate-400">
                  未用 <span className="text-slate-400 font-semibold">
                    {breakdownResult.plot_points.filter(p => p.status === 'unused').length}
                  </span>
                </span>
              </div>
            </div>
          </div>

          {/* 剧情点表格 */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-900/50">
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
                    事件
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider w-28">
                    钩子类型
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider w-20">
                    状态
                  </th>
                </tr>
              </thead>
              <tbody>
                {breakdownResult.plot_points.map((point) => (
                  <PlotPointTableRow
                    key={point.id}
                    point={{ ...point, status: plotPointStatus[point.id] || point.status }}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 质检报告弹窗 */}
        <AnimatePresence>
          {qaReportModalOpen && (
            <QAReportModal
              report={breakdownResult.qa_report || null}
              onClose={() => setQaReportModalOpen(false)}
            />
          )}
        </AnimatePresence>

        {/* 拆解详情弹窗 */}
        <AnimatePresence>
          {detailModalOpen && selectedBatch && (
            <BreakdownDetailModal
              batchId={selectedBatch.id}
              onClose={() => setDetailModalOpen(false)}
              onViewMethod={onViewMethod}
            />
          )}
        </AnimatePresence>
      </>
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
