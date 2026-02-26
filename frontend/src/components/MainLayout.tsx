import React, { useState } from 'react';
import { Film, LogOut, ChevronLeft, Settings, Shield, Gem, User, Lock, Bot, MessageSquare } from 'lucide-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { message, Dropdown } from 'antd';
import GlobalSettingsModal from './modals/GlobalSettingsModal';
import RechargeModal from './modals/RechargeModal';
import BillingModal from './modals/BillingModal';
import TierComparisonModal from './modals/TierComparisonModal';
import FeedbackModal from './modals/FeedbackModal';
import NotificationBell from './NotificationBell';
import { UserTier } from '../types';
import { TIER_NAMES, TIER_COLORS } from '../constants/tier';
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
  const [isTierComparisonOpen, setIsTierComparisonOpen] = useState(false);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);

  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // 判断是否显示返回按钮
  const isWorkspace = location.pathname.includes('/workspace') || location.pathname.includes('/projects/');
  const isAdminSubPage = location.pathname.startsWith('/admin/') && location.pathname !== '/admin/dashboard';
  const showBackBtn = isWorkspace || isAdminSubPage;

  // 返回按钮的目标路径
  const getBackPath = () => {
    if (isAdminSubPage) return '/admin/dashboard';
    return '/dashboard';
  };

  const handleRechargeSuccess = (newTier: UserTier) => {
    setUserTier(newTier);
    message.success('充值/升级成功');
  };

  const handleUpgrade = () => {
    setIsTierComparisonOpen(false);
    setIsRechargeOpen(true);
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950">
      {/* Top Header */}
      <header className="h-16 border-b border-slate-800/60 bg-slate-900/50 backdrop-blur-md px-6 flex items-center justify-between z-40 sticky top-0 shrink-0">
        <div className="flex items-center gap-4">
          {showBackBtn && (
            <button
                onClick={() => navigate(getBackPath())}
                className="p-2 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                title={isAdminSubPage ? "返回管理后台" : "返回仪表盘"}
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

          {/* Tier Version Badge - Small Capsule Style */}
          <button
            onClick={() => setIsTierComparisonOpen(true)}
            className="hidden md:flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700 hover:border-cyan-500/50 transition-all group cursor-pointer"
          >
            <div className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${TIER_COLORS[userTier]}`} />
            <span className="text-[10px] font-bold text-slate-400 group-hover:text-cyan-400 transition-colors uppercase tracking-wider">
              {TIER_NAMES[userTier]}
            </span>
          </button>
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

          {/* AI Settings - 跳转到资源管理页面 */}
          {user?.role === 'admin' && (
            <button
              onClick={() => navigate('/admin/resources')}
              className="h-10 px-3 bg-slate-900/50 rounded-full flex items-center justify-center cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all text-slate-400 hover:text-white"
              title="AI 资源管理"
            >
              <Bot size={19} />
            </button>
          )}

          {/* Feedback Button */}
          <button
            onClick={() => setIsFeedbackOpen(true)}
            className="h-10 px-3 bg-slate-900/50 rounded-full flex items-center justify-center cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all text-slate-400 hover:text-white"
            title="意见反馈"
          >
            <MessageSquare size={19} />
          </button>

          <button
            onClick={() => setIsSettingsOpen(true)}
            className="h-10 px-3 bg-slate-900/50 rounded-full flex items-center justify-center cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all text-slate-400 hover:text-white"
            title="全局设置"
          >
            <Settings size={19} />
          </button>

          {/* Notifications */}
          <NotificationBell />

          {/* Points */}
          <div
            onClick={() => setIsBillingOpen(true)}
            className="h-9 px-3 bg-slate-900/50 rounded-full flex items-center gap-2.5 cursor-pointer hover:border-purple-500/30 hover:bg-slate-800/80 transition-all group border border-transparent"
            title="账户资产"
          >
            <Gem size={15} className="text-fuchsia-400 group-hover:scale-110 transition-transform duration-300" />
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">积分</span>
              <span className="text-sm font-semibold bg-gradient-to-r from-pink-400 to-purple-500 bg-clip-text text-transparent">
                {(user?.credits ?? 0).toLocaleString()}
              </span>
            </div>
          </div>

          {/* User Profile */}
          <Dropdown
            dropdownRender={() => (
              <div className="bg-slate-900/95 border border-slate-700/50 rounded-xl shadow-2xl backdrop-blur-xl p-1 w-48 mt-2 overflow-hidden animate-in fade-in zoom-in duration-200">
                <button
                  onClick={() => message.info('编辑资料功能即将上线')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800/80 hover:text-white transition-colors rounded-lg text-left"
                >
                  <User size={14} className="text-slate-400" />
                  <span>编辑资料</span>
                </button>
                <button
                  onClick={() => message.info('修改密码功能即将上线')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800/80 hover:text-white transition-colors rounded-lg text-left"
                >
                  <Lock size={14} className="text-slate-400" />
                  <span>修改密码</span>
                </button>
                <div className="h-px bg-slate-800/60 my-1 mx-1" />
                <button
                  onClick={onLogout}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors rounded-lg text-left"
                >
                  <LogOut size={14} />
                  <span>退出登录</span>
                </button>
              </div>
            )}
            placement="bottomRight"
            trigger={['click']}
          >
            <div className="h-10 pl-4 pr-1 bg-slate-900/50 rounded-full flex items-center gap-3 cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all group">
              <span className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors hidden md:block">
                {user?.username}
              </span>
              <div className="w-8 h-8 rounded-full border border-white/10 bg-slate-900 overflow-hidden shadow-inner group-hover:border-cyan-500/50 transition-colors">
                <img
                  src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.username || 'Alex'}`}
                  className="w-full h-full object-cover"
                  alt="avatar"
                />
              </div>
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

      {/* Tier Comparison Modal */}
      {isTierComparisonOpen && (
        <TierComparisonModal
          isOpen={isTierComparisonOpen}
          onClose={() => setIsTierComparisonOpen(false)}
          currentTier={userTier}
          onUpgrade={handleUpgrade}
        />
      )}

      {/* Feedback Modal */}
      {isFeedbackOpen && (
        <FeedbackModal onClose={() => setIsFeedbackOpen(false)} />
      )}
    </div>
  );
};

export default MainLayout;
