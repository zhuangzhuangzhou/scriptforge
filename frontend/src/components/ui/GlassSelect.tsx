import React from 'react';
import { Select, SelectProps, ConfigProvider } from 'antd';

// Note: Dropdowns are rendered in a portal (document body) by default.
// To style the dropdown correctly without global CSS, we need to attach the popup to this container
// OR use a specific popupClassName and global/scoped styles.
// Here we use `popupClassName` and inject styles that target it.

const dropdownClassName = 'glass-select-dropdown-' + Math.random().toString(36).substr(2, 9);

const GLASS_SELECT_STYLES = `
  .glass-select-wrapper .ant-select-selector {
    background-color: rgba(2, 6, 23, 0.5) !important;
    border: 1px solid rgba(51, 65, 85, 0.6) !important;
    color: #e2e8f0 !important;
    backdrop-filter: blur(4px);
  }

  .glass-select-wrapper .ant-select:hover .ant-select-selector,
  .glass-select-wrapper .ant-select-focused .ant-select-selector {
    border-color: rgba(34, 211, 238, 0.5) !important;
    box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.1) !important;
  }

  .glass-select-wrapper .ant-select-arrow {
    color: #94a3b8 !important;
  }

  /* Dropdown Styles */
  .${dropdownClassName} {
    background-color: rgba(15, 23, 42, 0.95) !important;
    border: 1px solid rgba(51, 65, 85, 0.6) !important;
    backdrop-filter: blur(12px);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
    padding: 4px;
  }

  .${dropdownClassName} .ant-select-item {
    color: #cbd5e1 !important;
    border-radius: 4px;
  }

  .${dropdownClassName} .ant-select-item-option-selected {
    background-color: rgba(34, 211, 238, 0.15) !important;
    color: #22d3ee !important;
    font-weight: 500;
  }

  .${dropdownClassName} .ant-select-item-option-active {
    background-color: rgba(255, 255, 255, 0.05) !important;
  }
`;

export const GlassSelect = <T = any>(props: SelectProps<T>) => {
  return (
    <div className="glass-select-wrapper">
      <style>{GLASS_SELECT_STYLES}</style>
      <Select
        {...props}
        popupClassName={`${props.popupClassName || ''} ${dropdownClassName}`}
      />
    </div>
  );
};
