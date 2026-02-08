import React from 'react';
import {
  Hash, Type, CheckCircle2, Activity, BookOpen, LayoutTemplate, FileEdit,
  Sliders, BrainCircuit, Cpu, Database, Upload, Loader2, SplitSquareVertical,
  RefreshCw, Trash2, Lightbulb, BookText
} from 'lucide-react';

interface ConfigTabProps {
  project: any;
  formData: {
    name: string;
    novel_type: string;
    description: string;
    batch_size: number;
    chapter_split_rule: string;
    breakdown_model: string;
    script_model: string;
  };
  onFormChange: (field: string, value: any) => void;
  onSaveConfig: () => void;
  saving: boolean;
  uploading: boolean;
  splitting: boolean;
  onFileUpload: () => void;
  onSplit: () => void;
  getStatusText: (status: string) => string;
}

// 统计卡片组件
const StatCard = ({ icon: Icon, label, value, colorClass }: { icon: any, label: string, value: string | number, colorClass: string }) => (
  <div className="bg-slate-900/40 border border-slate-800 p-4 rounded-2xl flex items-center gap-4 group hover:border-slate-700 transition-all shadow-lg">
    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorClass} shadow-inner`}>
      <Icon size={20} />
    </div>
    <div>
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-bold text-white font-mono">{value}</p>
    </div>
  </div>
);

const ConfigTab: React.FC<ConfigTabProps> = ({
  project,
  formData,
  onFormChange,
  onSaveConfig,
  saving,
  uploading,
  splitting,
  onFileUpload,
  onSplit,
  getStatusText
}) => {
  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* 左侧内容 - 68% */}
      <div className="flex-1 lg:flex-[0.68] space-y-6 overflow-y-auto pr-2 custom-scrollbar">
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={Hash}
            label="总章节数"
            value={`${project.total_chapters || 0} 章`}
            colorClass="bg-blue-500/10 text-blue-400"
          />
          <StatCard
            icon={Type}
            label="预估字数"
            value={`${project.total_words ? (project.total_words / 10000).toFixed(1) : '0'} 万字`}
            colorClass="bg-purple-500/10 text-purple-400"
          />
          <StatCard
            icon={CheckCircle2}
            label="已拆解章节"
            value={`${project.processed_chapters || 0} / ${project.total_chapters || 0}`}
            colorClass="bg-emerald-500/10 text-emerald-400"
          />
          <StatCard
            icon={Activity}
            label="当前状态"
            value={getStatusText(project.status)}
            colorClass="bg-cyan-500/10 text-cyan-400"
          />
        </div>

        {/* 基础信息 */}
        <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 flex items-center gap-2"><BookOpen size={14}/> 小说名称</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => onFormChange('name', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none transition-all"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 flex items-center gap-2"><LayoutTemplate size={14}/> 小说类型</label>
              <select
                value={formData.novel_type}
                onChange={(e) => onFormChange('novel_type', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
              >
                <option value="悬疑惊悚">悬疑惊悚</option>
                <option value="都市言情">都市言情</option>
                <option value="玄幻奇幻">玄幻奇幻</option>
                <option value="武侠仙侠">武侠仙侠</option>
                <option value="科幻末世">科幻末世</option>
                <option value="历史军事">历史军事</option>
                <option value="游戏竞技">游戏竞技</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400 flex items-center gap-2"><FileEdit size={14}/> 小说简介</label>
            <textarea
              rows={5}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 text-sm text-slate-300 focus:ring-1 focus:ring-cyan-500 outline-none resize-none leading-relaxed"
              value={formData.description}
              onChange={(e) => onFormChange('description', e.target.value)}
              placeholder="请输入小说简介..."
            />
          </div>
        </div>

        {/* 配置卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider"><Sliders size={14} className="text-cyan-400"/> 核心逻辑</h3>
            <div className="space-y-2">
              <label className="text-[10px] text-slate-400 uppercase font-bold">拆剧批次</label>
              <input
                type="number"
                value={formData.batch_size}
                onChange={(e) => onFormChange('batch_size', parseInt(e.target.value) || 5)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:ring-1 focus:ring-cyan-500 outline-none"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] text-slate-400 uppercase font-bold">章节拆分规则</label>
              <select
                value={typeof formData.chapter_split_rule === 'string' ? formData.chapter_split_rule : 'custom'}
                onChange={(e) => onFormChange('chapter_split_rule', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-cyan-500 outline-none"
              >
                <option value="auto">智能识别 (第X章)</option>
                <option value="blank_line">空行拆分</option>
                <option value="custom">自定义正则</option>
              </select>
            </div>
          </div>
          <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider"><BrainCircuit size={14} className="text-purple-400"/> 剧情拆解模型</h3>
            <div className="space-y-2">
              <label className="text-[10px] text-slate-400 uppercase font-bold">Breakdown Model</label>
              <select className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-cyan-500 outline-none"><option>DeepNarrative-Pro</option><option>GPT-4o</option></select>
            </div>
          </div>
          <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider"><Cpu size={14} className="text-indigo-400"/> 剧集生成模型</h3>
            <div className="space-y-2">
              <label className="text-[10px] text-slate-400 uppercase font-bold">Script Model</label>
              <select className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-cyan-500 outline-none"><option>Gemini-1.5-Pro</option><option>GPT-4o</option></select>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧内容 - 32% - 小说源文件管理 */}
      <div className="flex-1 lg:flex-[0.32] bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col gap-6 h-fit lg:h-auto relative overflow-hidden">
        {/* 标题 */}
        <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider mb-2">
          <Database size={16} className="text-emerald-400"/> 小说源文件
        </h3>

        {/* 内容区域：根据是否有文件显示不同状态 */}
        {!project.original_file_name ? (
          /* 未上传状态 */
          <div
            onClick={onFileUpload}
            className="flex-1 min-h-[300px] border-2 border-dashed border-slate-700 hover:border-emerald-500/50 rounded-xl flex flex-col items-center justify-center gap-4 cursor-pointer group transition-all bg-slate-950/30 hover:bg-slate-900/50"
          >
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={32} className="animate-spin text-emerald-500" />
                <p className="text-xs text-emerald-500 font-bold animate-pulse">正在上传文件...</p>
              </div>
            ) : (
              <>
                <div className="w-16 h-16 rounded-full bg-slate-800 group-hover:bg-emerald-500/10 flex items-center justify-center transition-colors">
                  <Upload size={24} className="text-slate-400 group-hover:text-emerald-400 transition-colors" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-bold text-slate-300 group-hover:text-white transition-colors">点击上传小说文件</p>
                  <p className="text-xs text-slate-500 mt-1">支持 .txt, .docx, .pdf 格式</p>
                </div>
              </>
            )}
          </div>
        ) : (
          /* 已上传状态 */
          <>
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 flex flex-col items-center gap-4 group hover:border-emerald-500/30 transition-all">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 shadow-lg group-hover:scale-110 transition-transform">
                <BookText size={32} className="text-emerald-400" />
              </div>
              <div className="text-center w-full">
                <p className="text-sm font-bold text-white truncate px-2" title={project.original_file_name}>{project.original_file_name}</p>
                <p className="text-xs text-slate-500 mt-1 font-mono">
                  {project.original_file_size ? (project.original_file_size / 1024 / 1024).toFixed(2) : '0.00'} MB
                </p>
              </div>
              <div className="flex items-center gap-2 text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded-full border border-emerald-500/20">
                <CheckCircle2 size={12} /> 文件校验通过
              </div>
            </div>

            <div className="flex flex-col gap-3 mt-auto">
              {/* 根据状态显示主操作按钮 */}
              {project.status === 'uploaded' && (
                <button
                  onClick={onSplit}
                  disabled={splitting}
                  className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-bold shadow-lg shadow-emerald-900/20 flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {splitting ? <Loader2 size={18} className="animate-spin" /> : <SplitSquareVertical size={18} />}
                  {splitting ? '正在拆分...' : '开始智能拆分'}
                </button>
              )}

              {project.status === 'ready' && (
                <div className="w-full py-3 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-xl font-bold flex flex-col items-center justify-center gap-1 text-xs">
                  <span className="flex items-center gap-2"><CheckCircle2 size={14}/> 章节拆分完成</span>
                  <span className="opacity-70">请点击顶部 "项目启动" 进入下一步</span>
                </div>
              )}

              {(project.status === 'parsing' || project.status === 'scripting' || project.status === 'completed') && (
                <div className="w-full py-3 bg-slate-800 text-slate-500 rounded-xl font-bold flex items-center justify-center gap-2 text-xs cursor-not-allowed">
                  <CheckCircle2 size={14}/> 源文件已锁定
                </div>
              )}

              {/* 辅助操作按钮 (仅在 uploaded 或 ready 状态下允许修改) */}
              {(project.status === 'uploaded' || project.status === 'ready') && (
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={onFileUpload}
                    disabled={uploading || splitting}
                    className="py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                    重新上传
                  </button>
                  {project.status === 'ready' ? (
                    <button
                      onClick={onSplit}
                      disabled={splitting}
                      className="py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <RefreshCw size={14} /> 重新拆分
                    </button>
                  ) : (
                    <button className="py-2.5 bg-slate-800 hover:bg-red-900/20 text-slate-300 hover:text-red-400 border border-slate-700 hover:border-red-500/30 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2">
                      <Trash2 size={14} /> 删除文件
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="bg-slate-800/30 rounded-xl p-4 text-[10px] text-slate-500 leading-relaxed border border-slate-800/50">
              <p className="flex gap-2"><Lightbulb size={12} className="text-amber-400 shrink-0"/> <span>重新上传将覆盖现有文件，并建议重新执行拆分流程。</span></p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ConfigTab;
