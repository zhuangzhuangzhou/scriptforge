import React, { useState } from 'react';
import { Alert } from 'antd';
import { GlassCard } from '../../components/ui/GlassCard';
import { GlassTabs } from '../../components/ui/GlassTabs';
import ProviderManagement from './ModelManagement/ProviderManagement';
import ModelConfiguration from './ModelManagement/ModelConfiguration';
import CredentialManagement from './ModelManagement/CredentialManagement';
import PricingManagement from './ModelManagement/PricingManagement';
import SystemConfiguration from './ModelManagement/SystemConfiguration';

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
        <Alert
          message="组件加载失败"
          description={this.state.error?.message || '未知错误'}
          type="error"
          showIcon
          style={{ margin: '20px 0' }}
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
    <div className="p-6 h-full overflow-y-auto">
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
