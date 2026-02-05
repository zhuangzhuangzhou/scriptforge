import React, { useState } from 'react';
import { X, Check, Crown, User, Building2, Rocket } from 'lucide-react';
import { motion } from 'framer-motion';
import { UserTier } from '../../types';

interface RechargeModalProps {
  onClose: () => void;
  onSuccess: (tier: UserTier) => void;
  currentTier: UserTier;
}

const RechargeModal: React.FC<RechargeModalProps> = ({ onClose, onSuccess, currentTier }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedTier, setSelectedTier] = useState<UserTier | null>(null);

  const plans = [
    {
      id: 'CREATOR',
      name: "创作者版",
      price: "¥49",
      period: "/月",
      target: "个人创作者",
      icon: User,
      features: [
        "项目数：5个",
        "每月产出：30集剧本",
        "批次大小：6章",
        "模型：多模型可选",
        "导出：MD + Word",
        "历史版本：7天"
      ],
      color: "cyan",
      btnText: "订阅创作版"
    },
    {
      id: 'STUDIO',
      name: "工作室版",
      price: "¥199",
      period: "/月",
      target: "专业编剧/小团队",
      icon: Building2,
      features: [
        "项目数：20个",
        "每月产出：150集剧本",
        "批次大小：12章",
        "模型：高级模型",
        "导出：MD + Word + PDF",
        "自定义 Skill",
        "历史版本：30天"
      ],
      color: "purple",
      btnText: "订阅工作室版",
      popular: true
    },
    {
      id: 'ENTERPRISE',
      name: "企业版",
      price: "¥999",
      period: "/月",
      target: "企业/平台",
      icon: Rocket,
      features: [
        "项目数：无限",
        "每月产出：无限",
        "批次大小：自定义",
        "模型：自定义 API",
        "导出：全格式 (Json/XML)",
        "自定义 Agent & 流程",
        "API 接入",
        "专属客服"
      ],
      color: "amber",
      btnText: "联系销售 / 订阅"
    }
  ];

  const handleSubscribe = (tier: UserTier) => {
    if (tier === currentTier) return;
    setIsProcessing(true);
    setSelectedTier(tier);
    // Simulate payment processing
    setTimeout(() => {
      setIsProcessing(false);
      onSuccess(tier);
      onClose();
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="relative bg-slate-900 border border-slate-800 w-full max-w-5xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
           <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                 <Crown className="text-amber-400" /> 升级您的计划
              </h2>
              <p className="text-sm text-slate-400 mt-1">当前版本: <span className="text-white font-medium">{
                  currentTier === 'FREE' ? '免费版' : 
                  currentTier === 'CREATOR' ? '创作者版' :
                  currentTier === 'STUDIO' ? '工作室版' : '企业版'
              }</span></p>
           </div>
           <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
              <X size={24} />
           </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 md:p-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {plans.map((plan) => {
                    const isCurrent = currentTier === plan.id;
                    const isProcessingThis = isProcessing && selectedTier === plan.id;
                    
                    let borderColor = "border-slate-800";
                    let buttonStyle = "bg-slate-800 text-slate-300 hover:bg-slate-700";
                    
                    if (plan.color === 'cyan') {
                        borderColor = "hover:border-cyan-500/50";
                        buttonStyle = "bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/20";
                    } else if (plan.color === 'purple') {
                        borderColor = "hover:border-purple-500/50 border-purple-500/30 ring-1 ring-purple-500/20";
                        buttonStyle = "bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-900/20";
                    } else if (plan.color === 'amber') {
                        borderColor = "hover:border-amber-500/50";
                        buttonStyle = "bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white shadow-lg shadow-amber-900/20";
                    }

                    if (isCurrent) {
                        buttonStyle = "bg-slate-700 text-slate-400 cursor-default";
                    }

                    return (
                        <div key={plan.id} className={`relative bg-slate-900/50 rounded-2xl border ${borderColor} p-6 flex flex-col transition-all duration-300 group`}>
                            {plan.popular && (
                                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-purple-500 text-white text-[10px] font-bold rounded-full uppercase tracking-wider shadow-lg">
                                    Most Popular
                                </div>
                            )}

                            <div className="mb-6">
                                <div className={`w-12 h-12 rounded-xl mb-4 flex items-center justify-center ${
                                    plan.color === 'cyan' ? 'bg-cyan-500/10 text-cyan-400' :
                                    plan.color === 'purple' ? 'bg-purple-500/10 text-purple-400' :
                                    'bg-amber-500/10 text-amber-400'
                                }`}>
                                    <plan.icon size={24} />
                                </div>
                                <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                                <div className="flex items-baseline gap-1 mt-2">
                                    <span className="text-3xl font-bold text-white">{plan.price}</span>
                                    <span className="text-sm text-slate-500">{plan.period}</span>
                                </div>
                                <p className="text-xs text-slate-400 mt-2">{plan.target}</p>
                            </div>

                            <div className="flex-1 space-y-3 mb-8">
                                {plan.features.map((feature, idx) => (
                                    <div key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                                        <Check size={16} className={`shrink-0 mt-0.5 ${
                                            plan.color === 'cyan' ? 'text-cyan-500' :
                                            plan.color === 'purple' ? 'text-purple-500' :
                                            'text-amber-500'
                                        }`} />
                                        <span>{feature}</span>
                                    </div>
                                ))}
                            </div>

                            <button 
                                onClick={() => handleSubscribe(plan.id as UserTier)}
                                disabled={isCurrent || isProcessing}
                                className={`w-full py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${buttonStyle}`}
                            >
                                {isProcessingThis ? (
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : isCurrent ? (
                                    <>当前版本</>
                                ) : (
                                    <>
                                        {plan.btnText}
                                    </>
                                )}
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
      </motion.div>
    </div>
  );
};

export default RechargeModal;
