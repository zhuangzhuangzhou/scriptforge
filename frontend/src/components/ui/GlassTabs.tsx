import React from 'react';
import { Tabs, TabsProps, ConfigProvider } from 'antd';

export const GlassTabs: React.FC<TabsProps> = (props) => {
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
            titleFontSize: 14,
            itemSelectedColor: '#22d3ee',

            // Note: Ant Design's ConfigProvider doesn't support full CSS overrides for states like
            // "active tab background" vs "inactive tab background" perfectly in all versions via tokens alone
            // for the specific "Glass" look.
            // However, we can use the `className` to scope scoped CSS-in-JS or just use the style prop
            // if we want to avoid global CSS.
            // But to keep it clean and truly componentized without external CSS files,
            // we can inject a style tag or use a wrapper with emotion/styled-components.
            // Since we don't have emotion installed, we will use a localized style object or a unique class
            // with a `<style>` tag injected (Micro-frontend style) OR simply use Tailwind classes on the wrapper
            // and target the antd classes locally.
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
            padding: 8px 16px !important;
            border-radius: 6px 6px 0 0 !important;
          }
          .glass-tabs-wrapper .ant-tabs-tab:hover {
            color: #e2e8f0 !important;
            background: rgba(255, 255, 255, 0.05) !important;
          }
          .glass-tabs-wrapper .ant-tabs-tab-active {
            background: rgba(15, 23, 42, 0.6) !important;
            border: 1px solid rgba(51, 65, 85, 0.6) !important;
            border-bottom-color: transparent !important;
            position: relative;
          }
          .glass-tabs-wrapper .ant-tabs-tab-active .ant-tabs-tab-btn {
            color: #22d3ee !important;
            text-shadow: 0 0 10px rgba(34, 211, 238, 0.2);
            font-weight: 600;
          }
        `}</style>
        <Tabs {...props} type="card" />
      </div>
    </ConfigProvider>
  );
};
