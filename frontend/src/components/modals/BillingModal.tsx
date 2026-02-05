import React, { useState } from 'react';
import { X, Receipt, TrendingUp, Calendar, Download, Server, Cpu, Zap, CreditCard, ChevronDown, Filter } from 'lucide-react';
import { motion } from 'framer-motion';

interface BillingModalProps {
  onClose: () => void;
}

const BillingModal: React.FC<BillingModalProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<'USAGE' | 'HISTORY'>('USAGE');

  // Mock Data for Usage Logs
  const usageLogs = [
    { id: 1, model: 'GPT-4o', task: '剧本大纲生成', tokens: '12,450', cost: 1.85, time: '10分钟前', type: 'reasoning' },
    { id: 2, model: 'Gemini-1.5-Pro', task: '第15章 - 场景扩写', tokens: '145,200', cost: 4.20, time: '2小时前', type: 'generation' },
    { id: 3, model: 'DeepNarrative-Pro', task: '剧情逻辑检查', tokens: '8,500', cost: 0.95, time: '5小时前', type: 'reasoning' },
    { id: 4, model: 'Gemini-1.5-Flash', task: '角色小传生成', tokens: '2,100', cost: 0.05, time: '昨天 14:30', type: 'generation' },
    { id: 5, model: 'Custom-Llama-3', task: '风格润色', tokens: '55,000', cost: 2.50, time: '昨天 09:15', type: 'custom' },
    { id: 6, model: 'GPT-4o', task: '复杂冲突分析', tokens: '3,400', cost: 0.55, time: '10/22 18:00', type: 'reasoning' },
  ];

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
                <h2 className="text-xl font-bold text-white">账单与用量</h2>
                <p className="text-xs text-slate-500">Billing & Usage Statistics</p>
             </div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8">
            
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <CreditCard size={48} />
                    </div>
                    <p className="text-sm text-slate-400 mb-1">当前余额 (Balance)</p>
                    <div className="text-3xl font-bold text-white font-mono">2,450 <span className="text-sm text-slate-500 font-normal">积分</span></div>
                    <div className="mt-3 text-xs text-cyan-400 flex items-center gap-1">
                        <Zap size={12} /> 自动充值已关闭
                    </div>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 relative overflow-hidden group">
                     <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <TrendingUp size={48} />
                    </div>
                    <p className="text-sm text-slate-400 mb-1">本月消耗 (Used)</p>
                    <div className="text-3xl font-bold text-white font-mono">￥48.50</div>
                    <div className="mt-3 w-full bg-slate-700 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-gradient-to-r from-blue-500 to-indigo-500 w-[35%] h-full rounded-full" />
                    </div>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 relative overflow-hidden group">
                     <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Calendar size={48} />
                    </div>
                    <p className="text-sm text-slate-400 mb-1">预估下月 (Projected)</p>
                    <div className="text-3xl font-bold text-slate-300 font-mono">￥120.00</div>
                    <p className="mt-3 text-xs text-slate-500">基于当前使用频率预测</p>
                </div>
            </div>

            {/* Usage Stats Graph (Simplified) */}
            <div className="mb-8">
                <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                    <Cpu size={16} className="text-cyan-400"/> 模型消耗分布
                </h3>
                <div className="flex h-4 rounded-full overflow-hidden bg-slate-800 w-full mb-2">
                    <div className="bg-blue-500 h-full" style={{ width: '45%' }} title="GPT-4o (45%)"></div>
                    <div className="bg-cyan-500 h-full" style={{ width: '30%' }} title="Gemini-1.5-Pro (30%)"></div>
                    <div className="bg-purple-500 h-full" style={{ width: '15%' }} title="DeepNarrative (15%)"></div>
                    <div className="bg-slate-600 h-full" style={{ width: '10%' }} title="Others (10%)"></div>
                </div>
                <div className="flex gap-4 text-xs text-slate-400">
                    <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div>GPT-4o</div>
                    <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-cyan-500"></div>Gemini Pro</div>
                    <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-purple-500"></div>DeepNarrative</div>
                    <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-slate-600"></div>其他</div>
                </div>
            </div>

            {/* List Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
                    <button 
                        onClick={() => setActiveTab('USAGE')}
                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                            activeTab === 'USAGE' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                        }`}
                    >
                        用量明细
                    </button>
                    <button 
                        onClick={() => setActiveTab('HISTORY')}
                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                            activeTab === 'HISTORY' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                        }`}
                    >
                        充值记录
                    </button>
                </div>
                
                <div className="flex gap-2">
                     <button className="flex items-center gap-1 px-3 py-1.5 border border-slate-700 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                        <Filter size={12} /> 筛选
                     </button>
                     <button className="flex items-center gap-1 px-3 py-1.5 border border-slate-700 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                        <Download size={12} /> 导出账单
                     </button>
                </div>
            </div>

            {/* Logs List */}
            <div className="border border-slate-800 rounded-xl overflow-hidden">
                <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-800 grid grid-cols-12 gap-4 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    <div className="col-span-4">模型 / 任务</div>
                    <div className="col-span-3 text-right">Token 用量</div>
                    <div className="col-span-3 text-right">费用</div>
                    <div className="col-span-2 text-right">时间</div>
                </div>
                
                <div className="bg-slate-900/20 divide-y divide-slate-800/50">
                    {usageLogs.map((log) => (
                        <div key={log.id} className="grid grid-cols-12 gap-4 px-4 py-3.5 items-center hover:bg-slate-800/30 transition-colors group">
                            <div className="col-span-4">
                                <div className="flex items-center gap-3">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
                                        log.type === 'reasoning' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' :
                                        log.type === 'generation' ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400' :
                                        'bg-purple-500/10 border-purple-500/20 text-purple-400'
                                    }`}>
                                        <Server size={14} />
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-slate-200">{log.model}</div>
                                        <div className="text-xs text-slate-500">{log.task}</div>
                                    </div>
                                </div>
                            </div>
                            <div className="col-span-3 text-right">
                                <span className="text-sm font-mono text-slate-300">{log.tokens}</span>
                                <span className="text-[10px] text-slate-600 block">tokens</span>
                            </div>
                            <div className="col-span-3 text-right">
                                <span className="text-sm font-mono text-white font-bold">- ￥{log.cost.toFixed(2)}</span>
                            </div>
                            <div className="col-span-2 text-right text-xs text-slate-500">
                                {log.time}
                            </div>
                        </div>
                    ))}
                    {/* Empty placeholder if needed */}
                    {usageLogs.length === 0 && (
                        <div className="p-8 text-center text-slate-500 text-sm">暂无记录</div>
                    )}
                </div>
                <div className="px-4 py-2 bg-slate-900/80 border-t border-slate-800 text-center">
                    <button className="text-xs text-slate-400 hover:text-white flex items-center justify-center gap-1 w-full">
                        查看更多 <ChevronDown size={12} />
                    </button>
                </div>
            </div>

        </div>
      </motion.div>
    </div>
  );
};

export default BillingModal;
