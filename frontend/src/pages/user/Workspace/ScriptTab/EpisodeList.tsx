import React from 'react';
import { FileEdit } from 'lucide-react';
import { Pagination } from 'antd';
import EpisodeCard from './EpisodeCard';
import type { EpisodeScript } from '../../../../types';

interface EpisodeListProps {
  episodes: Array<{
    episode: number;
    status: string;
    breakdownId?: string;
    batchId?: string;
    script?: EpisodeScript;
  }>;
  selectedEpisode: number | null;
  onSelectEpisode: (episode: number) => void;
  loading: boolean;
  // 分页相关
  currentPage?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
}

const EpisodeList: React.FC<EpisodeListProps> = ({
  episodes,
  selectedEpisode,
  onSelectEpisode,
  loading,
  currentPage = 1,
  totalPages = 1,
  onPageChange
}) => {
  // 骨架屏组件
  const EpisodeSkeleton = () => (
    <div className="px-4 py-3 bg-slate-800/30 border-l-2 border-transparent animate-pulse">
      <div className="flex items-center justify-between mb-2">
        <div className="h-4 w-20 bg-slate-700/50 rounded" />
        <div className="h-3 w-16 bg-slate-700/30 rounded" />
      </div>
      <div className="h-3 w-full bg-slate-700/30 rounded mb-1" />
      <div className="h-3 w-2/3 bg-slate-700/30 rounded" />
    </div>
  );

  return (
    <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl">
      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/30">
        {/* 剧集列表 */}
        {loading ? (
          <div className="space-y-0">
            {[1, 2, 3, 4, 5].map((i) => (
              <EpisodeSkeleton key={i} />
            ))}
          </div>
        ) : episodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-600 px-6 text-center">
            <FileEdit size={32} className="mb-3 opacity-30" />
            <p className="text-xs">暂无剧集数据</p>
            <p className="text-[10px] text-slate-700 mt-1">请先完成剧情拆解</p>
          </div>
        ) : (
          <>
            {episodes.map(episode => (
              <EpisodeCard
                key={episode.episode}
                episode={episode}
                isSelected={selectedEpisode === episode.episode}
                onClick={() => onSelectEpisode(episode.episode)}
              />
            ))}
          </>
        )}
      </div>

      {/* 分页控件 */}
      {totalPages > 1 && (
        <div className="px-3 py-2 border-t border-slate-800 bg-slate-900/80">
          <Pagination
            current={currentPage}
            total={totalPages * 20}
            pageSize={20}
            onChange={onPageChange}
            size="small"
            showSizeChanger={false}
            showQuickJumper={totalPages > 10}
            className="flex justify-center [&_.ant-pagination-item]:!bg-slate-800 [&_.ant-pagination-item]:!border-slate-700 [&_.ant-pagination-item-active]:!bg-cyan-600 [&_.ant-pagination-item-active]:!border-cyan-600 [&_.ant-pagination-item_a]:!text-slate-300 [&_.ant-pagination-item-active_a]:!text-white [&_.ant-pagination-prev_.ant-pagination-item-link]:!bg-slate-800 [&_.ant-pagination-prev_.ant-pagination-item-link]:!border-slate-700 [&_.ant-pagination-next_.ant-pagination-item-link]:!bg-slate-800 [&_.ant-pagination-next_.ant-pagination-item-link]:!border-slate-700 [&_.ant-pagination-jump-prev]:!text-slate-500 [&_.ant-pagination-jump-next]:!text-slate-500"
          />
        </div>
      )}
    </div>
  );
};

export default EpisodeList;
