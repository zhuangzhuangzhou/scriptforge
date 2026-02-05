import React, { useState } from 'react';
import { Film, Bell, LogOut, ChevronLeft, Settings, Database, Shield, Sparkles } from 'lucide-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { message, Avatar, Dropdown } from 'antd';
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

        <div className="flex items-center gap-2 sm:gap-3">
          {/* Admin Entry */}
          {user?.role === 'admin' && (
            <button
              onClick={() => navigate('/admin/dashboard')}
              className="flex items-center gap-2 px-3 h-8 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full hover:bg-red-500/20 transition-all text-[10px] font-bold uppercase tracking-wider mr-2"
            >
              <Shield size={12} />
              Admin
            </button>
          )}

          {/* Settings */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="h-10 px-3 bg-slate-900/50 rounded-full flex items-center justify-center cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all text-slate-400 hover:text-white"
            title="全局设置"
          >
            <Settings size={19} />
          </button>

          {/* Notifications */}
          <button className="h-10 px-3 bg-slate-900/50 rounded-full flex items-center justify-center cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all text-slate-400 hover:text-white relative">
            <Bell size={19} />
            <span className="absolute top-2.5 right-3 w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.6)] ring-1 ring-slate-900" />
          </button>

          {/* Points */}
          <div
            onClick={() => setIsBillingOpen(true)}
            className="h-10 px-4 bg-slate-900/50 rounded-full flex items-center gap-2 cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all"
            title="账户资产"
          >
            <Sparkles size={16} className="text-cyan-400" />
            <div className="flex items-center gap-1">
              <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">积分:</span>
              <span className="text-sm font-bold text-cyan-400">
                {user?.balance ?? 0}
              </span>
            </div>
          </div>

          {/* User Profile */}
          <Dropdown
            menu={{
              items: [
                { key: 'edit', label: 'Edit Profile', onClick: () => message.info('Edit Profile feature coming soon') },
                { key: 'password', label: 'Change Password', onClick: () => message.info('Change Password feature coming soon') },
                { type: 'divider' },
                { key: 'logout', label: 'Logout', icon: <LogOut size={14} />, onClick: onLogout, danger: true },
              ]
            }}
            placement="bottomRight"
            trigger={['click']}
          >
            <div className="h-10 pl-1 pr-4 bg-slate-900/50 rounded-full flex items-center gap-3 cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all group">
              <div className="w-8 h-8 rounded-full border border-white/10 bg-slate-900 overflow-hidden shadow-inner group-hover:border-cyan-500/50 transition-colors">
                <img
                  src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.username || 'Alex'}`}
                  className="w-full h-full object-cover"
                  alt="avatar"
                />
              </div>
              <span className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors hidden md:block">
                {user?.username}
              </span>
            </div>
          </Dropdown>
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
