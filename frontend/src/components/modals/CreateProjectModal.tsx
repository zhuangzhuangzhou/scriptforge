import React, { useState } from 'react';
import { X, Sparkles, BookOpen, Tag, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { message } from 'antd';
import { UserTier } from '../../types';
import { projectApi } from '../../services/api';

interface CreateProjectModalProps {
  onClose: () => void;
  onSubmit: (projectData: any) => void;
  userTier?: UserTier;
  currentProjectCount?: number;
}

const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  onClose,
  onSubmit,
  userTier = 'FREE',
}) => {
  const [formData, setFormData] = useState({
    name: '',
    type: '悬疑惊悚',
    description: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setIsSubmitting(true);
    try {
      const response = await projectApi.createProject({
        name: formData.name,
        novel_type: formData.type,
        description: formData.description,
      });

      onSubmit(response.data);
    } catch (error: any) {
      console.error('创建项目失败:', error);
      const errorDetail = error.response?.data?.detail || '';

      if (error.response?.status === 403 && (errorDetail.includes('积分') || errorDetail.includes('配额'))) {
        message.error('积分不足，请充值后再试');
      } else {
        const errorMessage = errorDetail || '创建项目失败，请稍后重试';
        message.error(errorMessage);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const novelTypes = [
    { value: '悬疑惊悚', label: '悬疑惊悚', icon: '🔮', gradient: 'from-purple-500/20 to-indigo-500/20', border: 'border-purple-500/30', text: 'text-purple-400' },
    { value: '都市言情', label: '都市言情', icon: '🌆', gradient: 'from-pink-500/20 to-rose-500/20', border: 'border-pink-500/30', text: 'text-pink-400' },
    { value: '玄幻奇幻', label: '玄幻奇幻', icon: '✨', gradient: 'from-violet-500/20 to-purple-500/20', border: 'border-violet-500/30', text: 'text-violet-400' },
    { value: '武侠仙侠', label: '武侠仙侠', icon: '⚔️', gradient: 'from-red-500/20 to-orange-500/20', border: 'border-red-500/30', text: 'text-red-400' },
    { value: '科幻末世', label: '科幻末世', icon: '🚀', gradient: 'from-cyan-500/20 to-blue-500/20', border: 'border-cyan-500/30', text: 'text-cyan-400' },
    { value: '历史军事', label: '历史军事', icon: '🏯', gradient: 'from-amber-500/20 to-orange-500/20', border: 'border-amber-500/30', text: 'text-amber-400' },
    { value: '游戏竞技', label: '游戏竞技', icon: '🎮', gradient: 'from-green-500/20 to-emerald-500/20', border: 'border-green-500/30', text: 'text-green-400' },
    { value: '灵异恐怖', label: '灵异恐怖', icon: '👻', gradient: 'from-slate-500/20 to-gray-500/20', border: 'border-slate-500/30', text: 'text-slate-400' },
    { value: '青春校园', label: '青春校园', icon: '🎓', gradient: 'from-blue-500/20 to-indigo-500/20', border: 'border-blue-500/30', text: 'text-blue-400' },
    { value: '古代言情', label: '古代言情', icon: '🌸', gradient: 'from-rose-500/20 to-pink-500/20', border: 'border-rose-500/30', text: 'text-rose-400' },
    { value: '现代言情', label: '现代言情', icon: '💕', gradient: 'from-fuchsia-500/20 to-pink-500/20', border: 'border-fuchsia-500/30', text: 'text-fuchsia-400' },
    { value: '幻想修真', label: '幻想修真', icon: '🌟', gradient: 'from-indigo-500/20 to-purple-500/20', border: 'border-indigo-500/30', text: 'text-indigo-400' },
    { value: '商战职场', label: '商战职场', icon: '💼', gradient: 'from-gray-500/20 to-slate-500/20', border: 'border-gray-500/30', text: 'text-gray-400' },
    { value: '轻小说', label: '轻小说', icon: '📚', gradient: 'from-teal-500/20 to-cyan-500/20', border: 'border-teal-500/30', text: 'text-teal-400' },
    { value: '二次元', label: '二次元', icon: '🎨', gradient: 'from-sky-500/20 to-blue-500/20', border: 'border-sky-500/30', text: 'text-sky-400' },
  ];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* 背景遮罩 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* 弹窗主体 */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative w-full max-w-2xl"
        >
          {/* 装饰性背景光晕 */}
          <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-purple-500/20 rounded-2xl blur-2xl" />

          {/* 主卡片 */}
          <div className="relative bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden">

            {/* Header */}
            <div className="relative px-6 py-4 border-b border-slate-800/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                    <Sparkles size={20} className="text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">创建新项目</h2>
                    <p className="text-xs text-slate-400 mt-0.5">开启您的 AI 改编之旅</p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="w-9 h-9 rounded-lg bg-slate-800/50 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-all group"
                >
                  <X size={18} className="group-hover:rotate-90 transition-transform duration-300" />
                </button>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              {/* 项目名称 */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                  <BookOpen size={16} className="text-cyan-400" />
                  项目名称
                </label>
                <div className="relative group">
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={e => setFormData({...formData, name: e.target.value})}
                    className="w-full bg-slate-800/60 border border-slate-700/50 hover:border-cyan-500/50 focus:border-cyan-500 rounded-xl px-4 py-2.5 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-cyan-500/20 outline-none transition-all"
                    placeholder="为您的项目起个响亮的名字..."
                  />
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                </div>
              </div>

              {/* 小说类型 */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                  <Tag size={16} className="text-blue-400" />
                  小说类型
                </label>
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {novelTypes.map((type) => {
                    const isSelected = formData.type === type.value;
                    return (
                      <motion.button
                        key={type.value}
                        type="button"
                        onClick={() => setFormData({...formData, type: type.value})}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className={`relative p-2.5 rounded-lg border text-left transition-all duration-200 ${
                          isSelected
                            ? `${type.border} bg-gradient-to-br ${type.gradient} shadow-lg`
                            : 'border-slate-700/50 bg-slate-800/30 hover:border-slate-600 hover:bg-slate-800/50'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{type.icon}</span>
                          <span className={`text-xs font-medium ${isSelected ? type.text : 'text-slate-400'}`}>
                            {type.label}
                          </span>
                        </div>
                        {isSelected && (
                          <motion.div
                            layoutId="selected-type"
                            className="absolute inset-0 rounded-lg border-2 border-cyan-400/50"
                            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                          />
                        )}
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              {/* 项目描述 */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                  <FileText size={16} className="text-purple-400" />
                  项目描述
                  <span className="text-xs text-slate-500 font-normal">(可选)</span>
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={e => setFormData({...formData, description: e.target.value})}
                  className="w-full bg-slate-800/60 border border-slate-700/50 hover:border-cyan-500/50 focus:border-cyan-500 rounded-xl px-4 py-2.5 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-cyan-500/20 outline-none transition-all resize-none"
                  placeholder="简要描述您的故事核心，帮助 AI 更好地理解创作方向..."
                />
              </div>

              {/* Actions */}
              <div className="pt-4 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 rounded-lg transition-all"
                >
                  取消
                </button>
                <motion.button
                  type="submit"
                  disabled={isSubmitting}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="relative px-5 py-2 text-sm font-bold rounded-lg overflow-hidden group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {/* 渐变背景 */}
                  <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 to-blue-600" />
                  <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />

                  {/* 按钮文字 */}
                  <span className="relative flex items-center gap-2 text-white">
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        创建中...
                      </>
                    ) : (
                      <>
                        <Sparkles size={14} />
                        创建项目
                      </>
                    )}
                  </span>
                </motion.button>
              </div>
            </form>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CreateProjectModal;
