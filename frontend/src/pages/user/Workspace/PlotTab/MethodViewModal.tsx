import React, { useEffect, useState } from 'react';
import { X, Loader2, BookOpen } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '../../../../services/api';
import ReactMarkdown from 'react-markdown';

interface MethodViewModalProps {
  methodId: string;
  onClose: () => void;
}

interface MethodDetail {
  id: string;
  name: string;
  display_name: string;
  description: string;
  content: string;
  category: string;
}

const MethodViewModal: React.FC<MethodViewModalProps> = ({ methodId, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [method, setMethod] = useState<MethodDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMethod = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/ai-resources/${methodId}`);
        setMethod(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取方法论详情失败');
      } finally {
        setLoading(false);
      }
    };
    fetchMethod();
  }, [methodId]);

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
            <BookOpen className="w-4 h-4 text-cyan-400" />
            {loading ? '加载中...' : method?.display_name || '方法论详情'}
          </h3>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* 内容 - 固定高度 */}
        <div className="h-[500px] overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm text-slate-400 mt-3">加载中...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          ) : method ? (
            <div className="p-6">
              {/* 描述 */}
              {method.description && (
                <div className="mb-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                  <p className="text-sm text-slate-400">{method.description}</p>
                </div>
              )}

              {/* 内容 - Markdown 渲染 */}
              <div className="prose prose-invert prose-sm max-w-none
                prose-headings:text-slate-200 prose-headings:font-semibold
                prose-p:text-slate-300 prose-p:leading-relaxed
                prose-li:text-slate-300
                prose-strong:text-cyan-400
                prose-code:text-cyan-300 prose-code:bg-slate-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                prose-pre:bg-slate-800 prose-pre:border prose-pre:border-slate-700
                prose-blockquote:border-l-cyan-500 prose-blockquote:text-slate-400
                prose-hr:border-slate-700
              ">
                <ReactMarkdown>{method.content || '暂无内容'}</ReactMarkdown>
              </div>
            </div>
          ) : null}
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

export default MethodViewModal;
