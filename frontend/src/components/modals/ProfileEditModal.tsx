import React, { useState } from 'react';
import { X, User, Loader2, CheckCircle, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { message } from 'antd';
import { authApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface ProfileEditModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

const ProfileEditModal: React.FC<ProfileEditModalProps> = ({ onClose, onSuccess }) => {
  const { user, refreshUser } = useAuth();

  const [username, setUsername] = useState(user?.username || '');
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [avatarSeed, setAvatarSeed] = useState(user?.username || 'default');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [usernameError, setUsernameError] = useState('');

  // 验证用户名格式
  const validateUsername = (value: string) => {
    if (value.length < 3) {
      return '用户名至少 3 个字符';
    }
    if (value.length > 20) {
      return '用户名最多 20 个字符';
    }
    if (!/^[a-zA-Z0-9_]+$/.test(value)) {
      return '用户名只能包含字母、数字和下划线';
    }
    return '';
  };

  const handleUsernameChange = (value: string) => {
    setUsername(value);
    setUsernameError(validateUsername(value));
  };

  // 随机更换头像
  const handleRandomAvatar = () => {
    const newSeed = Math.random().toString(36).substring(7);
    setAvatarSeed(newSeed);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const error = validateUsername(username);
    if (error) {
      setUsernameError(error);
      return;
    }

    setLoading(true);

    try {
      const avatarUrl = `https://api.dicebear.com/7.x/avataaars/svg?seed=${avatarSeed}`;

      await authApi.updateProfile({
        username: username !== user?.username ? username : undefined,
        full_name: fullName || undefined,
        avatar_url: avatarUrl,
      });

      // 刷新用户信息
      if (refreshUser) {
        await refreshUser();
      }

      setSuccess(true);
      onSuccess?.();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '更新失败，请稍后重试');
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
        className="relative bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
              <User className="text-cyan-400" size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">编辑资料</h2>
              <p className="text-xs text-slate-400">修改您的个人信息</p>
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
                className="space-y-5"
              >
                {/* 头像 */}
                <div className="flex flex-col items-center gap-3">
                  <div className="relative">
                    <div className="w-20 h-20 rounded-full border-2 border-slate-700 overflow-hidden bg-slate-800">
                      <img
                        src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${avatarSeed}`}
                        alt="头像"
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleRandomAvatar}
                      className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition-all"
                      title="随机更换头像"
                    >
                      <RefreshCw size={14} />
                    </button>
                  </div>
                  <span className="text-xs text-slate-500">点击刷新按钮随机更换头像</span>
                </div>

                {/* 用户名 */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    用户名 <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => handleUsernameChange(e.target.value)}
                    placeholder="3-20字符，字母数字下划线"
                    disabled={loading}
                    maxLength={20}
                    className={`w-full px-4 py-3 bg-slate-800/50 border rounded-xl text-white placeholder-slate-500 focus:outline-none transition-all disabled:opacity-50 ${
                      usernameError
                        ? 'border-red-500/50 focus:border-red-500'
                        : 'border-slate-700 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20'
                    }`}
                  />
                  {usernameError && (
                    <p className="text-xs text-red-400 mt-1">{usernameError}</p>
                  )}
                </div>

                {/* 昵称 */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    昵称 <span className="text-slate-500">(选填)</span>
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="显示名称"
                    disabled={loading}
                    maxLength={50}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-all disabled:opacity-50"
                  />
                </div>

                {/* 邮箱（只读） */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    邮箱 <span className="text-slate-500">(不可修改)</span>
                  </label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-4 py-3 bg-slate-800/30 border border-slate-700/50 rounded-xl text-slate-500 cursor-not-allowed"
                  />
                </div>

                {/* 提交按钮 */}
                <button
                  type="submit"
                  disabled={loading || !!usernameError || !username}
                  className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      保存中...
                    </>
                  ) : (
                    '保存修改'
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
                <h3 className="text-xl font-bold text-white mb-2">资料已更新</h3>
                <p className="text-slate-400 mb-6">您的个人信息已成功保存</p>
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

export default ProfileEditModal;
