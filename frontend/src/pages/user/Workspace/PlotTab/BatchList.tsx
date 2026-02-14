import React from 'react';
import { Layers, Loader2 } from 'lucide-react';
import { Batch } from '../../../../types';
import BatchCard from './BatchCard';

interface BatchListProps {
  batches: Batch[];
  selectedBatch: Batch | null;
  onSelectBatch: (batch: Batch) => void;
  onStartBreakdown: (batchId: string) => void;
  isCreatingBatches: boolean;
  loadingBatches: boolean;
  breakdownTaskId: string | null;
  breakdownProgress: number;
  onScroll: (e: React.UIEvent<HTMLDivElement>) => void;
}

const BatchList: React.FC<BatchListProps> = ({
  batches,
  selectedBatch,
  onSelectBatch,
  onStartBreakdown,
  isCreatingBatches,
  loadingBatches,
  breakdownTaskId,
  breakdownProgress,
  onScroll
}) => {
  // 批次骨架屏组件
  const BatchSkeleton = () => (
    <div className="bg-slate-800/30 border border-slate-700/30 p-4 animate-pulse">
      <div className="flex items-center justify-between mb-2">
        <div className="h-4 w-20 bg-slate-700/50 rounded" />
        <div className="h-3 w-16 bg-slate-700/30 rounded" />
      </div>
      <div className="h-3 w-full bg-slate-700/30 rounded mb-2" />
      <div className="h-3 w-2/3 bg-slate-700/30 rounded" />
    </div>
  );

  return (
    <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl">
      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/30 no-scrollbar" onScroll={onScroll}>
        {isCreatingBatches ? (
          // 创建批次中
          <div className="p-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <BatchSkeleton key={i} />
            ))}
          </div>
        ) : batches.length === 0 && !loadingBatches ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-600 px-6 text-center">
            <Layers size={32} className="mb-3 opacity-30" />
            <p className="text-xs">暂无批次数据</p>
            <p className="text-[10px] text-slate-700 mt-1">请先在配置页启动项目</p>
          </div>
        ) : (
          <>
            {batches.map(batch => (
              <BatchCard
                key={batch.id}
                batch={batch}
                isSelected={selectedBatch?.id === batch.id}
                onClick={() => onSelectBatch(batch)}
                onRetry={() => {
                  onSelectBatch(batch);
                  onStartBreakdown(batch.id);
                }}
                breakdownTaskId={breakdownTaskId}
                breakdownProgress={breakdownProgress}
              />
            ))}
            {loadingBatches && (
              <div className="p-4 flex justify-center">
                <Loader2 size={16} className="animate-spin text-cyan-500/50" />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default BatchList;
