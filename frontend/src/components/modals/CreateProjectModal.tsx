import React, { useState } from 'react';
import { X, UploadCloud, AlignJustify, Settings, Lock } from 'lucide-react';
import { motion } from 'framer-motion';
import { UserTier } from '../../types';

interface CreateProjectModalProps {
  onClose: () => void;
  onSubmit: (projectData: any) => void;
  userTier?: UserTier;
  currentProjectCount?: number;
}

const TIER_LIMITS = {
  FREE: { batch: 3, projects: 999 }, // 暂时调高限制
  CREATOR: { batch: 6, projects: 999 },
  STUDIO: { batch: 12, projects: 999 },
  ENTERPRISE: { batch: 9999, projects: 9999 },
};

const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ onClose, onSubmit, userTier = 'FREE', currentProjectCount = 0 }) => {
  const limits = TIER_LIMITS[userTier];
  const [formData, setFormData] = useState({
    name: '',
    type: '悬疑/惊悚',
    description: '',
    batchSize: Math.min(5, limits.batch).toString(),
    splitRule: '按章节',
  });

  // 暂时移除项目限制逻辑
  const isProjectLimitReached = false; 

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // In a real app, we would process the file here
    onSubmit({
        ...formData,
        id: Math.random().toString(36).substr(2, 9),
        updatedAt: '刚刚',
        progress: 0,
        status: '配置中',
        totalChapters: 45, // mocked
        processedChapters: 0
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="relative bg-slate-900 border border-slate-800 w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-8 border-b border-slate-800 bg-slate-900/50">
          <div>
            <h2 className="text-2xl font-bold text-white">创建新项目</h2>
            <p className="text-slate-500 text-sm mt-1">上传您的小说源文件并配置初始参数</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors p-2 hover:bg-slate-800 rounded-full">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-8 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            {/* Left Column: Basic Info */}
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-300">项目名称 (小说名)</label>
                <input 
                  type="text" 
                  required
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 outline-none transition-all placeholder:text-slate-600"
                  placeholder="例如：三体II·黑暗森林"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-300">小说类型</label>
                <select 
                   value={formData.type}
                   onChange={e => setFormData({...formData, type: e.target.value})}
                   className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-cyan-500/50 outline-none appearance-none"
                >
                  <option>悬疑/惊悚</option>
                  <option>科幻/奇幻</option>
                  <option>古装/历史</option>
                  <option>都市/情感</option>
                  <option>喜剧</option>
                </select>
              </div>

              <div className="space-y-2">
                 <label className="text-sm font-semibold text-slate-300">项目描述</label>
                 <textarea 
                    rows={5}
                    value={formData.description}
                    onChange={e => setFormData({...formData, description: e.target.value})}
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-cyan-500/50 outline-none resize-none placeholder:text-slate-600"
                    placeholder="简要描述故事核心梗概，帮助 AI 更好理解人物动机和世界观..."
                 />
              </div>
            </div>

            {/* Right Column: Processing Logic */}
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-300">小说源文件 (.txt, .doc)</label>
                <div className="border-2 border-dashed border-slate-700 rounded-2xl p-10 flex flex-col items-center justify-center text-center hover:border-cyan-500/50 hover:bg-slate-800/30 transition-all cursor-pointer group bg-slate-800/20">
                  <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center mb-4 group-hover:bg-cyan-500/10 group-hover:text-cyan-400 transition-colors shadow-inner">
                    <UploadCloud size={28} className="text-slate-400 group-hover:text-cyan-400" />
                  </div>
                  <p className="text-base text-slate-300 font-medium">点击或拖拽上传</p>
                  <p className="text-xs text-slate-500 mt-2 leading-relaxed">支持 TXT, DOCX 格式 (最大 10MB)<br/>系统将自动分析章节结构</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-5">
                 <div className="space-y-2">
                    <label className="text-sm font-semibold text-slate-300 flex items-center justify-between">
                        <span className="flex items-center gap-2"><AlignJustify size={16} className="text-cyan-400" /> 批次大小</span>
                    </label>
                    <div className="relative">
                        <input 
                        type="number" 
                        value={formData.batchSize}
                        onChange={e => setFormData({...formData, batchSize: e.target.value})}
                        className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-cyan-500/50 outline-none font-mono"
                        />
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-slate-500">章</span>
                    </div>
                    <p className="text-[10px] text-slate-500">当前等级上限: {limits.batch}章</p>
                 </div>
                 <div className="space-y-2">
                    <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                        <Settings size={16} className="text-cyan-400" /> 拆分规则
                    </label>
                    <select 
                       value={formData.splitRule}
                       onChange={e => setFormData({...formData, splitRule: e.target.value})}
                       className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-cyan-500/50 outline-none"
                    >
                      <option>按章节 (第X章)</option>
                      <option>按字数 (2000字)</option>
                      <option>智能语义拆分</option>
                    </select>
                 </div>
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-800 flex justify-end items-center gap-4">
             <button 
               type="button" 
               onClick={onClose}
               className="px-6 py-3 text-sm font-medium text-slate-400 hover:text-white transition-colors rounded-xl hover:bg-slate-800"
             >
               取消
             </button>
             <button 
               type="submit"
               className="px-8 py-3 text-sm font-bold rounded-xl shadow-lg transition-all flex items-center gap-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white transform hover:scale-[1.02] active:scale-[0.98] shadow-cyan-500/20"
             >
               创建项目
             </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

export default CreateProjectModal;
