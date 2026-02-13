import React, { useState } from 'react';
import { InfoCircleOutlined } from '@ant-design/icons';
import { GlassCard } from '../../components/ui/GlassCard';
import { GlassTabs } from '../../components/ui/GlassTabs';
import ProviderManagement from './ModelManagement/ProviderManagement';
import ModelConfiguration from './ModelManagement/ModelConfiguration';
import CredentialManagement from './ModelManagement/CredentialManagement';
import PricingManagement from './ModelManagement/PricingManagement';
import SystemConfiguration from './ModelManagement/SystemConfiguration';

// 深色主题提示框组件
const GlassAlert: React.FC<{
  type?: 'info' | 'warning' | 'error';
  title: string;
  description?: string;
}> = ({ type = 'error', title, description }) => {
  const colorMap = {
    info: {
      bg: 'bg-cyan-500/10',
      border: 'border-cyan-500/30',
      icon: 'text-cyan-400',
      title: 'text-cyan-300',
    },
    warning: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      icon: 'text-amber-400',
      title: 'text-amber-300',
    },
    error: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/30',
      icon: 'text-red-400',
      title: 'text-red-300',
    },
  };

  const colors = colorMap[type];

  return (
    <div className={`${colors.bg} ${colors.border} border rounded-lg p-4 flex items-start gap-3 my-5`}>
      <InfoCircleOutlined className={`${colors.icon} text-lg mt-0.5`} />
      <div>
        <div className={`${colors.title} font-medium`}>{title}</div>
        {description && (
          <div className="text-slate-400 text-sm mt-1">{description}</div>
        )}
      </div>
    </div>
  );
};

// 错误边界组件
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('组件渲染错误:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <GlassAlert
          type="error"
          title="组件加载失败"
          description={this.state.error?.message || '未知错误'}
        />
      );
    }

    return this.props.children;
  }
}

const ModelManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState('providers');

  // 渲染当前激活的标签页内容（懒加载）
  const renderTabContent = () => {
    switch (activeTab) {
      case 'providers':
        return <ProviderManagement />;
      case 'models':
        return <ModelConfiguration />;
      case 'credentials':
        return <CredentialManagement />;
      case 'pricing':
        return <PricingManagement />;
      case 'system':
        return <SystemConfiguration />;
      default:
        return null;
    }
  };

  // 标签页配置（不包含 children，避免提前渲染）
  const tabItems = [
    {
      key: 'providers',
      label: '提供商管理',
    },
    {
      key: 'models',
      label: '模型配置',
    },
    {
      key: 'credentials',
      label: '凭证管理',
    },
    {
      key: 'pricing',
      label: '计费规则',
    },
    {
      key: 'system',
      label: '系统配置',
    },
  ];

  // 渲染
  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-950">
      <GlassCard>
        <div className="mb-6">
          <h1 className="m-0 text-2xl font-semibold text-white">
            模型管理中心
          </h1>
          <p className="mt-2 mb-0 text-slate-400">
            管理 AI 模型提供商、模型配置、API 凭证、计费规则和系统配置
          </p>
        </div>

        <GlassTabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />

        {/* 懒加载标签页内容，并用错误边界包裹 */}
        <div className="mt-4">
          <ErrorBoundary key={activeTab}>
            {renderTabContent()}
          </ErrorBoundary>
        </div>
      </GlassCard>
    </div>
  );
};

export default ModelManagement;
