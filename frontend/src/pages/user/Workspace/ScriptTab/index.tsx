import React from 'react';
import {
  Plus, Layers, RefreshCw, Trash2, X, CheckCircle2, Loader2,
  ThumbsUp, Download, FileEdit, Save, FileCheck, Search
} from 'lucide-react';

interface Episode {
  id: number;
  title: string;
  subtitle: string;
  status: string;
  wordCount: number;
  content: string;
  qcReport: {
    score: number;
    status: string;
    checks: { title: string; items: string[] }[];
  } | null;
}

interface ScriptTabProps {
  episodes: Episode[];
  selectedEpisodeId: number;
  onSelectEpisode: (id: number) => void;
}

const ChevronDownIcon = ({size, className}:{size:number, className?:string}) => (
  <svg width={size} height={size} className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
);

const ScriptTab: React.FC<ScriptTabProps> = ({
  episodes,
  selectedEpisodeId,
  onSelectEpisode
}) => {
  const selectedEpisode = episodes.find(ep => ep.id === selectedEpisodeId) || episodes[0];

  return (
    <div className="h-full flex gap-0 animate-in fade-in slide-in-from-bottom-4 duration-300 overflow-hidden bg-slate-950">
      {/* LEFT COLUMN: Controls & List */}
      <div className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl">
        {/* Generator Controls */}
        <div className="p-4 border-b border-slate-800 space-y-3 bg-slate-900/50">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">剧集生成控制</h3>

          <button className="w-full py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white rounded-lg font-bold shadow-lg shadow-green-900/20 text-sm flex items-center justify-center gap-2 transition-all hover:scale-[1.02]">
            <Plus size={16} /> 生成下一批 (1/1)
          </button>

          <button className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2">
            <Layers size={14} /> ∞ 全部生成
          </button>

          <div className="flex items-center gap-2">
            <div className="flex-1 relative">
              <input
                type="number"
                defaultValue={3}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-center text-white focus:border-cyan-500 outline-none font-mono shadow-inner"
              />
            </div>
            <button className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs text-slate-400 border border-slate-700 rounded-lg flex items-center justify-center gap-1 transition-all">
              <RefreshCw size={12} /> 循环生成
            </button>
          </div>
        </div>

        {/* Batch List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="px-4 py-3 flex items-center justify-between text-xs text-slate-500 bg-slate-900/50 sticky top-0 z-10 backdrop-blur border-b border-slate-800">
            <span>批次管理</span>
            <div className="flex gap-2">
              <Trash2 size={12} className="hover:text-red-400 cursor-pointer transition-colors"/>
              <X size={12} className="hover:text-white cursor-pointer transition-colors"/>
            </div>
          </div>

          {/* Batch Header */}
          <div className="px-4 py-2 bg-slate-800/30 border-b border-slate-800 flex items-center justify-between shadow-inner">
            <div className="flex items-center gap-2">
              <ChevronDownIcon size={12} className="text-slate-400" />
              <span className="text-xs font-bold text-slate-200">第1批次 (1-6章)</span>
            </div>
            <div className="flex items-center gap-1 text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
              <CheckCircle2 size={10} /> 全部通过
            </div>
          </div>

          {/* Episodes List */}
          <div className="divide-y divide-slate-800/30">
            {episodes.map(ep => (
              <div
                key={ep.id}
                onClick={() => onSelectEpisode(ep.id)}
                className={`px-4 py-4 cursor-pointer transition-all flex items-center justify-between group ${
                  selectedEpisodeId === ep.id
                  ? 'bg-cyan-500/10 border-l-2 border-l-cyan-500 shadow-inner'
                  : 'hover:bg-slate-800 border-l-2 border-l-transparent'
                }`}
              >
                <div className="min-w-0 pr-2">
                  <div className={`text-[10px] font-bold uppercase transition-colors ${selectedEpisodeId === ep.id ? 'text-cyan-400' : 'text-slate-500'}`}>
                    {ep.title}
                  </div>
                  <div className={`text-xs truncate mt-1 ${selectedEpisodeId === ep.id ? 'text-white font-medium' : 'text-slate-400'}`}>{ep.subtitle}</div>
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  {ep.status === 'APPROVED' && (
                    <span className="px-1.5 py-0.5 bg-green-500/10 text-green-500 text-[9px] font-black rounded border border-green-500/20 tracking-tighter">
                      OK
                    </span>
                  )}
                  {ep.status === 'GENERATING' && (
                    <Loader2 size={12} className="animate-spin text-blue-400"/>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* MIDDLE COLUMN: Script Editor */}
      <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
        {/* Toolbar */}
        <div className="h-14 border-b border-slate-800 bg-slate-900 flex items-center justify-between px-6 shrink-0 z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold text-white tracking-widest uppercase truncate max-w-[300px]">
              {selectedEpisode.title} <span className="text-slate-500 mx-2">/</span> <span className="text-slate-400">{selectedEpisode.subtitle}</span>
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 text-slate-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-all" title="Like"><ThumbsUp size={16} /></button>
            <div className="w-px h-4 bg-slate-800 mx-1"></div>
            <button className="flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all"><Download size={14} /> 导出</button>
            <button className="flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold text-green-400 bg-green-500/10 border border-green-500/30 rounded-lg hover:bg-green-500/20 transition-all ml-2 shadow-sm"><CheckCircle2 size={14} /> 审核通过</button>
          </div>
        </div>

        {/* Editor Area */}
        <div className="flex-1 overflow-y-auto p-0 md:p-8 font-mono text-sm leading-relaxed text-slate-300 bg-slate-950/40">
          <div className="max-w-3xl mx-auto bg-slate-900 border border-slate-800 shadow-2xl min-h-full p-8 md:p-12 rounded-xl md:rounded-2xl relative">
            {selectedEpisode.content ? (
              <textarea
                className="w-full h-full min-h-[800px] bg-transparent resize-none outline-none border-none focus:ring-0 text-slate-300 whitespace-pre-wrap selection:bg-cyan-500/30 scrollbar-hide"
                value={selectedEpisode.content}
                readOnly
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4 mt-40 opacity-30">
                <FileEdit size={64} />
                <p className="text-sm tracking-widest uppercase">Initializing Content...</p>
              </div>
            )}
          </div>
        </div>

        {/* Editor Footer */}
        <div className="h-8 bg-slate-900 border-t border-slate-800 flex items-center justify-between px-4 text-[10px] text-slate-500 shrink-0 font-mono">
          <div className="flex items-center gap-4">
            <span>STAT: {selectedEpisode.wordCount} WORDS</span>
            <span>ENCODING: UTF-8</span>
          </div>
          <span className="flex items-center gap-1.5 text-green-500 animate-pulse"><Save size={10} /> AUTO-SYNCED</span>
        </div>
      </div>

      {/* RIGHT COLUMN: QC Report */}
      <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col z-10 shadow-2xl">
        <div className="p-4 border-b border-slate-800 flex items-center gap-2 bg-slate-900/50 backdrop-blur">
          <FileCheck size={16} className="text-green-400" />
          <h3 className="font-bold text-white text-xs uppercase tracking-wider">质量检查报告</h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
          {selectedEpisode.qcReport ? (
            <>
              <div className="bg-slate-800/30 rounded-lg p-3 text-[11px] text-slate-500 border border-slate-800/50 italic">
                根据深度创作标准，对第{selectedEpisodeId}集剧本进行全量扫描...
              </div>
              {selectedEpisode.qcReport.checks.map((check: any, idx: number) => (
                <div key={idx} className="space-y-2">
                  <h4 className="text-[11px] font-black text-slate-200 uppercase flex items-center gap-2 tracking-tighter">
                    <span className="w-4 h-4 rounded bg-slate-800 flex items-center justify-center text-[9px] text-cyan-500 border border-cyan-500/20">{idx + 1}</span>
                    {check.title}
                  </h4>
                  <ul className="space-y-2 pl-3 border-l border-slate-800 ml-2">
                    {check.items.map((item: string, i: number) => (
                      <li key={i} className="text-[11px] text-slate-400 leading-relaxed flex items-start gap-2">
                        <div className="mt-1 w-1 h-1 rounded-full bg-cyan-500 opacity-40 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              <div className="mt-6 pt-4 border-t border-slate-800">
                <div className="bg-green-500/5 border border-green-500/10 rounded-xl p-4 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center font-black text-lg shadow-lg shadow-green-500/20">{selectedEpisode.qcReport.score}</div>
                  <div>
                    <div className="text-[10px] text-green-400 font-black tracking-widest uppercase">Verified Pass</div>
                    <div className="text-[9px] text-slate-500 leading-tight">此批次创作质量卓越，符合归档标准。</div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center text-slate-600 mt-20 opacity-20"><Search size={48} className="mx-auto mb-4" /><p className="text-xs uppercase font-bold">Scanning...</p></div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScriptTab;
