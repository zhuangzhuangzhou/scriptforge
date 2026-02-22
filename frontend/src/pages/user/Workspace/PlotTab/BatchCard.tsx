import React from 'react';
import { CheckCircle2, Loader2, X, CircleDashed } from 'lucide-react';
import { Batch } from '../../../../types';
import { BATCH_STATUS } from '../../../../constants/status';

interface BatchCardProps {
  batch: Batch;
  isSelected: boolean;
  onClick: () => void;
  onRetry: () => void;
  breakdownTaskId: string | null;
  breakdownProgress: number;
}

const BatchCard: React.FC<BatchCardProps> = ({
  batch,
  isSelected,
  onClick,
  onRetry,
  breakdownTaskId,
  breakdownProgress
}) => {
  return (
    <div
      onClick={onClick}
      className={`px-5 py-4 cursor-pointer transition-all group relative ${
        isSelected
          ? 'bg-cyan-500/10 border-l-4 border-l-cyan-500 shadow-inner'
          : 'hover:bg-slate-800/50 border-l-4 border-l-transparent'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full transition-all ${
            isSelected
              ? 'bg-cyan-500 shadow-[0_0_8px_2px_rgba(6,182,212,0.6)]'
              : 'bg-slate-600'
          }`} />
          <span className={`text-sm font-bold ${isSelected ? 'text-cyan-400' : 'text-white'}`}>
            批次 {batch.batch_number}
          </span>
        </div>
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold border transition-colors ${
          batch.breakdown_status === BATCH_STATUS.COMPLETED
            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
            : (batch.breakdown_status === BATCH_STATUS.IN_PROGRESS || batch.breakdown_status === BATCH_STATUS.QUEUED)
            ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20 animate-pulse'
            : batch.breakdown_status === BATCH_STATUS.FAILED
            ? 'bg-red-500/10 text-red-400 border-red-500/20'
            : 'bg-slate-800 text-slate-500 border-slate-700'
        }`}>
          {batch.breakdown_status === BATCH_STATUS.COMPLETED && <CheckCircle2 size={10} />}
          {(batch.breakdown_status === BATCH_STATUS.IN_PROGRESS || batch.breakdown_status === BATCH_STATUS.QUEUED) && <Loader2 size={10} className="animate-spin" />}
          {batch.breakdown_status === BATCH_STATUS.FAILED && <X size={10} />}
          {batch.breakdown_status === BATCH_STATUS.PENDING && <CircleDashed size={10} />}
          {batch.breakdown_status === BATCH_STATUS.COMPLETED ? '已拆解' :
           (batch.breakdown_status === BATCH_STATUS.IN_PROGRESS || batch.breakdown_status === BATCH_STATUS.QUEUED) ? '拆解中' :
           batch.breakdown_status === BATCH_STATUS.FAILED ? '失败' : '未拆解'}
        </div>
      </div>
      <div className="text-xs text-slate-400">
        第 {batch.start_chapter} - {batch.end_chapter} 章
        <span className="text-slate-600 ml-2">({batch.total_chapters} 章)</span>
      </div>
      {(batch.breakdown_status === BATCH_STATUS.IN_PROGRESS || batch.breakdown_status === BATCH_STATUS.QUEUED) && (
        <div className="mt-2">
          {/* 进度条 */}
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500 ${!isSelected ? 'animate-pulse' : ''}`}
              style={{
                width: isSelected && breakdownTaskId
                  ? `${breakdownProgress}%`
                  : '100%'
              }}
            />
          </div>

          {/* 进度信息 */}
          {isSelected && breakdownTaskId && (
            <div className="flex items-center justify-between mt-1.5 text-[10px]">
              <span className="text-cyan-400 font-medium">{breakdownProgress}%</span>
              <span className="text-slate-500">{breakdownProgress < 30 ? '正在初始化...' : breakdownProgress < 60 ? '分析中...' : breakdownProgress < 90 ? '生成结果...' : '完成中...'}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BatchCard;
