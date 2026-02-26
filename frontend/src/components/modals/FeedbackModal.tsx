import React, { useState } from 'react';
import { X, MessageSquare, Loader2, CheckCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { message } from 'antd';
import { feedbackApi } from '../../services/api';

interface FeedbackModalProps {
  onClose: () => void;
}

const FEEDBACK_TYPES = [
  { value: 'suggestion', label: '需求建议', color: 'from-cyan-500 to-blue-500' },
  { value: 'bug', label: '问题报告', color: 'from-orange-500 to-red-500' },
  { value: 'other', label: '其他', color: 'from-slate-500 to-slate-600' },
];

const FeedbackModal: React.FC<FeedbackModalProps> = ({ onClose }) => {
  const [type, setType] = useState('suggestion');
  const [content, setContent] = useState('');
  const [contact, setContact] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!content.trim()) {
      message.warning('请输入反馈内容');
      return;
    }

    setLoading(true);

    try {
      await feedbackApi.create({
        type,
        content: content.trim(),
        contact: contact.trim() || undefined,
      });
      setSuccess(true);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '提交失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={handleClose} />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative bg-slate-900 border border-slate-800 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
              <MessageSquare className="text-cyan-400" size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">意见反馈</h2>
              <p className="text-xs text-slate-400">您的反馈对我们很重要</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={loading}
            className="text-slate-500 hover:text-white transition-colors disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          <AnimatePresence mode="wait">
            {!success ? (
              <motion.form
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handleSubmit}
                className="space-y-4"
              >
                {/* 反馈类型 */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    反馈类型
                  </label>
                  <div className="flex gap-2">
                    {FEEDBACK_TYPES.map((item) => (
                      <button
                        key={item.value}
                        type="button"
                        onClick={() => setType(item.value)}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                          type === item.value
                            ? `bg-gradient-to-r ${item.color} text-white`
                            : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800 hover:text-white'
                        }`}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 反馈内容 */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    反馈内容 <span className="text-red-400">*</span>
                  </label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="请详细描述您的建议或遇到的问题..."
                    disabled={loading}
                    rows={5}
                    maxLength={5000}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-all resize-none disabled:opacity-50"
                  />
                  <div className="text-xs text-slate-500 text-right mt-1">
                    {content.length}/5000
                  </div>
                </div>

                {/* 联系方式 */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    联系方式 <span className="text-slate-500">(选填)</span>
                  </label>
                  <input
                    type="text"
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                    placeholder="邮箱或微信，方便我们回复您"
                    disabled={loading}
                    maxLength={255}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-all disabled:opacity-50"
                  />
                </div>

                {/* 提交按钮 */}
                <button
                  type="submit"
                  disabled={loading || !content.trim()}
                  className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      提交中...
                    </>
                  ) : (
                    <>
                      <MessageSquare size={18} />
                      提交反馈
                    </>
                  )}
                </button>
              </motion.form>
            ) : (
              <motion.div
                key="success"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-8"
              >
                <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="text-emerald-400" size={32} />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">感谢您的反馈</h3>
                <p className="text-slate-400 mb-6">我们会认真阅读并尽快处理</p>
                <button
                  onClick={handleClose}
                  className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-all"
                >
                  完成
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};

export default FeedbackModal;
