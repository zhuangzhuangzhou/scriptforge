import React, { useEffect, useState } from 'react';
import {
  X, Clock, FileText, CheckCircle, XCircle, AlertTriangle,
  RefreshCw, Loader2, History, ExternalLink
} from 'lucide-react';
import { motion } from 'framer-motion';
import { breakdownApi } from '../../../../services/api';

interface BreakdownDetailModalProps {
  batchId: string;
  onClose: () => void;
  onViewMethod?: (methodId: string) => void;
}

interface BreakdownDetail {
  breakdown_id: string;
  batch_id: string;
  created_at: string | null;
  format_version: number;
  model_info: {
    provider: string;
    model_name: string;
    display_name: string;
  } | null;
  resource_info: {
    adapt_method?: {
      id: string;
      name: string;
      display_name: string;
    };
  };
  qa_status: string;
  qa_score: number | null;
  qa_report: any;
  qa_retry_count: number;
  plot_points_count?: number;
  task_info: {
    task_id: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    duration_seconds: number | null;
    retry_count: number;
  } | null;
}

const BreakdownDetailModal: React.FC<BreakdownDetailModalProps> = ({ batchId, onClose, onViewMethod }) => {
  const [loading, setLoading] = useState(true);
  const [details, setDetails] = useState<BreakdownDetail[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true);
        const response = await breakdownApi.getBreakdownHistory(batchId);
        const list = response.data?.items || response.data || [];
        setDetails(Array.isArray(list) ? list : [list]);
      } catch (err: any) {
        try {
          const response = await breakdownApi.getBreakdownDetail(batchId);
          setDetails(response.data ? [response.data] : []);
        } catch (fallbackErr: any) {
          setError(fallbackErr.response?.data?.detail || '获取详情失败');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchDetails();
  }, [batchId]);

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return '-';
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m${seconds % 60}s`;
  };

  const getQAStatusStyle = (status: string) => {
    switch (status) {
      case 'PASS': return 'bg-green-500/20 text-green-400';
      case 'FAIL': return 'bg-red-500/20 text-red-400';
      default: return 'bg-yellow-500/20 text-yellow-400';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl"
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <History className="w-4 h-4 text-cyan-400" />
            拆解历史
            {details.length > 0 && (
              <span className="text-xs text-slate-400 font-normal">共 {details.length} 次</span>
            )}
          </h3>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* 内容 - 固定高度 */}
        <div className="h-[400px] overflow-y-auto">
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
          ) : details.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <FileText className="w-8 h-8 text-slate-600" />
              <p className="text-sm text-slate-500 mt-3">暂无拆解记录</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-800/50 sticky top-0">
                <tr className="border-b border-slate-700/50">
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider w-12">#</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider">时间</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider">模型</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider">方法论</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider">剧情点</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider">质检</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider">修正</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider">耗时</th>
                </tr>
              </thead>
              <tbody>
                {details.map((detail, index) => (
                  <tr key={detail.breakdown_id} className="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <span className="text-xs text-slate-500">{details.length - index}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span className="text-xs text-slate-300">{formatDateTime(detail.created_at)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {detail.model_info ? (
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] px-1.5 py-0.5 bg-cyan-500/20 text-cyan-300 rounded">
                            {detail.model_info.provider}
                          </span>
                          <span className="text-xs text-slate-300 truncate max-w-[100px]" title={detail.model_info.model_name}>
                            {detail.model_info.model_name}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {detail.resource_info?.adapt_method ? (
                        <button
                          onClick={() => onViewMethod?.(detail.resource_info.adapt_method!.id)}
                          className="text-xs text-cyan-400 hover:text-cyan-300 truncate max-w-[120px] block text-left flex items-center gap-1 group"
                          title={detail.resource_info.adapt_method.display_name}
                        >
                          <span className="truncate">{detail.resource_info.adapt_method.display_name}</span>
                          <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500">默认</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-xs text-cyan-400 font-medium">
                        {detail.plot_points_count ?? '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <span className={`text-xs font-bold ${
                          detail.qa_status === 'PASS' ? 'text-green-400' :
                          detail.qa_status === 'FAIL' ? 'text-red-400' : 'text-yellow-400'
                        }`}>
                          {detail.qa_score ?? '-'}
                        </span>
                        <span className={`w-4 h-4 rounded-full flex items-center justify-center ${getQAStatusStyle(detail.qa_status)}`}>
                          {detail.qa_status === 'PASS' ? <CheckCircle className="w-2.5 h-2.5" /> :
                           detail.qa_status === 'FAIL' ? <XCircle className="w-2.5 h-2.5" /> :
                           <AlertTriangle className="w-2.5 h-2.5" />}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {detail.qa_retry_count > 0 ? (
                        <div className="flex items-center justify-center gap-1 text-amber-400">
                          <RefreshCw className="w-3 h-3" />
                          <span className="text-[10px]">{detail.qa_retry_count}</span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-xs text-slate-400">
                        {formatDuration(detail.task_info?.duration_seconds ?? null)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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

export default BreakdownDetailModal;
