import React from 'react';
import { Tabs, TabsProps, ConfigProvider } from 'antd';

export const GlassTabs: React.FC<TabsProps> = (props) => {
  const isLarge = props.size === 'large';

  return (
    <ConfigProvider
      theme={{
        components: {
          Tabs: {
            cardBg: 'transparent',
            cardGutter: 4,
            colorBorderSecondary: 'rgba(51, 65, 85, 0.4)', // slate-700
            itemActiveColor: '#22d3ee', // cyan-400
            itemHoverColor: '#e2e8f0', // slate-200
            itemColor: '#94a3b8', // slate-400
            titleFontSize: isLarge ? 15 : 14,
            itemSelectedColor: '#22d3ee',
          },
        },
      }}
    >
      <div className="glass-tabs-wrapper">
        <style>{`
          .glass-tabs-wrapper .ant-tabs-nav::before {
            border-bottom: 1px solid rgba(51, 65, 85, 0.4) !important;
          }
          .glass-tabs-wrapper .ant-tabs-tab {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-bottom: none !important;
            color: #94a3b8 !important;
            transition: all 0.3s;
            padding: ${isLarge ? '10px 20px' : '8px 16px'} !important;
            border-radius: 8px 8px 0 0 !important;
            margin: 0 2px !important;
          }
          .glass-tabs-wrapper .ant-tabs-tab .ant-tabs-tab-btn {
            font-size: ${isLarge ? '15px' : '14px'} !important;
            font-weight: 500 !important;
          }
          .glass-tabs-wrapper .ant-tabs-tab:hover {
            color: #e2e8f0 !important;
            background: rgba(255, 255, 255, 0.05) !important;
          }
          .glass-tabs-wrapper .ant-tabs-tab-active {
            background: rgba(34, 211, 238, 0.1) !important;
            border: 1px solid rgba(34, 211, 238, 0.3) !important;
            border-bottom-color: transparent !important;
            position: relative;
          }
          .glass-tabs-wrapper .ant-tabs-tab-active .ant-tabs-tab-btn {
            color: #22d3ee !important;
            text-shadow: 0 0 12px rgba(34, 211, 238, 0.3);
            font-weight: 600 !important;
          }
          .glass-tabs-wrapper .ant-tabs-ink-bar {
            background: #22d3ee !important;
            height: 2px !important;
          }
          /* 禁用所有 Tabs 内容动画 */
          .glass-tabs-wrapper .ant-tabs-content-holder {
            overflow: visible !important;
          }
          .glass-tabs-wrapper .ant-tabs-content {
            animation: none !important;
            transition: none !important;
          }
          .glass-tabs-wrapper .ant-tabs-tabpane {
            animation: none !important;
            opacity: 1 !important;
          }
        `}</style>
        <Tabs {...props} type="card" animated={false} />
      </div>
    </ConfigProvider>
  );
};
