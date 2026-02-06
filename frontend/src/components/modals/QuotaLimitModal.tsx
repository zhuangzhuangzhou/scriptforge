import React from 'react';
import { Modal } from 'antd';
import { Crown, TrendingUp, Zap } from 'lucide-react';

interface QuotaLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTier: string;
  currentLimit: number;
  quotaType?: string;
}

const QuotaLimitModal: React.FC<QuotaLimitModalProps> = ({
  isOpen,
  onClose,
  currentTier,
  currentLimit,
  quotaType = '项目'
}) => {
  const tierNames: Record<string, string> = {
    'FREE': '免费版',
    'CREATOR': '创作者版',
    'STUDIO': '工作室版',
    'ENTERPRISE': '企业版'
  };

  const upgradeTiers = [
    { name: 'CREATOR', displayName: '创作者版', limit: 5, price: '¥99/月', icon: Zap, color: '#1677ff' },
    { name: 'STUDIO', displayName: '工作室版', limit: 20, price: '¥299/月', icon: TrendingUp, color: '#722ed1' },
    { name: 'ENTERPRISE', displayName: '企业版', limit: '∞', price: '联系销售', icon: Crown, color: '#d46b08' }
  ];

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center">
            <Crown className="text-amber-400" size={20} />
          </div>
          <span className="text-lg font-bold text-white">配额已用尽</span>
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
        <p className="text-slate-400 text-sm mb-6">
          您的 <span className="text-cyan-400 font-semibold">{tierNames[currentTier] || '当前等级'}</span> 最多创建 <span className="text-cyan-400 font-semibold">{currentLimit}</span> 个{quotaType}
        </p>

        <div className="space-y-3">
          {upgradeTiers.map((tier) => {
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
                    <p className="text-slate-400 text-sm">最多 {tier.limit} 个{quotaType}</p>
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
          升级后立即生效，享受更多高级功能和优先支持
        </p>
      </div>
    </Modal>
  );
};

export default QuotaLimitModal;
