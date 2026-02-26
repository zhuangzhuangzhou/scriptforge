import React, { useState } from 'react';
import { X, Gift, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { message } from 'antd';
import { redeemApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface RedeemCodeModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

const RedeemCodeModal: React.FC<RedeemCodeModalProps> = ({ onClose, onSuccess }) => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    type?: string;
    credits_granted?: number;
    tier_after?: string;
    new_balance?: number;
    message?: string;
  } | null>(null);

  const { refreshUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedCode = code.trim().toUpperCase();
    if (!trimmedCode) {
      message.warning('请输入兑换码');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await redeemApi.useCode(trimmedCode);
      setResult(response.data);

      // 刷新用户信息以更新积分显示
      if (refreshUser) {
        await refreshUser();
      }

      if (onSuccess) {
        onSuccess();
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || '兑换失败，请检查兑换码是否正确';
      setResult({
        success: false,
        message: errorMsg
      });
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
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center">
              <Gift className="text-emerald-400" size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">兑换码</h2>
              <p className="text-xs text-slate-400">输入兑换码获取积分或升级</p>
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
            {!result ? (
              <motion.form
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handleSubmit}
                className="space-y-4"
              >
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    请输入兑换码
                  </label>
                  <input
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value.toUpperCase())}
                    placeholder="例如：ABCD1234EFGH"
                    disabled={loading}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-all text-center text-lg tracking-widest font-mono uppercase disabled:opacity-50"
                    autoFocus
                    maxLength={32}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !code.trim()}
                  className="w-full py-3 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-bold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      兑换中...
                    </>
                  ) : (
                    <>
                      <Gift size={18} />
                      立即兑换
                    </>
                  )}
                </button>

                <p className="text-xs text-slate-500 text-center">
                  兑换码不区分大小写，每个兑换码只能使用一次
                </p>
              </motion.form>
            ) : (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-4"
              >
                {result.success ? (
                  <>
                    <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="text-emerald-400" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">兑换成功</h3>
                    <p className="text-slate-400 mb-4">{result.message}</p>

                    {result.type === 'credits' && (
                      <div className="bg-slate-800/50 rounded-xl p-4 mb-4">
                        <div className="text-3xl font-bold text-emerald-400 mb-1">
                          +{result.credits_granted?.toLocaleString()}
                        </div>
                        <div className="text-sm text-slate-400">积分已到账</div>
                        <div className="text-xs text-slate-500 mt-2">
                          当前余额: {result.new_balance?.toLocaleString()} 积分
                        </div>
                      </div>
                    )}

                    {result.type === 'tier_upgrade' && (
                      <div className="bg-slate-800/50 rounded-xl p-4 mb-4">
                        <div className="text-xl font-bold text-purple-400 mb-1">
                          已升级到 {result.tier_after}
                        </div>
                        <div className="text-sm text-slate-400">享受更多权益</div>
                      </div>
                    )}

                    <button
                      onClick={handleClose}
                      className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-all"
                    >
                      完成
                    </button>
                  </>
                ) : (
                  <>
                    <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
                      <AlertCircle className="text-red-400" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">兑换失败</h3>
                    <p className="text-slate-400 mb-6">{result.message}</p>

                    <div className="flex gap-3">
                      <button
                        onClick={() => {
                          setResult(null);
                          setCode('');
                        }}
                        className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-all"
                      >
                        重新输入
                      </button>
                      <button
                        onClick={handleClose}
                        className="flex-1 py-3 bg-slate-800/50 hover:bg-slate-800 text-slate-300 font-medium rounded-xl transition-all"
                      >
                        关闭
                      </button>
                    </div>
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};

export default RedeemCodeModal;
