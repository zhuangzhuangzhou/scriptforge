import React from 'react';
import { Batch, PlotBreakdown } from '../../../../types';
import BatchList from './BatchList';
import BreakdownDetail from './BreakdownDetail';

interface PlotTabProps {
  projectId: string;
  batches: Batch[];
  selectedBatch: Batch | null;
  onSelectBatch: (batch: Batch) => void;
  onStartBreakdown: (batchId: string) => void;
  isCreatingBatches: boolean;
  loadingBatches: boolean;
  breakdownTaskId: string | null;
  breakdownProgress: number;
  breakdownResult: PlotBreakdown | null;
  breakdownLoading: boolean;
  onBatchScroll: (e: React.UIEvent<HTMLDivElement>) => void;
}

const PlotTab: React.FC<PlotTabProps> = ({
  batches,
  selectedBatch,
  onSelectBatch,
  onStartBreakdown,
  isCreatingBatches,
  loadingBatches,
  breakdownTaskId,
  breakdownProgress,
  breakdownResult,
  breakdownLoading,
  onBatchScroll
}) => {
  return (
    <div className="h-full flex gap-0 animate-in fade-in slide-in-from-bottom-4 duration-300 overflow-hidden bg-slate-950">
      {/* LEFT COLUMN: Batch List */}
      <BatchList
        batches={batches}
        selectedBatch={selectedBatch}
        onSelectBatch={onSelectBatch}
        onStartBreakdown={onStartBreakdown}
        isCreatingBatches={isCreatingBatches}
        loadingBatches={loadingBatches}
        breakdownTaskId={breakdownTaskId}
        breakdownProgress={breakdownProgress}
        onScroll={onBatchScroll}
      />

      {/* RIGHT COLUMN: Breakdown Details */}
      <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-0">
          <BreakdownDetail
            selectedBatch={selectedBatch}
            breakdownResult={breakdownResult}
            breakdownLoading={breakdownLoading}
            breakdownProgress={breakdownProgress}
            onStartBreakdown={onStartBreakdown}
          />
        </div>
      </div>
    </div>
  );
};

export default PlotTab;
