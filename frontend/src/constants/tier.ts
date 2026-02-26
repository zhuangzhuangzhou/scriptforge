import { UserTier } from '../types';

/**
 * 用户等级显示名称映射
 */
export const TIER_NAMES: Record<UserTier | string, string> = {
  FREE: '免费版',
  CREATOR: '创作者版',
  STUDIO: '工作室版',
  ENTERPRISE: '企业版',
};

/**
 * 用户等级渐变色映射
 */
export const TIER_COLORS: Record<UserTier, string> = {
  FREE: 'from-slate-500 to-slate-700',
  CREATOR: 'from-blue-500 to-cyan-500',
  STUDIO: 'from-purple-500 to-pink-500',
  ENTERPRISE: 'from-amber-500 to-orange-500',
};

/**
 * 获取等级显示名称
 */
export function getTierName(tier: string): string {
  return TIER_NAMES[tier.toUpperCase()] || tier;
}
