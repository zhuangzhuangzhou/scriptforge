import React from 'react';
import { Modal } from 'antd';
import { LucideIcon, AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react';

interface ConfirmModalProps {
  /** 控制弹窗显示 */
  open: boolean;
  /** 关闭回调 */
  onCancel: () => void;
  /** 确认回调 */
  onConfirm: () => void | Promise<void>;
  /** 弹窗标题 */
  title?: React.ReactNode;
  /** 弹窗内容 */
  content?: React.ReactNode;
  /** 确认按钮文字 */
  confirmText?: string;
  /** 取消按钮文字 */
  cancelText?: string;
  /** 确认按钮类型 */
  confirmType?: 'primary' | 'danger' | 'success';
  /** 图标类型 */
  iconType?: 'warning' | 'success' | 'info' | 'danger';
  /** 自定义图标 */
  icon?: LucideIcon;
  /** 加载状态 */
  loading?: boolean;
  /** 宽度 */
  width?: number;
  /** 类名 */
  className?: string;
}

const iconMap = {
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
  danger: XCircle,
};

const iconColorMap = {
  warning: 'text-amber-400',
  success: 'text-green-400',
  info: 'text-blue-400',
  danger: 'text-red-400',
};

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  open,
  onCancel,
  onConfirm,
  title = '确认操作',
  content,
  confirmText = '确认',
  cancelText = '取消',
  confirmType = 'primary',
  iconType = 'warning',
  icon: CustomIcon,
  loading = false,
  width = 420,
  className = '',
}) => {
  const IconComponent = CustomIcon || iconMap[iconType];
  const iconColorClass = iconColorMap[iconType];

  // 根据确认类型设置按钮样式
  const getConfirmButtonStyle = () => {
    switch (confirmType) {
      case 'danger':
        return {
          background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
          borderColor: '#dc2626',
          boxShadow: '0 4px 15px rgba(220, 38, 38, 0.3)',
        };
      case 'success':
        return {
          background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
          borderColor: '#10b981',
          boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)',
        };
      default:
        return {
          background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
          borderColor: '#6366f1',
          boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
        };
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onCancel}
      footer={null}
      closable={false}
      width={width}
      centered
      className={`confirm-modal ${className}`}
      styles={{
        mask: {
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(8px)',
        },
        content: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          backgroundImage: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%)',
          border: '1px solid rgba(51, 65, 85, 0.5)',
          borderRadius: '20px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)',
          overflow: 'hidden',
        },
        header: {
          backgroundColor: 'transparent',
          borderBottom: 'none',
          padding: '24px 24px 0',
          marginBottom: 0,
        },
        body: {
          backgroundColor: 'transparent',
          padding: '0 24px 20px',
        },
        footer: {
          backgroundColor: 'rgba(30, 41, 59, 0.5)',
          borderTop: '1px solid rgba(51, 65, 85, 0.3)',
          borderRadius: '0 0 20px 20px',
          padding: '16px 24px',
          marginTop: 0,
        },
      }}
    >
      {/* 标题区域 */}
      <div className="flex flex-col items-center mb-4">
        <div className={`w-14 h-14 rounded-full bg-slate-800/50 flex items-center justify-center border border-slate-700/50 mb-4 ${iconType === 'danger' ? 'bg-red-500/10 border-red-500/20' : ''}`}>
          <IconComponent size={28} className={iconColorClass} />
        </div>
        <h3 className="text-xl font-semibold text-white text-center leading-tight">
          {title}
        </h3>
      </div>

      {/* 内容区域 */}
      <div className="text-slate-300 text-center leading-relaxed mb-6">
        {content}
      </div>

      {/* 按钮区域 */}
      <div className="flex gap-3 justify-center">
        <button
          onClick={onCancel}
          disabled={loading}
          className="px-6 py-2.5 rounded-xl bg-slate-800/80 border border-slate-600/50 text-slate-300 font-medium hover:bg-slate-700 hover:text-white hover:border-slate-500 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed min-w-[100px]"
        >
          {cancelText}
        </button>
        <button
          onClick={onConfirm}
          loading={loading}
          disabled={loading}
          style={getConfirmButtonStyle()}
          className="px-6 py-2.5 rounded-xl text-white font-semibold transition-all duration-200 hover:brightness-110 disabled:opacity-70 disabled:cursor-not-allowed min-w-[100px] shadow-lg"
        >
          {confirmText}
        </button>
      </div>
    </Modal>
  );
};

export default ConfirmModal;
export type { ConfirmModalProps };
