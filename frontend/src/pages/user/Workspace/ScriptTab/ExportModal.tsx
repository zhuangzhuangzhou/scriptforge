import React, { useState } from 'react';
import { X, Download, FileText, File, Files, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface ExportModalProps {
  onClose: () => void;
  onExport: (scope: 'current' | 'all' | 'merged', format: 'pdf' | 'docx') => Promise<void>;
  currentEpisode: number;
  totalEpisodes: number;
}

const ExportModal: React.FC<ExportModalProps> = ({
  onClose,
  onExport,
  currentEpisode,
  totalEpisodes
}) => {
  const [scope, setScope] = useState<'current' | 'all' | 'merged'>('current');
  const [format, setFormat] = useState<'pdf' | 'docx'>('docx');
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    try {
      setExporting(true);
      await onExport(scope, format);
      onClose();
    } catch (err) {
      console.error('导出失败:', err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl"
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Download className="w-4 h-4 text-cyan-400" />
            导出剧本
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 space-y-6">
          {/* 导出范围 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-3">
              导出范围
            </label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setScope('current')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  scope === 'current'
                    ? 'border-cyan-500 bg-cyan-500/10'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                }`}
              >
                <FileText className={`w-6 h-6 mx-auto mb-2 ${
                  scope === 'current' ? 'text-cyan-400' : 'text-slate-400'
                }`} />
                <div className="text-sm font-medium text-slate-300">本集</div>
                <div className="text-xs text-slate-500 mt-1">第 {currentEpisode} 集</div>
              </button>

              <button
                onClick={() => setScope('all')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  scope === 'all'
                    ? 'border-cyan-500 bg-cyan-500/10'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                }`}
              >
                <File className={`w-6 h-6 mx-auto mb-2 ${
                  scope === 'all' ? 'text-cyan-400' : 'text-slate-400'
                }`} />
                <div className="text-sm font-medium text-slate-300">分集</div>
                <div className="text-xs text-slate-500 mt-1">{totalEpisodes} 个文件</div>
              </button>

              <button
                onClick={() => {
                  setScope('merged');
                  setFormat('docx');
                }}
                className={`p-4 rounded-lg border-2 transition-all ${
                  scope === 'merged'
                    ? 'border-cyan-500 bg-cyan-500/10'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                }`}
              >
                <Files className={`w-6 h-6 mx-auto mb-2 ${
                  scope === 'merged' ? 'text-cyan-400' : 'text-slate-400'
                }`} />
                <div className="text-sm font-medium text-slate-300">合并</div>
                <div className="text-xs text-slate-500 mt-1">1 个文件</div>
              </button>
            </div>
          </div>

          {/* 导出格式 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-3">
              导出格式
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setFormat('pdf')}
                disabled={scope === 'merged'}
                className={`p-4 rounded-lg border-2 transition-all ${
                  format === 'pdf'
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                } ${scope === 'merged' ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="text-2xl mb-2">📄</div>
                <div className="text-sm font-medium text-slate-300">PDF</div>
                <div className="text-xs text-slate-500 mt-1">便于阅读</div>
              </button>

              <button
                onClick={() => setFormat('docx')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  format === 'docx'
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                }`}
              >
                <div className="text-2xl mb-2">📝</div>
                <div className="text-sm font-medium text-slate-300">Word</div>
                <div className="text-xs text-slate-500 mt-1">便于编辑</div>
              </button>
            </div>
          </div>

          {/* 提示信息 */}
          {scope === 'all' && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
              <p className="text-xs text-amber-300">
                导出所有剧集将生成 ZIP 压缩包，可能需要较长时间
              </p>
            </div>
          )}
          {scope === 'merged' && (
            <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3">
              <p className="text-xs text-cyan-300">
                合并导出将所有剧集整合为一份 Word 文档，每集之间自动分页
              </p>
            </div>
          )}
        </div>

        {/* 底部操作 */}
        <div className="p-4 border-t border-slate-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={exporting}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm rounded-lg transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {exporting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                导出中...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                开始导出
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default ExportModal;
