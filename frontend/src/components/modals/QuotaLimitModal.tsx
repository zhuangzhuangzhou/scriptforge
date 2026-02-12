import React from 'react';
import { Modal } from 'antd';
import { Crown, TrendingUp, Zap, CreditCard } from 'lucide-react';

interface CreditsLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTier: string;
  currentBalance: number;
  requiredCredits: number;
  taskType?: string;
}

const QuotaLimitModal: React.FC<CreditsLimitModalProps> = ({
  isOpen,
  onClose,
  currentTier,
  currentBalance,
  requiredCredits,
  taskType = '任务'
}) => {
  const tierNames: Record<string, string> = {
    'free': '免费版',
    'creator': '创作者版',
    'studio': '工作室版',
    'enterprise': '企业版'
  };

  const upgradeTiers = [
    { name: 'creator', displayName: '创作者版', credits: 3000, price: '¥49/月', icon: Zap, color: '#1677ff' },
    { name: 'studio', displayName: '工作室版', credits: 15000, price: '¥199/月', icon: TrendingUp, color: '#722ed1' },
    { name: 'enterprise', displayName: '企业版', credits: 100000, price: '¥999/月', icon: Crown, color: '#d46b08' }
  ];

  const shortfall = requiredCredits - currentBalance;

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-500/20 to-orange-500/20 border border-red-500/30 flex items-center justify-center">
            <CreditCard className="text-red-400" size={20} />
          </div>
          <span className="text-lg font-bold text-white">积分不足</span>
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      footer={null}
      width={520}
      className="quota-modal"
      styles={{
        content: {
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(51, 65, 85, 0.5)',
          borderRadius: '16px'
        },
        header: {
          background: 'transparent',
          borderBottom: '1px solid rgba(51, 65, 85, 0.5)'
        }
      }}
    >
      <div className="py-4">
        <div className="bg-slate-800/50 rounded-xl p-4 mb-6">
          <div className="flex justify-between items-center mb-3">
            <span className="text-slate-400">当前积分</span>
            <span className="text-white font-mono font-bold">{currentBalance.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center mb-3">
            <span className="text-slate-400">{taskType}所需</span>
            <span className="text-cyan-400 font-mono font-bold">{requiredCredits.toLocaleString()}</span>
          </div>
          <div className="border-t border-slate-700 pt-3 flex justify-between items-center">
            <span className="text-slate-400">还需</span>
            <span className="text-red-400 font-mono font-bold">{shortfall.toLocaleString()}</span>
          </div>
        </div>

        <p className="text-slate-400 text-sm mb-4">
          您的 <span className="text-cyan-400 font-semibold">{tierNames[currentTier.toLowerCase()] || '当前等级'}</span> 积分不足，可以选择：
        </p>

        <div className="space-y-3 mb-6">
          <div
            className="group cursor-pointer p-4 rounded-xl border border-cyan-500/30 hover:border-cyan-500/50 bg-cyan-500/5 hover:bg-cyan-500/10 transition-all"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div className="w-12 h-12 rounded-lg flex items-center justify-center bg-cyan-500/20">
                <CreditCard size={24} className="text-cyan-400" />
              </div>
              <div>
                <h4 className="text-white font-bold">立即充值</h4>
                <p className="text-slate-400 text-sm">1 元 = 100 积分</p>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="text-cyan-400 font-bold text-lg">¥{Math.ceil(shortfall / 100)}</div>
              <div className="text-slate-500 text-xs group-hover:text-cyan-400 transition-colors">
                去充值 →
              </div>
            </div>
          </div>
        </div>

        <p className="text-slate-500 text-sm mb-3">或升级套餐获得更多月度积分：</p>

        <div className="space-y-3">
          {upgradeTiers
            .filter(tier => tier.name !== currentTier.toLowerCase())
            .map((tier) => {
              const Icon = tier.icon;
              return (
                <div
                  key={tier.name}
                  className="group cursor-pointer p-4 rounded-xl border border-slate-700/50 hover:border-slate-600 bg-slate-800/40 hover:bg-slate-800/60 transition-all"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div
                      className="w-12 h-12 rounded-lg flex items-center justify-center"
                      style={{ background: `linear-gradient(135deg, ${tier.color}22, ${tier.color}11)` }}
                    >
                      <Icon size={24} style={{ color: tier.color }} />
                    </div>
                    <div>
                      <h4 className="text-white font-bold">{tier.displayName}</h4>
                      <p className="text-slate-400 text-sm">每月 {tier.credits.toLocaleString()} 积分</p>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div className="text-cyan-400 font-bold text-lg">{tier.price}</div>
                    <div className="text-slate-500 text-xs group-hover:text-cyan-400 transition-colors" style={{ color: tier.color }}>
                      立即升级 →
                    </div>
                  </div>
                </div>
              );
            })}
        </div>

        <p className="text-slate-500 text-xs text-center mt-6 pt-4 border-t border-slate-800">
          升级后立即生效，当月积分立即发放
        </p>
      </div>
    </Modal>
  );
};

export default QuotaLimitModal;
