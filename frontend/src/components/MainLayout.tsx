import React, { useState } from 'react';
import { Film, Bell, LogOut, ChevronLeft, Settings, Database, Shield } from 'lucide-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { message, Avatar } from 'antd';
import GlobalSettingsModal from './modals/GlobalSettingsModal';
import RechargeModal from './modals/RechargeModal';
import BillingModal from './modals/BillingModal';
import { UserTier } from '../types';
import { useAuth } from '../context/AuthContext';

interface MainLayoutProps {
  children?: React.ReactNode;
  onLogout: () => void;
  userTier: UserTier;
  setUserTier: (tier: UserTier) => void;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children, onLogout, userTier, setUserTier }) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isRechargeOpen, setIsRechargeOpen] = useState(false);
  const [isBillingOpen, setIsBillingOpen] = useState(false);

  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const showBackBtn = location.pathname.includes('/workspace') || location.pathname.includes('/projects/');

  const handleRechargeSuccess = (newTier: UserTier) => {
    setUserTier(newTier);
    message.success('充值/升级成功');
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950">
      {/* Top Header */}
      <header className="h-16 border-b border-slate-800/60 bg-slate-900/50 backdrop-blur-md px-6 flex items-center justify-between z-40 sticky top-0 shrink-0">
        <div className="flex items-center gap-4">
          {showBackBtn && (
            <button
                onClick={() => navigate('/dashboard')}
                className="p-2 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                title="返回仪表盘"
            >
                <ChevronLeft size={20} />
            </button>
          )}
          <div className="flex items-center gap-2" onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Film className="text-white" size={16} />
            </div>
            <span className="font-bold text-lg bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 hidden sm:block">
              AI ScriptFlow
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          {/* Admin Entry */}
          {user?.role === 'admin' && (
            <button
              onClick={() => navigate('/admin/dashboard')}
              className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-all text-xs font-bold uppercase tracking-wider"
            >
              <Shield size={14} />
              Admin
            </button>
          )}

          {/* 1. 功能操作组 */}
          <div className="flex items-center gap-2 pr-4 border-r border-slate-800/40">
            {/* Settings */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="text-slate-400 hover:text-white transition-all p-2 hover:bg-slate-800/40 rounded-full"
              title="全局设置"
            >
              <Settings size={19} />
            </button>

            {/* Notifications */}
            <button className="relative text-slate-400 hover:text-white transition-all p-2 hover:bg-slate-800/40 rounded-full">
              <Bell size={19} />
              <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.6)] ring-2 ring-slate-900" />
            </button>
          </div>

          {/* 2. 活力资产与极简身份 */}
          <div className="flex items-center gap-8 pl-4">

            {/* 1. 积分看板 */}
            <div
              onClick={() => setIsBillingOpen(true)}
              className="flex items-center gap-3 px-4 py-1.5 bg-slate-900/40 border border-slate-800/60 hover:border-cyan-500/40 rounded-xl cursor-pointer group/asset transition-all hover:bg-slate-800/60"
              title="账户资产"
            >
              <div className="flex flex-col items-end">
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.15em] leading-none mb-1">Balance</span>
                <div className="flex items-baseline gap-1">
                  <span className="text-lg font-bold text-white group-hover/asset:text-cyan-400 transition-colors">
                    {user?.balance ?? 0}
                  </span>
                  <span className="text-[10px] font-bold text-cyan-500/60 uppercase">PTS</span>
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 group-hover/asset:bg-cyan-500/20 transition-all">
                <Database size={16} className="text-cyan-400" />
              </div>
            </div>

            {/* 2. 用户资料 */}
            <div className="flex items-center gap-4 px-2">
              <div className="flex items-center">
                <span className="text-[14px] font-semibold text-slate-200 hover:text-white transition-colors tracking-wide">
                  {user?.full_name || user?.username}
                </span>
              </div>

              <div
                className="relative cursor-pointer group/avatar"
                onClick={() => message.info('个人中心开发中')}
              >
                <div className="w-12 h-12 rounded-2xl border border-white/10 bg-slate-900 p-0.5 shadow-2xl group-hover/avatar:scale-105 group-hover/avatar:border-cyan-500/50 transition-all duration-300 ring-4 ring-transparent group-hover/avatar:ring-cyan-500/10">
                  <img
                    src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.username || 'Alex'}`}
                    className="w-full h-full rounded-xl object-cover"
                    alt="avatar"
                  />
                </div>
              </div>

              {/* 独立登出 */}
              <button
                onClick={onLogout}
                className="p-2.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all"
                title="退出登录"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Content Area */}
      <main className="flex-1 overflow-hidden relative">
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none z-0 bg-[url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyBgYAAAAe/nuLAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAABCSURBVGhD7c4xEQAgDMCwYFv/nB0H80EAnX6yZ0mSJElyN8nI7v5fJElyN8nI7v5fJElyN8nI7v5fJElyN8nI7v5fJElyNwXN7x9F8B5fOAAAAABJRU5ErkJggg==')]"></div>
        {children || <Outlet />}
      </main>

      {/* Global Settings Modal */}
      {isSettingsOpen && (
        <GlobalSettingsModal onClose={() => setIsSettingsOpen(false)} userTier={userTier} />
      )}

      {/* Recharge/Subscription Modal */}
      {isRechargeOpen && (
        <RechargeModal onClose={() => setIsRechargeOpen(false)} onSuccess={handleRechargeSuccess} currentTier={userTier} />
      )}

      {/* Billing Modal */}
      {isBillingOpen && (
        <BillingModal onClose={() => setIsBillingOpen(false)} />
      )}
    </div>
  );
};

export default MainLayout;
