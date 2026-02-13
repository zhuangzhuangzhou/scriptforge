import React from 'react';
import { DatePicker } from 'antd';
import type { RangePickerProps } from 'antd/es/date-picker';

const { RangePicker } = DatePicker;

const dropdownClassName = 'glass-datepicker-dropdown';

const GLASS_DATEPICKER_STYLES = `
  .glass-datepicker-wrapper .ant-picker {
    background-color: rgba(2, 6, 23, 0.5) !important;
    border: 1px solid rgba(51, 65, 85, 0.6) !important;
    color: #e2e8f0 !important;
    backdrop-filter: blur(4px);
  }

  .glass-datepicker-wrapper .ant-picker:hover,
  .glass-datepicker-wrapper .ant-picker-focused {
    border-color: rgba(34, 211, 238, 0.5) !important;
    box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.1) !important;
  }

  .glass-datepicker-wrapper .ant-picker-input > input {
    color: #e2e8f0 !important;
  }

  .glass-datepicker-wrapper .ant-picker-input > input::placeholder {
    color: #64748b !important;
  }

  .glass-datepicker-wrapper .ant-picker-suffix,
  .glass-datepicker-wrapper .ant-picker-separator {
    color: #64748b !important;
  }

  .glass-datepicker-wrapper .ant-picker-clear {
    background: transparent !important;
    color: #64748b !important;
  }

  .glass-datepicker-wrapper .ant-picker-clear:hover {
    color: #94a3b8 !important;
  }

  .glass-datepicker-wrapper .ant-picker-active-bar {
    background: #22d3ee !important;
  }

  /* Dropdown Panel Styles */
  .${dropdownClassName} {
    background-color: rgba(15, 23, 42, 0.98) !important;
    border: 1px solid rgba(51, 65, 85, 0.6) !important;
    backdrop-filter: blur(12px);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
  }

  .${dropdownClassName} .ant-picker-panel-container {
    background: transparent !important;
  }

  .${dropdownClassName} .ant-picker-panel {
    background: transparent !important;
    border-color: rgba(51, 65, 85, 0.4) !important;
  }

  .${dropdownClassName} .ant-picker-header {
    color: #e2e8f0 !important;
    border-color: rgba(51, 65, 85, 0.4) !important;
  }

  .${dropdownClassName} .ant-picker-header button {
    color: #94a3b8 !important;
  }

  .${dropdownClassName} .ant-picker-header button:hover {
    color: #22d3ee !important;
  }

  .${dropdownClassName} .ant-picker-content th {
    color: #64748b !important;
  }

  .${dropdownClassName} .ant-picker-cell {
    color: #94a3b8 !important;
  }

  .${dropdownClassName} .ant-picker-cell:hover:not(.ant-picker-cell-selected):not(.ant-picker-cell-range-start):not(.ant-picker-cell-range-end) .ant-picker-cell-inner {
    background: rgba(255, 255, 255, 0.1) !important;
  }

  .${dropdownClassName} .ant-picker-cell-in-view {
    color: #e2e8f0 !important;
  }

  .${dropdownClassName} .ant-picker-cell-selected .ant-picker-cell-inner,
  .${dropdownClassName} .ant-picker-cell-range-start .ant-picker-cell-inner,
  .${dropdownClassName} .ant-picker-cell-range-end .ant-picker-cell-inner {
    background: #22d3ee !important;
    color: #0f172a !important;
  }

  .${dropdownClassName} .ant-picker-cell-in-range::before {
    background: rgba(34, 211, 238, 0.15) !important;
  }

  .${dropdownClassName} .ant-picker-cell-range-hover::before,
  .${dropdownClassName} .ant-picker-cell-range-hover-start::before,
  .${dropdownClassName} .ant-picker-cell-range-hover-end::before {
    background: rgba(34, 211, 238, 0.1) !important;
  }

  .${dropdownClassName} .ant-picker-today-btn {
    color: #22d3ee !important;
  }

  .${dropdownClassName} .ant-picker-cell-today .ant-picker-cell-inner::before {
    border-color: #22d3ee !important;
  }

  .${dropdownClassName} .ant-picker-footer {
    border-color: rgba(51, 65, 85, 0.4) !important;
  }

  .${dropdownClassName} .ant-picker-ranges {
    border-color: rgba(51, 65, 85, 0.4) !important;
  }

  .${dropdownClassName} .ant-picker-preset > .ant-tag {
    background: rgba(34, 211, 238, 0.1) !important;
    border-color: rgba(34, 211, 238, 0.3) !important;
    color: #22d3ee !important;
  }
`;

export const GlassRangePicker: React.FC<RangePickerProps> = (props) => {
  return (
    <div className="glass-datepicker-wrapper">
      <style>{GLASS_DATEPICKER_STYLES}</style>
      <RangePicker
        {...props}
        popupClassName={`${props.popupClassName || ''} ${dropdownClassName}`}
      />
    </div>
  );
};
