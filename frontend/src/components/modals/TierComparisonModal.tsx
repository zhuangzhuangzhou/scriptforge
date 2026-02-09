import React from 'react';
import { Crown, TrendingUp, Zap, Star, Check, X } from 'lucide-react';
import { Modal } from 'antd';
import { motion } from 'framer-motion';

interface TierComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTier: string;
  onUpgrade: (tier: string) => void;
}

const TierComparisonModal: React.FC<TierComparisonModalProps> = ({
  isOpen,
  onClose,
  currentTier,
  onUpgrade
}) => {
  const tierNames: Record<string, string> = {
    'FREE': '免费版',
    'CREATOR': '创作者版',
    'STUDIO': '工作室版',
    'ENTERPRISE': '企业版'
  };

  const tierIcons: Record<string, React.ReactNode> = {
    'FREE': <Star size={20} className="text-slate-400" />,
    'CREATOR': <Zap size={20} className="text-blue-400" />,
    'STUDIO': <TrendingUp size={20} className="text-purple-400" />,
    'ENTERPRISE': <Crown size={20} className="text-amber-400" />
  };

  const tiers = [
    {
      key: 'FREE',
      name: '免费版',
      price: '¥0',
      period: '永久免费',
      color: 'from-slate-500 to-slate-700',
      bgColor: 'bg-slate-500',
      features: [
        { name: '项目数量', value: '1' },
        { name: '单批章节数', value: '3 章' },
        { name: 'AI 处理', value: '基础' },
        { name: '导出格式', value: 'TXT' },
        { name: '优先支持', value: false },
        { name: 'API 访问', value: false },
      ]
    },
    {
      key: 'CREATOR',
      name: '创作者版',
      price: '¥99',
      period: '/月',
      color: 'from-blue-500 to-cyan-500',
      bgColor: 'bg-blue-500',
      features: [
        { name: '项目数量', value: '5' },
        { name: '单批章节数', value: '6 章' },
        { name: 'AI 处理', value: '标准' },
        { name: '导出格式', value: 'TXT+PDF' },
        { name: '优先支持', value: true },
        { name: 'API 访问', value: false },
      ]
    },
    {
      key: 'STUDIO',
      name: '工作室版',
      price: '¥299',
      period: '/月',
      color: 'from-purple-500 to-pink-500',
      bgColor: 'bg-purple-500',
      features: [
        { name: '项目数量', value: '20' },
        { name: '单批章节数', value: '12 章' },
        { name: 'AI 处理', value: '高级' },
        { name: '导出格式', value: '全部格式' },
        { name: '优先支持', value: true },
        { name: 'API 访问', value: true },
      ]
    },
    {
      key: 'ENTERPRISE',
      name: '企业版',
      price: '联系销售',
      period: '',
      color: 'from-amber-500 to-orange-500',
      bgColor: 'bg-amber-500',
      features: [
        { name: '项目数量', value: '无限' },
        { name: '单批章节数', value: '自定义' },
        { name: 'AI 处理', value: '企业定制' },
        { name: '导出格式', value: '全部+定制' },
        { name: '优先支持', value: true },
        { name: 'API 访问', value: true },
      ]
    }
  ];

  const getCurrentTierIndex = () => {
    const tierOrder = ['FREE', 'CREATOR', 'STUDIO', 'ENTERPRISE'];
    return tierOrder.indexOf(currentTier);
  };

  const currentIndex = getCurrentTierIndex();

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-cyan-500/30 flex items-center justify-center">
            <Crown className="text-cyan-400" size={20} />
          </div>
          <div>
            <span className="text-lg font-bold text-white">版本对比</span>
            <p className="text-xs text-slate-400 font-normal">选择最适合您的方案</p>
          </div>
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      footer={null}
      width={900}
      styles={{
        content: {
          background: 'rgba(15, 23, 42, 0.98)',
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
        {/* 版本卡片 */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {tiers.map((tier) => {
            const isCurrent = tier.key === currentTier;
            const isHigher = tiers.indexOf(tier) > currentIndex;

            return (
              <motion.div
                key={tier.key}
                whileHover={{ scale: 1.02 }}
                className={`relative p-4 rounded-xl border transition-all ${
                  isCurrent
                    ? 'border-cyan-500/50 bg-cyan-500/10'
                    : 'border-slate-700/50 bg-slate-800/40 hover:border-slate-600'
                }`}
              >
                {/* 当前版本标识 */}
                {isCurrent && (
                  <div className="absolute -top-2 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full text-xs font-bold text-white">
                    当前版本
                  </div>
                )}

                {/* 图标和名称 */}
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${tier.color} flex items-center justify-center`}>
                    {tierIcons[tier.key]}
                  </div>
                  <div>
                    <h3 className="font-bold text-white">{tier.name}</h3>
                    <p className="text-xs text-slate-400">
                      {tier.price}{tier.period}
                    </p>
                  </div>
                </div>

                {/* 升级按钮 */}
                {isCurrent ? (
                  <button
                    disabled
                    className="w-full py-2 rounded-lg bg-slate-700/50 text-slate-400 text-sm font-medium cursor-not-allowed"
                  >
                    当前版本
                  </button>
                ) : (
                  <button
                    onClick={() => onUpgrade(tier.key)}
                    className={`w-full py-2 rounded-lg text-sm font-bold transition-all ${
                      isHigher
                        ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:from-cyan-400 hover:to-blue-400'
                        : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50'
                    }`}
                  >
                    {isHigher ? '升级' : '降级'}
                  </button>
                )}
              </motion.div>
            );
          })}
        </div>

        {/* 功能对比表 */}
        <div className="border border-slate-700/50 rounded-xl overflow-hidden">
          <div className="grid grid-cols-4 gap-4 p-4 bg-slate-800/50 border-b border-slate-700/50">
            <div className="text-sm font-medium text-slate-400">功能</div>
            {tiers.map((tier) => (
              <div key={tier.key} className="text-sm font-bold text-white text-center">
                {tier.name}
              </div>
            ))}
          </div>

          {[
            { key: 'project', label: '项目数量' },
            { key: 'batch', label: '单批章节数' },
            { key: 'ai', label: 'AI 处理' },
            { key: 'export', label: '导出格式' },
            { key: 'support', label: '优先支持' },
            { key: 'api', label: 'API 访问' },
          ].map((feature, index) => (
            <div
              key={feature.key}
              className={`grid grid-cols-4 gap-4 p-4 border-b border-slate-700/30 ${
                index % 2 === 0 ? 'bg-slate-800/20' : 'bg-transparent'
              }`}
            >
              <div className="text-sm text-slate-300">{feature.label}</div>
              {tiers.map((tier) => {
                const tierFeatures = tier.features.find(f => f.name === feature.label);
                const value = tierFeatures?.value;

                return (
                  <div key={tier.key} className="text-sm text-white text-center flex items-center justify-center">
                    {value === true ? (
                      <Check size={16} className="text-green-400" />
                    ) : value === false ? (
                      <X size={16} className="text-slate-500" />
                    ) : (
                      <span className={tier.key === currentTier ? 'text-cyan-400 font-bold' : ''}>
                        {value}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* 底部提示 */}
        <div className="mt-6 text-center">
          <p className="text-slate-400 text-sm">
            升级后立即生效，支持支付宝/微信支付
          </p>
          <p className="text-slate-500 text-xs mt-2">
            如需企业定制或技术支持，请联系 sales@aiscriptflow.com
          </p>
        </div>
      </div>
    </Modal>
  );
};

export default TierComparisonModal;
