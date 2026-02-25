import React from 'react';
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
}

const EpisodeList: React.FC<EpisodeListProps> = ({
  episodes,
  selectedEpisode,
  onSelectEpisode,
  loading
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
    </div>
  );
};

export default EpisodeList;
