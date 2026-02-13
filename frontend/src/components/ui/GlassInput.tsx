import React from 'react';
import { Input, InputProps } from 'antd';
import { TextAreaProps } from 'antd/es/input';

const GLASS_INPUT_STYLES = `
  .glass-input-wrapper .ant-input {
    background-color: rgba(2, 6, 23, 0.5) !important;
    border: 1px solid rgba(51, 65, 85, 0.6) !important;
    border-radius: 6px;
    color: #e2e8f0 !important;
  }

  .glass-input-wrapper .ant-input:hover,
  .glass-input-wrapper .ant-input:focus,
  .glass-input-wrapper .ant-input-focused {
    border-color: rgba(34, 211, 238, 0.5) !important;
    box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.1) !important;
  }

  .glass-input-wrapper .ant-input-affix-wrapper {
    background-color: rgba(2, 6, 23, 0.5) !important;
    border: 1px solid rgba(51, 65, 85, 0.6) !important;
    border-radius: 6px;
    color: #e2e8f0 !important;
    padding: 4px 11px;
  }

  .glass-input-wrapper .ant-input-affix-wrapper:hover,
  .glass-input-wrapper .ant-input-affix-wrapper-focused {
    border-color: rgba(34, 211, 238, 0.5) !important;
    box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.1) !important;
  }

  .glass-input-wrapper .ant-input-affix-wrapper .ant-input {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
  }

  .glass-input-wrapper textarea {
    background-color: transparent !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(51, 65, 85, 0.6) !important;
    border-radius: 6px;
  }

  .glass-input-wrapper textarea:hover,
  .glass-input-wrapper textarea:focus {
    border-color: rgba(34, 211, 238, 0.5) !important;
    box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.1) !important;
  }

  .glass-input-wrapper .ant-input::placeholder,
  .glass-input-wrapper textarea::placeholder {
    color: #64748b !important;
  }

  .glass-input-wrapper .ant-input-prefix,
  .glass-input-wrapper .ant-input-suffix {
    color: #64748b !important;
  }

  .glass-input-wrapper .ant-input-clear-wrapper:hover .ant-input-clear {
    color: #94a3b8 !important;
  }
`;

export const GlassInput: React.FC<InputProps> = (props) => {
  return (
    <div className="glass-input-wrapper">
      <style>{GLASS_INPUT_STYLES}</style>
      <Input {...props} />
    </div>
  );
};

export const GlassTextArea: React.FC<TextAreaProps> = (props) => {
  return (
    <div className="glass-input-wrapper">
      <style>{GLASS_INPUT_STYLES}</style>
      <Input.TextArea {...props} />
    </div>
  );
};
