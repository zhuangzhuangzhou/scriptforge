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
    <div style={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <GlassCard style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>
            模型管理中心
          </h1>
          <p style={{ margin: '8px 0 0 0', color: 'rgba(255, 255, 255, 0.6)' }}>
            管理 AI 模型提供商、模型配置、API 凭证、计费规则和系统配置
          </p>
        </div>

        <GlassTabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />

        {/* 懒加载标签页内容，并用错误边界包裹 */}
        <div style={{ marginTop: 16, flex: 1, overflow: 'auto' }}>
          <ErrorBoundary key={activeTab}>
            {renderTabContent()}
          </ErrorBoundary>
        </div>
      </GlassCard>
    </div>
  );
};

export default ModelManagement;
