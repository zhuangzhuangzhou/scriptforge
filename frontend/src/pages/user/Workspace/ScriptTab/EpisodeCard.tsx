import React from 'react';
import { Circle, CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import type { EpisodeScript } from '../../../../types';

interface EpisodeCardProps {
  episode: {
    episode: number;
    status: string;
    breakdownId?: string;
    batchId?: string;
    script?: EpisodeScript;
  };
  isSelected: boolean;
  onClick: () => void;
}

const EpisodeCard: React.FC<EpisodeCardProps> = ({
  episode,
  isSelected,
  onClick
}) => {
  // 状态图标
  const getStatusIcon = () => {
    if (episode.status === 'completed' && episode.script) {
      return <CheckCircle2 className="w-4 h-4 text-green-400" />;
    }
    if (episode.status === 'in_progress') {
      return <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />;
    }
    if (episode.status === 'failed') {
      return <XCircle className="w-4 h-4 text-red-400" />;
    }
    return <Circle className="w-4 h-4 text-slate-600" />;
  };

  // 底部信息
  const getMetaInfo = () => {
    if (episode.script) {
      const parts: string[] = [];
      if (episode.script.word_count) parts.push(`${episode.script.word_count} 字`);
      if (episode.script.qa_status === 'PASS') parts.push('质检通过');
      else if (episode.script.qa_status === 'FAIL') parts.push('质检未通过');
      return parts.join(' · ');
    }
    if (episode.status === 'in_progress') return '生成中...';
    if (episode.status === 'failed') return '生成失败';
    return '待生成';
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onClick={onClick}
      className={`
        h-[72px] px-3 py-2 flex items-start gap-3 cursor-pointer transition-all
        ${isSelected
          ? 'bg-cyan-500/10 border-l-2 border-cyan-500'
          : 'hover:bg-slate-800/50 border-l-2 border-transparent'
        }
      `}
    >
      <div className="pt-0.5">{getStatusIcon()}</div>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium ${isSelected ? 'text-cyan-300' : 'text-slate-300'}`}>
          第 {episode.episode} 集
        </div>
        <div className="text-xs text-slate-400 truncate mt-0.5">
          {episode.script?.title || '—'}
        </div>
        <div className={`text-[11px] mt-1 ${
          episode.script?.qa_status === 'FAIL' ? 'text-red-400' : 'text-slate-500'
        }`}>
          {getMetaInfo()}
        </div>
      </div>
    </motion.div>
  );
};

export default EpisodeCard;
