import React, { useRef, useCallback } from 'react';
import { FileEdit, Loader2 } from 'lucide-react';
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
  // 无限滚动相关
  hasMore?: boolean;
  onLoadMore?: () => void;
  loadingMore?: boolean;
}

const EpisodeList: React.FC<EpisodeListProps> = ({
  episodes,
  selectedEpisode,
  onSelectEpisode,
  loading,
  hasMore = false,
  onLoadMore,
  loadingMore = false
}) => {
  const listRef = useRef<HTMLDivElement>(null);

  // 滚动到底部时加载更多
  const handleScroll = useCallback(() => {
    if (!listRef.current || !hasMore || loadingMore || !onLoadMore) return;

    const { scrollTop, scrollHeight, clientHeight } = listRef.current;
    // 距离底部 100px 时触发加载
    if (scrollHeight - scrollTop - clientHeight < 100) {
      onLoadMore();
    }
  }, [hasMore, loadingMore, onLoadMore]);

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
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto divide-y divide-slate-800/30"
      >
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

            {/* 加载更多指示器 */}
            {loadingMore && (
              <div className="flex items-center justify-center py-4 text-slate-500">
                <Loader2 size={16} className="animate-spin mr-2" />
                <span className="text-xs">加载中...</span>
              </div>
            )}

            {/* 已加载全部 */}
            {!hasMore && episodes.length > 0 && (
              <div className="py-3 text-center text-xs text-slate-600">
                已加载全部 {episodes.length} 集
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default EpisodeList;
