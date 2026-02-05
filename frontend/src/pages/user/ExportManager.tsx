import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Space, Button, message, Typography } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

const { Text } = Typography;

const ExportManager: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [loading, setLoading] = useState(false);

  const exportBatch = async (format: 'pdf' | 'docx') => {
    if (!projectId) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/export/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          project_id: projectId,
          format
        })
      });
      if (!response.ok) throw new Error('导出失败');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `project-${projectId}-scripts.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      message.error('导出失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card bordered={false}>
      <Space direction="vertical" size="large">
        <Text type="secondary">导出项目下全部剧本（打包为 ZIP）</Text>
        <Space>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => exportBatch('pdf')}
            loading={loading}
          >
            导出 PDF
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => exportBatch('docx')}
            loading={loading}
          >
            导出 DOCX
          </Button>
        </Space>
      </Space>
    </Card>
  );
};

export default ExportManager;
