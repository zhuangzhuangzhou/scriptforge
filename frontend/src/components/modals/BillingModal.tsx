import React, { useState, useEffect } from 'react';
import { X, Receipt, TrendingUp, Calendar, Cpu, Zap, CreditCard, ChevronDown, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { billingApi } from '../../services/api';

interface BillingModalProps {
  onClose: () => void;
}

interface CreditsInfo {
  credits: number;  // 积分余额
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
  const [loadingMore, setLoadingMore] = useState(false);
  const [creditsInfo, setCreditsInfo] = useState<CreditsInfo | null>(null);
  const [records, setRecords] = useState<BillingRecord[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const PAGE_SIZE = 20;

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [creditsRes, recordsRes] = await Promise.all([
        billingApi.getCreditsInfo(),
        billingApi.getRecords(PAGE_SIZE, 0)
      ]);
      setCreditsInfo(creditsRes.data);
      const newRecords = recordsRes.data.records || [];
      setRecords(newRecords);
      setHasMore(newRecords.length >= PAGE_SIZE);
    } catch (error) {
      console.error('加载账单数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const recordsRes = await billingApi.getRecords(PAGE_SIZE, records.length);
      const newRecords = recordsRes.data.records || [];
      setRecords(prev => [...prev, ...newRecords]);
      setHasMore(newRecords.length >= PAGE_SIZE);
    } catch (error) {
      console.error('加载更多记录失败:', error);
    } finally {
      setLoadingMore(false);
    }
  };

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    // 格式化为 YYYY-MM-DD HH:mm:ss
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
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
        className="relative bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 w-full max-w-3xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/60 bg-slate-900/50">
          <div className="flex items-center gap-2.5">
             <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-400">
                <Receipt size={16} />
             </div>
             <div>
                <h2 className="text-base font-semibold text-white">积分与账单</h2>
                <p className="text-[10px] text-slate-500">Credits & Billing</p>
             </div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors p-1">
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="animate-spin text-cyan-400" size={28} />
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <CreditCard size={40} />
                  </div>
                  <p className="text-xs text-slate-400 mb-0.5">当前积分</p>
                  <div className="text-2xl font-bold text-white font-mono">
                    {creditsInfo?.credits.toLocaleString() || 0}
                  </div>
                  <div className="mt-2 text-[10px] text-cyan-400 flex items-center gap-1">
                    <Zap size={10} /> {creditsInfo?.tier_display || '免费版'}
                  </div>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <TrendingUp size={40} />
                  </div>
                  <p className="text-xs text-slate-400 mb-0.5">本月消耗</p>
                  <div className="text-2xl font-bold text-white font-mono">{monthlyConsumed.toLocaleString()}</div>
                  <div className="mt-2 w-full bg-slate-700 rounded-full h-1 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all"
                      style={{ width: `${Math.min(100, (monthlyConsumed / (creditsInfo?.monthly_credits || 1)) * 100)}%` }}
                    />
                  </div>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Calendar size={40} />
                  </div>
                  <p className="text-xs text-slate-400 mb-0.5">每月赠送</p>
                  <div className="text-2xl font-bold text-slate-300 font-mono">
                    {creditsInfo?.monthly_credits.toLocaleString() || 0}
                  </div>
                  <p className="mt-2 text-[10px] text-slate-500">
                    下次发放: {creditsInfo?.next_grant_at ? new Date(creditsInfo.next_grant_at).toLocaleDateString('zh-CN') : '-'}
                  </p>
                </div>
              </div>

              {/* Tab Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex gap-0.5 bg-slate-800/50 p-0.5 rounded-md border border-slate-700/50">
                  <button
                    onClick={() => setActiveTab('USAGE')}
                    className={`px-3 py-1 text-xs font-medium rounded transition-all ${
                      activeTab === 'USAGE' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    消费记录
                  </button>
                  <button
                    onClick={() => setActiveTab('PRICING')}
                    className={`px-3 py-1 text-xs font-medium rounded transition-all ${
                      activeTab === 'PRICING' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    积分定价
                  </button>
                </div>
              </div>

              {activeTab === 'USAGE' ? (
                /* Records List */
                <div className="border border-slate-700/50 rounded-lg overflow-hidden">
                  <div className="bg-slate-800/30 px-3 py-2 border-b border-slate-700/50 grid grid-cols-12 gap-2 text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                    <div className="col-span-4">描述</div>
                    <div className="col-span-2 text-center">类型</div>
                    <div className="col-span-2 text-right">积分变动</div>
                    <div className="col-span-4 text-right">时间</div>
                  </div>

                  <div className="bg-slate-900/20 divide-y divide-slate-800/30 max-h-[280px] overflow-y-auto">
                    {records.length > 0 ? records.map((record) => (
                      <div key={record.id} className="grid grid-cols-12 gap-2 px-3 py-2 items-center hover:bg-slate-800/20 transition-colors">
                        <div className="col-span-4">
                          <div className="text-xs text-slate-300 truncate" title={record.description}>{record.description}</div>
                        </div>
                        <div className="col-span-2 text-center">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${getTypeColor(record.type)} bg-slate-800/80`}>
                            {getTypeLabel(record.type)}
                          </span>
                        </div>
                        <div className="col-span-2 text-right">
                          <span className={`text-xs font-mono font-semibold ${record.credits > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {record.credits > 0 ? '+' : ''}{record.credits.toLocaleString()}
                          </span>
                        </div>
                        <div className="col-span-4 text-right text-[10px] text-slate-500 font-mono">
                          {formatTime(record.created_at)}
                        </div>
                      </div>
                    )) : (
                      <div className="p-6 text-center text-slate-500 text-xs">暂无记录</div>
                    )}
                  </div>
                  {records.length > 0 && (
                    <div className="px-3 py-1.5 bg-slate-800/30 border-t border-slate-700/50 text-center">
                      {hasMore ? (
                        <button
                          onClick={loadMore}
                          disabled={loadingMore}
                          className="text-[10px] text-slate-400 hover:text-white flex items-center justify-center gap-1 w-full disabled:opacity-50"
                        >
                          {loadingMore ? (
                            <>
                              <Loader2 size={10} className="animate-spin" /> 加载中...
                            </>
                          ) : (
                            <>
                              查看更多 <ChevronDown size={10} />
                            </>
                          )}
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-500">没有更多了</span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                /* Pricing Info */
                <div className="space-y-3">
                  <div className="border border-slate-700/50 rounded-lg overflow-hidden">
                    <div className="bg-slate-800/30 px-3 py-2 border-b border-slate-700/50">
                      <h3 className="text-xs font-medium text-white flex items-center gap-1.5">
                        <Cpu size={14} className="text-cyan-400" /> 基础费用（每次任务固定收取）
                      </h3>
                    </div>
                    <div className="p-3 space-y-2">
                      {creditsInfo?.pricing.base && Object.entries(creditsInfo.pricing.base).map(([key, value]) => (
                        <div key={key} className="flex justify-between items-center text-xs">
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

                  <div className="border border-slate-700/50 rounded-lg overflow-hidden">
                    <div className="bg-slate-800/30 px-3 py-2 border-b border-slate-700/50">
                      <h3 className="text-xs font-medium text-white flex items-center gap-1.5">
                        <Zap size={14} className="text-yellow-400" /> Token 费用
                      </h3>
                    </div>
                    <div className="p-3">
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Token 费用根据实际使用的 AI 模型分别计算，不同模型的输入/输出 Token 单价可能不同。
                        具体费用以任务完成后的实际消耗为准。
                      </p>
                    </div>
                  </div>

                  <div className="border border-slate-700/50 rounded-lg p-3 bg-slate-800/20">
                    <p className="text-xs text-slate-400">
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
