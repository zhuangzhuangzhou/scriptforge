import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

/**
 * GlassCard: 磨砂玻璃质感的容器卡片
 */
export const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', onClick }) => {
  return (
    <div
      className={`backdrop-blur-xl bg-slate-900/60 border border-slate-800/60 rounded-2xl p-6 ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
};
