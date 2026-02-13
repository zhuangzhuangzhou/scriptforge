// import React from 'react';
import { Table, TableProps, ConfigProvider, theme } from 'antd';

/**
 * GlassTable: 磨砂玻璃质感的表格组件
 * 使用 ConfigProvider 配置样式，避免直接修改全局 CSS
 */
export const GlassTable = <RecordType extends object>(props: TableProps<RecordType>) => {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        components: {
          Table: {
            colorBgContainer: 'transparent',
            headerBg: '#0f172a',
            borderColor: '#1e293b',
            rowHoverBg: 'rgba(30, 41, 59, 0.5)',
          },
        },
      }}
    >
      <Table {...props} />
    </ConfigProvider>
  );
};
