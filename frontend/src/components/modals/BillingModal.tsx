import React, { useState, useEffect } from 'react';
import { X, Receipt, TrendingUp, Calendar, Cpu, Zap, CreditCard, ChevronDown, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { billingApi } from '../../services/api';

interface BillingModalProps {
  onClose: () => void;
}

interface CreditsInfo {
  balance: number;
  monthly_granted: number;
  monthly_credits: number;
  monthly_consumed: number;
  next_grant_at: string | null;
  tier: string;
  tier_display: string;
  pricing: {
    base: Record<string, number>;
    token: {
      enabled: boolean;
      input_per_1k: number;
      output_per_1k: number;
    };
  };
}

interface BillingRecord {
  id: string;
  type: string;
  credits: number;
  balance_after: number;
  description: string;
  reference_id?: string;
  created_at: string | null;
}

const BillingModal: React.FC<BillingModalProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<'USAGE' | 'PRICING'>('USAGE');
  const [loading, setLoading] = useState(true);
  const [creditsInfo, setCreditsInfo] = useState<CreditsInfo | null>(null);
  const [records, setRecords] = useState<BillingRecord[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [creditsRes, recordsRes] = await Promise.all([
        billingApi.getCreditsInfo(),
        billingApi.getRecords(20, 0)
      ]);
      setCreditsInfo(creditsRes.data);
      setRecords(recordsRes.data.records || []);
    } catch (error) {
      console.error('加载账单数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'consume': return 'text-red-400';
      case 'grant': return 'text-green-400';
      case 'recharge': return 'text-cyan-400';
      case 'refund': return 'text-yellow-400';
      default: return 'text-slate-400';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'consume': return '消费';
      case 'grant': return '赠送';
      case 'recharge': return '充值';
      case 'refund': return '退还';
      default: return type;
    }
  };

  // 本月消耗（从后端获取精确值）
  const monthlyConsumed = creditsInfo?.monthly_consumed || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative bg-slate-900 border border-slate-800 w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-400">
                <Receipt size={20} />
             </div>
             <div>
                <h2 className="text-xl font-bold text-white">积分与账单</h2>
                <p className="text-xs text-slate-500">Credits & Billing</p>
             </div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="animate-spin text-cyan-400" size={32} />
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <CreditCard size={48} />
                  </div>
                  <p className="text-sm text-slate-400 mb-1">当前积分</p>
                  <div className="text-3xl font-bold text-white font-mono">
                    {creditsInfo?.balance.toLocaleString() || 0}
                  </div>
                  <div className="mt-3 text-xs text-cyan-400 flex items-center gap-1">
                    <Zap size={12} /> {creditsInfo?.tier_display || '免费版'}
                  </div>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <TrendingUp size={48} />
                  </div>
                  <p className="text-sm text-slate-400 mb-1">本月消耗</p>
                  <div className="text-3xl font-bold text-white font-mono">{monthlyConsumed.toLocaleString()}</div>
                  <div className="mt-3 w-full bg-slate-700 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all"
                      style={{ width: `${Math.min(100, (monthlyConsumed / (creditsInfo?.monthly_credits || 1)) * 100)}%` }}
                    />
                  </div>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Calendar size={48} />
                  </div>
                  <p className="text-sm text-slate-400 mb-1">每月赠送</p>
                  <div className="text-3xl font-bold text-slate-300 font-mono">
                    {creditsInfo?.monthly_credits.toLocaleString() || 0}
                  </div>
                  <p className="mt-3 text-xs text-slate-500">
                    下次发放: {creditsInfo?.next_grant_at ? new Date(creditsInfo.next_grant_at).toLocaleDateString('zh-CN') : '-'}
                  </p>
                </div>
              </div>

              {/* Tab Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setActiveTab('USAGE')}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                      activeTab === 'USAGE' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    消费记录
                  </button>
                  <button
                    onClick={() => setActiveTab('PRICING')}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                      activeTab === 'PRICING' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    积分定价
                  </button>
                </div>
              </div>

              {activeTab === 'USAGE' ? (
                /* Records List */
                <div className="border border-slate-800 rounded-xl overflow-hidden">
                  <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-800 grid grid-cols-12 gap-4 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    <div className="col-span-5">描述</div>
                    <div className="col-span-2 text-center">类型</div>
                    <div className="col-span-3 text-right">积分变动</div>
                    <div className="col-span-2 text-right">时间</div>
                  </div>

                  <div className="bg-slate-900/20 divide-y divide-slate-800/50">
                    {records.length > 0 ? records.map((record) => (
                      <div key={record.id} className="grid grid-cols-12 gap-4 px-4 py-3.5 items-center hover:bg-slate-800/30 transition-colors">
                        <div className="col-span-5">
                          <div className="text-sm text-slate-200">{record.description}</div>
                        </div>
                        <div className="col-span-2 text-center">
                          <span className={`text-xs px-2 py-0.5 rounded ${getTypeColor(record.type)} bg-slate-800`}>
                            {getTypeLabel(record.type)}
                          </span>
                        </div>
                        <div className="col-span-3 text-right">
                          <span className={`text-sm font-mono font-bold ${record.credits > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {record.credits > 0 ? '+' : ''}{record.credits.toLocaleString()}
                          </span>
                        </div>
                        <div className="col-span-2 text-right text-xs text-slate-500">
                          {formatTime(record.created_at)}
                        </div>
                      </div>
                    )) : (
                      <div className="p-8 text-center text-slate-500 text-sm">暂无记录</div>
                    )}
                  </div>
                  {records.length > 0 && (
                    <div className="px-4 py-2 bg-slate-900/80 border-t border-slate-800 text-center">
                      <button className="text-xs text-slate-400 hover:text-white flex items-center justify-center gap-1 w-full">
                        查看更多 <ChevronDown size={12} />
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                /* Pricing Info */
                <div className="space-y-4">
                  <div className="border border-slate-800 rounded-xl overflow-hidden">
                    <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-800">
                      <h3 className="text-sm font-medium text-white flex items-center gap-2">
                        <Cpu size={16} className="text-cyan-400" /> 基础费用（每次任务固定收取）
                      </h3>
                    </div>
                    <div className="p-4 space-y-3">
                      {creditsInfo?.pricing.base && Object.entries(creditsInfo.pricing.base).map(([key, value]) => (
                        <div key={key} className="flex justify-between items-center">
                          <span className="text-slate-400">
                            {key === 'breakdown' ? '剧情拆解' :
                             key === 'script' ? '剧本生成' :
                             key === 'qa' ? '质检校验' :
                             key === 'retry' ? '任务重试' : key}
                          </span>
                          <span className="text-white font-mono">{value} 积分/次</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="border border-slate-800 rounded-xl overflow-hidden">
                    <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-800">
                      <h3 className="text-sm font-medium text-white flex items-center gap-2">
                        <Zap size={16} className="text-yellow-400" /> Token 费用
                        {creditsInfo?.pricing.token.enabled ? (
                          <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400">已启用</span>
                        ) : (
                          <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-400">未启用</span>
                        )}
                      </h3>
                    </div>
                    <div className="p-4 space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">输入 Token</span>
                        <span className="text-white font-mono">{creditsInfo?.pricing.token.input_per_1k || 1} 积分/1K tokens</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">输出 Token</span>
                        <span className="text-white font-mono">{creditsInfo?.pricing.token.output_per_1k || 2} 积分/1K tokens</span>
                      </div>
                      {!creditsInfo?.pricing.token.enabled && (
                        <p className="text-xs text-slate-500 mt-2">
                          Token 计费未启用，当前仅收取基础费用
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="border border-slate-800 rounded-xl p-4 bg-slate-800/20">
                    <p className="text-sm text-slate-400">
                      <span className="text-cyan-400 font-medium">充值比例：</span> 1 元 = 100 积分
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default BillingModal;
