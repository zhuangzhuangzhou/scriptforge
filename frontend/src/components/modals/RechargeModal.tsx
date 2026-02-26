import React, { useState } from 'react';
import { X, Check, Crown, User, Building2, Rocket, Gift, MessageCircle, Mail } from 'lucide-react';
import { motion } from 'framer-motion';
import { UserTier } from '../../types';
import RedeemCodeModal from './RedeemCodeModal';

interface RechargeModalProps {
  onClose: () => void;
  onSuccess: (tier: UserTier) => void;
  currentTier: UserTier;
}

const RechargeModal: React.FC<RechargeModalProps> = ({ onClose, onSuccess, currentTier }) => {
  const [showRedeemModal, setShowRedeemModal] = useState(false);

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
    }
  ];

  const handleRedeemSuccess = () => {
    setShowRedeemModal(false);
    // 兑换成功后关闭整个弹窗
    onClose();
  };

  return (
    <>
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
            {/* 兑换码入口 */}
            <div className="mb-6 p-4 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20 rounded-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                    <Gift className="text-emerald-400" size={20} />
                  </div>
                  <div>
                    <div className="text-white font-medium">有兑换码？</div>
                    <div className="text-sm text-slate-400">输入兑换码立即获取积分或升级</div>
                  </div>
                </div>
                <button
                  onClick={() => setShowRedeemModal(true)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors"
                >
                  立即兑换
                </button>
              </div>
            </div>

            {/* 套餐列表 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              {plans.map((plan) => {
                const isCurrent = currentTier === plan.id;

                let borderColor = "border-slate-800";
                let cardBg = "bg-slate-900/50";

                if (plan.color === 'cyan') {
                  borderColor = "hover:border-cyan-500/50";
                } else if (plan.color === 'purple') {
                  borderColor = "hover:border-purple-500/50 border-purple-500/30 ring-1 ring-purple-500/20";
                  cardBg = "bg-purple-500/5";
                } else if (plan.color === 'amber') {
                  borderColor = "hover:border-amber-500/50";
                }

                return (
                  <div key={plan.id} className={`relative ${cardBg} rounded-2xl border ${borderColor} p-6 flex flex-col transition-all duration-300 group`}>
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

                    <div className="flex-1 space-y-3 mb-6">
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

                    {isCurrent ? (
                      <div className="w-full py-3 bg-slate-700 text-slate-400 text-sm font-bold rounded-xl text-center">
                        当前版本
                      </div>
                    ) : (
                      <div className="text-center text-sm text-slate-500">
                        联系客服订阅
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 联系客服 */}
            <div className="p-6 bg-slate-800/30 border border-slate-700/50 rounded-xl">
              <h3 className="text-lg font-bold text-white mb-4 text-center">如何订阅？</h3>
              <p className="text-slate-400 text-center mb-6">
                目前暂未开放在线支付，请通过以下方式联系我们完成订阅
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
                <div className="flex items-center gap-3 px-6 py-3 bg-slate-800 rounded-xl">
                  <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                    <MessageCircle className="text-green-400" size={20} />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">微信客服</div>
                    <div className="text-white font-medium">AIScriptFlow</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 px-6 py-3 bg-slate-800 rounded-xl">
                  <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <Mail className="text-blue-400" size={20} />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">邮箱</div>
                    <div className="text-white font-medium">support@aiscriptflow.com</div>
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-500 text-center mt-4">
                工作时间：周一至周五 9:00-18:00，通常 24 小时内回复
              </p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* 兑换码弹窗 */}
      {showRedeemModal && (
        <RedeemCodeModal
          onClose={() => setShowRedeemModal(false)}
          onSuccess={handleRedeemSuccess}
        />
      )}
    </>
  );
};

export default RechargeModal;
