import React from 'react';
import { Modal, ConfigProvider, theme } from 'antd';
import type { ModalProps } from 'antd';

/**
 * GlassModal: 磨砂玻璃样式的弹窗
 */
export const GlassModal: React.FC<ModalProps> = (props) => {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        components: {
          Modal: {
            contentBg: 'rgba(15, 23, 42, 0.95)',
            headerBg: 'transparent',
          },
        },
      }}
    >
      <Modal
        {...props}
        centered
      />
    </ConfigProvider>
  );
};
