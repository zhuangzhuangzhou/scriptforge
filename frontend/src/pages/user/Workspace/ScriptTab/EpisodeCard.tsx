import React from 'react';
import { FileEdit, CheckCircle2, Loader2, XCircle, Clock } from 'lucide-react';
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
  // 状态图标和颜色
  const getStatusDisplay = () => {
    if (episode.status === 'completed' && episode.script) {
      return {
        icon: <CheckCircle2 className="w-3.5 h-3.5" />,
        text: '已完成',
        color: 'text-green-400',
        bgColor: 'bg-green-500/20',
        borderColor: 'border-green-500/30'
      };
    }
    if (episode.status === 'in_progress') {
      return {
        icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
        text: '生成中',
        color: 'text-cyan-400',
        bgColor: 'bg-cyan-500/20',
        borderColor: 'border-cyan-500/30'
      };
    }
    if (episode.status === 'failed') {
      return {
        icon: <XCircle className="w-3.5 h-3.5" />,
        text: '失败',
        color: 'text-red-400',
        bgColor: 'bg-red-500/20',
        borderColor: 'border-red-500/30'
      };
    }
    return {
      icon: <Clock className="w-3.5 h-3.5" />,
      text: '待生成',
      color: 'text-slate-400',
      bgColor: 'bg-slate-600/20',
      borderColor: 'border-slate-600/30'
    };
  };

  const statusDisplay = getStatusDisplay();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onClick}
      className={`
        px-4 py-3 cursor-pointer transition-all
        ${isSelected
          ? 'bg-cyan-500/10 border-l-2 border-cyan-500'
          : 'hover:bg-slate-800/50 border-l-2 border-transparent'
        }
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <FileEdit className={`w-4 h-4 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
          <span className={`text-sm font-semibold ${isSelected ? 'text-cyan-300' : 'text-slate-300'}`}>
            第 {episode.episode} 集
          </span>
        </div>
        <div className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium flex items-center gap-1 ${statusDisplay.bgColor} ${statusDisplay.color} border ${statusDisplay.borderColor}`}>
          {statusDisplay.icon}
          {statusDisplay.text}
        </div>
      </div>

      {/* 剧本信息 */}
      {episode.script && (
        <div className="space-y-1">
          <p className="text-xs text-slate-400 line-clamp-1">{episode.script.title}</p>
          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            {episode.script.word_count && (
              <span>{episode.script.word_count} 字</span>
            )}
            {episode.script.qa_status && (
              <>
                <span>•</span>
                <span className={`${
                  episode.script.qa_status === 'PASS'
                    ? 'text-green-400'
                    : episode.script.qa_status === 'FAIL'
                    ? 'text-red-400'
                    : 'text-yellow-400'
                }`}>
                  {episode.script.qa_status === 'PASS' ? '质检通过' : episode.script.qa_status === 'FAIL' ? '质检未通过' : '待质检'}
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* 待生成状态 */}
      {!episode.script && episode.status === 'pending' && (
        <p className="text-[10px] text-slate-600">点击开始生成剧本</p>
      )}
    </motion.div>
  );
};

export default EpisodeCard;
