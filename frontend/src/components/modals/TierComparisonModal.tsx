import React from 'react';
import { Crown, TrendingUp, Zap, Star, Check, X } from 'lucide-react';
import { GlassModal } from '../ui/GlassModal';
import { TIER_NAMES } from '../../constants/tier';

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
  const tiers = [
    {
      key: 'FREE',
      name: '免费版',
      price: '¥0',
      period: '',
      description: '体验基础功能',
      icon: Star,
      color: 'slate',
      gradient: 'from-slate-500 to-slate-600',
      features: {
        projects: '1 个',
        batch: '3 章/批',
        ai: '基础模型',
        export: 'TXT',
        support: false,
        api: false,
      }
    },
    {
      key: 'CREATOR',
      name: '创作者版',
      price: '¥99',
      period: '/月',
      description: '个人创作者首选',
      icon: Zap,
      color: 'blue',
      gradient: 'from-blue-500 to-cyan-500',
      features: {
        projects: '5 个',
        batch: '6 章/批',
        ai: '标准模型',
        export: 'TXT + Word',
        support: true,
        api: false,
      }
    },
    {
      key: 'STUDIO',
      name: '工作室版',
      price: '¥299',
      period: '/月',
      description: '团队协作必备',
      icon: TrendingUp,
      color: 'purple',
      gradient: 'from-purple-500 to-pink-500',
      popular: true,
      features: {
        projects: '20 个',
        batch: '12 章/批',
        ai: '高级模型',
        export: '全格式',
        support: true,
        api: true,
      }
    },
    {
      key: 'ENTERPRISE',
      name: '企业版',
      price: '定制',
      period: '',
      description: '企业级解决方案',
      icon: Crown,
      color: 'amber',
      gradient: 'from-amber-500 to-orange-500',
      features: {
        projects: '无限',
        batch: '自定义',
        ai: '专属模型',
        export: '全格式 + API',
        support: true,
        api: true,
      }
    }
  ];

  const featureLabels = [
    { key: 'projects', label: '项目数量' },
    { key: 'batch', label: '批量处理' },
    { key: 'ai', label: 'AI 模型' },
    { key: 'export', label: '导出格式' },
    { key: 'support', label: '优先支持' },
    { key: 'api', label: 'API 接入' },
  ];

  const tierOrder = ['FREE', 'CREATOR', 'STUDIO', 'ENTERPRISE'];
  const currentIndex = tierOrder.indexOf(currentTier);

  return (
    <GlassModal
      title={null}
      open={isOpen}
      onCancel={onClose}
      footer={null}
      width={880}
      closable={true}
    >
      <div className="py-1">
        {/* Header */}
        <div className="text-center mb-5">
          <h2 className="text-xl font-bold text-white mb-1">选择您的方案</h2>
          <p className="text-slate-400 text-sm">
            当前版本：<span className="text-cyan-400 font-medium">{TIER_NAMES[currentTier]}</span>
          </p>
        </div>

        {/* 版本卡片 - 横向排列 */}
        <div className="grid grid-cols-4 gap-3 mb-5">
          {tiers.map((tier, index) => {
            const isCurrent = tier.key === currentTier;
            const isHigher = index > currentIndex;
            const Icon = tier.icon;

            return (
              <div
                key={tier.key}
                className={`relative rounded-2xl border-2 transition-all duration-300 ${
                  isCurrent
                    ? 'border-cyan-500 bg-cyan-500/5 shadow-lg shadow-cyan-500/10'
                    : tier.popular
                    ? 'border-purple-500/50 bg-purple-500/5'
                    : 'border-slate-700/50 bg-slate-800/30 hover:border-slate-600'
                }`}
              >
                {/* 推荐标签 */}
                {tier.popular && !isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full text-[10px] font-bold text-white uppercase tracking-wider">
                    推荐
                  </div>
                )}

                {/* 当前版本标签 */}
                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full text-[10px] font-bold text-white uppercase tracking-wider">
                    当前
                  </div>
                )}

                <div className="p-4">
                  {/* 图标 */}
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${tier.gradient} flex items-center justify-center mb-3`}>
                    <Icon size={20} className="text-white" />
                  </div>

                  {/* 名称和描述 */}
                  <h3 className="text-base font-bold text-white mb-0.5">{tier.name}</h3>
                  <p className="text-[10px] text-slate-500 mb-3">{tier.description}</p>

                  {/* 价格 */}
                  <div className="mb-4">
                    <span className="text-2xl font-bold text-white">{tier.price}</span>
                    {tier.period && <span className="text-slate-400 text-xs">{tier.period}</span>}
                  </div>

                  {/* 按钮 */}
                  {isCurrent ? (
                    <div className="w-full py-2 rounded-lg bg-slate-700/30 text-slate-500 text-xs font-medium text-center">
                      当前版本
                    </div>
                  ) : (
                    <button
                      onClick={() => onUpgrade(tier.key)}
                      className={`w-full py-2 rounded-lg text-xs font-bold transition-all ${
                        isHigher
                          ? `bg-gradient-to-r ${tier.gradient} text-white hover:opacity-90`
                          : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                      }`}
                    >
                      {isHigher ? '立即升级' : '切换'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* 功能对比表 */}
        <div className="rounded-xl border border-slate-700/50 overflow-hidden">
          {/* 表头 */}
          <div className="grid grid-cols-5 bg-slate-800/60">
            <div className="p-3 text-xs font-medium text-slate-400">功能特性</div>
            {tiers.map((tier) => (
              <div
                key={tier.key}
                className={`p-3 text-center ${
                  tier.key === currentTier ? 'bg-cyan-500/10' : ''
                }`}
              >
                <span className={`text-xs font-bold ${
                  tier.key === currentTier ? 'text-cyan-400' : 'text-white'
                }`}>
                  {tier.name}
                </span>
              </div>
            ))}
          </div>

          {/* 表格内容 */}
          {featureLabels.map((feature, idx) => (
            <div
              key={feature.key}
              className={`grid grid-cols-5 border-t border-slate-700/30 ${
                idx % 2 === 0 ? 'bg-slate-800/20' : ''
              }`}
            >
              <div className="p-3 text-xs text-slate-300 flex items-center">
                {feature.label}
              </div>
              {tiers.map((tier) => {
                const value = tier.features[feature.key as keyof typeof tier.features];
                const isCurrent = tier.key === currentTier;

                return (
                  <div
                    key={tier.key}
                    className={`p-3 flex items-center justify-center ${
                      isCurrent ? 'bg-cyan-500/5' : ''
                    }`}
                  >
                    {value === true ? (
                      <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <Check size={12} className="text-emerald-400" />
                      </div>
                    ) : value === false ? (
                      <div className="w-5 h-5 rounded-full bg-slate-700/50 flex items-center justify-center">
                        <X size={12} className="text-slate-500" />
                      </div>
                    ) : (
                      <span className={`text-xs ${
                        isCurrent ? 'text-cyan-400 font-semibold' : 'text-slate-300'
                      }`}>
                        {value}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* 底部说明 */}
        <div className="mt-4 text-center">
          <p className="text-slate-500 text-[10px]">
            升级后立即生效 · 支持随时切换 · 企业定制请联系 sales@aiscriptflow.com
          </p>
        </div>
      </div>
    </GlassModal>
  );
};

export default TierComparisonModal;
