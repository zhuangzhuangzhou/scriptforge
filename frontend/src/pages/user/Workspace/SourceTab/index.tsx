import React, { useState } from 'react';
import {
  Search, X, Loader2, Trash2, BookOpen, Download, Eye, BookText, Upload,
  CheckCircle2, CircleDashed
} from 'lucide-react';
import ConfirmModal from '../../../../components/modals/ConfirmModal';

interface SourceTabProps {
  project: any;
  chapters: any[];
  selectedChapter: any | null;
  onSelectChapter: (chapter: any) => void;
  loadingChapters: boolean;
  totalChapters: number;
  keyword: string;
  onKeywordChange: (keyword: string) => void;
  onScroll: (e: React.UIEvent<HTMLDivElement>) => void;
  onDeleteChapter: (e: React.MouseEvent, chapterId: string) => void;
  onDownloadChapter: () => void;
  onUploadChapter: () => void;
}

// 状态标签组件
const StatusTag = ({ status }: { status: 'processed' | 'unprocessed' }) => (
  <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold border transition-colors ${
    status === 'processed'
    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
    : 'bg-slate-800 text-slate-500 border-slate-700'
  }`}>
    {status === 'processed' ? <CheckCircle2 size={10} /> : <CircleDashed size={10} />}
    {status === 'processed' ? '已拆解' : '未拆解'}
  </div>
);

const SourceTab: React.FC<SourceTabProps> = ({
  project,
  chapters,
  selectedChapter,
  onSelectChapter,
  loadingChapters,
  totalChapters,
  keyword,
  onKeywordChange,
  onScroll,
  onDeleteChapter,
  onDownloadChapter,
  onUploadChapter
}) => {
  // 删除确认弹窗状态
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingChapterId, setDeletingChapterId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // 处理删除点击
  const handleDeleteClick = (e: React.MouseEvent, chapterId: string) => {
    e.stopPropagation();
    setDeletingChapterId(chapterId);
    setDeleteModalOpen(true);
  };

  // 执行删除
  const handleConfirmDelete = async () => {
    if (!deletingChapterId) return;
    setIsDeleting(true);
    try {
      await onDeleteChapter({ stopPropagation: () => {} } as React.MouseEvent, deletingChapterId);
      setDeleteModalOpen(false);
      setDeletingChapterId(null);
    } finally {
      setIsDeleting(false);
    }
  };
  return (
    <div className="h-full flex gap-0 overflow-hidden bg-slate-950">
      {/* LEFT COLUMN: Chapter List */}
      <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl relative">
        <div className="p-5 border-b border-slate-800 flex flex-col gap-4 bg-slate-900/50 backdrop-blur">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-white tracking-tight flex items-center gap-2 truncate pr-2">
              {project.name}
              <span className="bg-slate-800 border border-slate-700 text-xs px-2 py-0.5 rounded-full text-slate-400 font-mono shrink-0">
                {totalChapters} 章
              </span>
            </h3>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="搜索章节名称..."
              value={keyword}
              onChange={(e) => onKeywordChange(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-300 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all"
            />
            {keyword && (
              <X
                size={14}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white cursor-pointer"
                onClick={() => onKeywordChange('')}
              />
            )}
          </div>
        </div>

        <div
          className="flex-1 overflow-y-auto divide-y divide-slate-800/30 no-scrollbar pb-16"
          onScroll={onScroll}
        >
          {loadingChapters && chapters.length === 0 ? (
            // 骨架屏加载
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4 animate-pulse">
                  <div className="flex items-center justify-between mb-2">
                    <div className="h-3 w-16 bg-slate-700/50 rounded" />
                    <div className="h-2 w-12 bg-slate-700/30 rounded" />
                  </div>
                  <div className="h-3 w-3/4 bg-slate-700/50 rounded" />
                </div>
              ))}
            </div>
          ) : chapters.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-slate-600 px-6 text-center">
              <p className="text-xs">{keyword ? '未搜索到相关章节' : '暂无章节数据，请先在配置页执行"智能拆分"'}</p>
            </div>
          ) : (
            <>
              {chapters.map(ch => (
                <div
                  key={ch.id}
                  onClick={() => onSelectChapter(ch)}
                  className={`px-5 py-3 cursor-pointer transition-all flex flex-col gap-1 group relative ${
                    selectedChapter?.id === ch.id
                    ? 'bg-cyan-500/10 border-l-4 border-l-cyan-500 shadow-inner'
                    : 'hover:bg-slate-800/50 border-l-4 border-l-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {/* Glowing indicator light */}
                      <div className={`w-2 h-2 rounded-full transition-all ${
                        selectedChapter?.id === ch.id
                        ? 'bg-cyan-500 shadow-[0_0_8px_2px_rgba(6,182,212,0.6)]'
                        : 'bg-slate-600'
                      }`} />
                      <div className={`text-[10px] font-black uppercase tracking-widest transition-colors ${selectedChapter?.id === ch.id ? 'text-cyan-400' : 'text-slate-500'}`}>
                        Chapter {String(ch.chapter_number).padStart(2, '0')}
                      </div>
                      <button
                        onClick={(e) => handleDeleteClick(e, String(ch.id))}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 transition-all"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                    <div className="mr-2.5">
                      <StatusTag status={ch.status === 'processed' ? 'processed' : 'unprocessed'} />
                    </div>
                  </div>
                  <div className={`text-xs truncate ${selectedChapter?.id === ch.id ? 'text-white font-bold' : 'text-slate-400'}`}>
                    {ch.title}
                  </div>
                </div>
              ))}
              {loadingChapters && (
                <div className="p-4 flex justify-center">
                  <Loader2 size={16} className="animate-spin text-cyan-500/50" />
                </div>
              )}
            </>
          )}
        </div>

        {/* FIXED FOOTER: Import Button */}
        <div className="absolute bottom-0 left-0 w-full p-2.5 bg-slate-900/80 border-t border-slate-800 backdrop-blur-md flex justify-center">
          <button
            onClick={onUploadChapter}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/40 hover:bg-slate-800 text-slate-500 hover:text-slate-300 rounded-lg text-[10px] transition-all border border-slate-800 hover:border-slate-700 active:scale-95 group shadow-sm"
          >
            <Upload size={12} className="group-hover:-translate-y-0.5 transition-transform" />
            导入章节 (TXT)
          </button>
        </div>
      </div>

      {/* RIGHT COLUMN: Content Viewer */}
      <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
        {/* Inner Header */}
        <div className="h-16 border-b border-slate-800 bg-slate-900 flex items-center justify-between px-8 shrink-0 z-10 shadow-sm">
          <div className="flex items-center gap-4 h-full">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 shadow-inner shrink-0">
              <BookOpen size={20} className="text-cyan-400" />
            </div>
            <div className="flex items-center gap-3 min-w-0">
              <h2 className="text-sm font-bold text-white tracking-widest uppercase truncate max-w-[400px]">
                {selectedChapter ? selectedChapter.title : '请选择章节'}
              </h2>
              {selectedChapter && (
                <span className="text-[10px] text-slate-600 font-mono shrink-0 pt-0.5 uppercase">
                  Stat: {selectedChapter.word_count || 0} Words
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-4">
            {selectedChapter && (
              <div className="flex items-center gap-2">
                <StatusTag status={selectedChapter.status === 'processed' ? 'processed' : 'unprocessed'} />
                {selectedChapter.status === 'processed' && (
                  <button className="flex items-center gap-1.5 px-3 py-2 text-slate-400 hover:text-indigo-400 text-xs font-bold transition-colors">
                    <Eye size={14} /> 查看结果
                  </button>
                )}
              </div>
            )}
            <div className="w-px h-4 bg-slate-800"></div>
            <button
              onClick={onDownloadChapter}
              disabled={!selectedChapter}
              className="p-2 text-slate-500 hover:text-white transition-all disabled:opacity-30"
              title="下载原文"
            >
              <Download size={16}/>
            </button>
          </div>
        </div>

        {/* Content Display */}
        <div className="flex-1 overflow-y-auto p-0 md:p-8 font-mono text-sm leading-relaxed text-slate-300 bg-slate-950/40">
          <div className="max-w-3xl mx-auto bg-slate-900 border border-slate-800 shadow-2xl min-h-full px-5 py-8 md:py-12 rounded-xl md:rounded-2xl relative">
            {selectedChapter ? (
              <article className="prose prose-invert prose-slate max-w-none prose-p:text-slate-300 prose-p:leading-relaxed prose-headings:text-white">
                <h1 className="text-2xl font-bold mb-8 text-center border-b border-slate-800/50 pb-6 tracking-tight">{selectedChapter.title}</h1>
                <div className="whitespace-pre-line text-slate-300 selection:bg-cyan-500/30 text-sm leading-loose">
                  {selectedChapter.content || '章节内容为空'}
                </div>
              </article>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-700 gap-4 mt-20 opacity-30">
                <BookText size={64} />
                <p className="text-sm tracking-widest uppercase font-black">Select a chapter to read</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 删除确认弹窗 */}
      <ConfirmModal
        open={deleteModalOpen}
        onCancel={() => {
          setDeleteModalOpen(false);
          setDeletingChapterId(null);
        }}
        onConfirm={handleConfirmDelete}
        title="确认删除章节"
        content={
          <div className="text-left">
            <p className="text-slate-300 mb-3">
              确定要删除该章节吗？此操作不可撤销。
            </p>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
              <div className="flex gap-2 items-start">
                <Trash2 size={14} className="text-amber-400 mt-0.5 shrink-0" />
                <p className="text-xs text-amber-300 leading-relaxed">
                  删除章节后将无法恢复，请确认操作。
                </p>
              </div>
            </div>
          </div>
        }
        confirmText="确认删除"
        confirmType="danger"
        iconType="danger"
        loading={isDeleting}
      />
    </div>
  );
};

export default SourceTab;
