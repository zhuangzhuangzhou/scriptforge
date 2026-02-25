import React, { useEffect, useState } from 'react';
import {
  X, Clock, FileText, CheckCircle, XCircle,
  RefreshCw, Loader2, History, Eye
} from 'lucide-react';
import { motion } from 'framer-motion';
import { scriptApi } from '../../../../services/api';

interface ScriptHistoryModalProps {
  projectId: string;
  episodeNumber: number;
  onClose: () => void;
  onViewScript?: (scriptId: string, allScriptIds?: string[]) => void;
}

interface ScriptHistoryItem {
  script_id: string;
  episode_number: number;
  title: string;
  word_count: number;
  scene_count: number;
  qa_status: string | null;
  qa_score: number | null;
  is_current: boolean;
  created_at: string;
}

const ScriptHistoryModal: React.FC<ScriptHistoryModalProps> = ({
  projectId,
  episodeNumber,
  onClose,
  onViewScript
}) => {
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<ScriptHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const response = await scriptApi.getScriptHistory(projectId, episodeNumber);
        const list = response.data || [];
        setHistory(Array.isArray(list) ? list : [list]);
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取历史记录失败');
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [projectId, episodeNumber]);

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    });
  };

  const getQAStatusStyle = (status: string | null) => {
    switch (status) {
      case 'PASS': return 'bg-green-500/20 text-green-400';
      case 'FAIL': return 'bg-red-500/20 text-red-400';
      default: return 'bg-yellow-500/20 text-yellow-400';
    }
  };

  const handleView = (scriptId: string) => {
    if (onViewScript) {
      onViewScript(scriptId, history.map(h => h.script_id));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl"
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <History className="w-4 h-4 text-cyan-400" />
            剧本历史
            <span className="text-xs text-slate-400 font-normal">第{episodeNumber}集</span>
            {history.length > 0 && (
              <span className="text-xs text-slate-400 font-normal">共 {history.length} 次</span>
            )}
          </h3>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* 内容 - 固定高度 */}
        <div className="h-[350px] overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm text-slate-400 mt-3">加载中...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <XCircle className="w-8 h-8 text-red-400" />
              <p className="text-sm text-red-400 mt-3">{error}</p>
            </div>
          ) : history.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <FileText className="w-8 h-8 text-slate-600" />
              <p className="text-sm text-slate-500 mt-3">暂无剧本记录</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-800/50 sticky top-0">
                <tr className="border-b border-slate-700/50">
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider w-12">#</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider">时间</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider">标题</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider">字数</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider">场景</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider">质检</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider w-20">操作</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, index) => (
                  <tr key={item.script_id} className="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-slate-500">{history.length - index}</span>
                        {item.is_current && (
                          <span className="text-[9px] px-1 py-0.5 bg-cyan-500/20 text-cyan-400 rounded">最新</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span className="text-xs text-slate-300">{formatDateTime(item.created_at)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-slate-300 truncate max-w-[150px] block" title={item.title}>
                        {item.title}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-xs text-slate-400">{item.word_count || 0}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-xs text-slate-400">{item.scene_count || 0}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${getQAStatusStyle(item.qa_status)}`}>
                          {item.qa_score ?? '-'}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleView(item.script_id)}
                        className="flex items-center gap-1 px-2 py-1 text-[10px] text-cyan-400 hover:bg-cyan-500/10 rounded transition-colors"
                      >
                        <Eye className="w-3 h-3" />
                        查看
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 底部操作区 */}
        <div className="p-4 border-t border-slate-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
          >
            关闭
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default ScriptHistoryModal;
