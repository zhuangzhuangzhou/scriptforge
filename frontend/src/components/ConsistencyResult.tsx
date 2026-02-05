import React from 'react';
import { Progress, Tabs, List, Typography, Tag, Space, Card, Empty } from 'antd';
import { AlertOutlined, BulbOutlined, CheckCircleOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface CategoryDetail {
  issues: string[];
  suggestions: string[];
}

interface ConsistencyResults {
  logic?: CategoryDetail;
  character?: CategoryDetail;
  timeline?: CategoryDetail;
  scene?: CategoryDetail;
  dialogue?: CategoryDetail;
  [key: string]: CategoryDetail | undefined;
}

interface ConsistencyResultProps {
  results: ConsistencyResults;
  score: number;
  status: string;
}

const ConsistencyResult: React.FC<ConsistencyResultProps> = ({ results, score, status }) => {
  const categories = [
    { key: 'logic', label: '逻辑一致性' },
    { key: 'character', label: '角色一致性' },
    { key: 'timeline', label: '时间线一致性' },
    { key: 'scene', label: '场景一致性' },
    { key: 'dialogue', label: '对白一致性' },
  ];

  const renderCategoryContent = (detail?: CategoryDetail) => {
    if (!detail || ((!detail.issues || detail.issues.length === 0) && (!detail.suggestions || detail.suggestions.length === 0))) {
      return (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '24px', marginBottom: '8px' }} />
          <p>未发现明显问题</p>
        </div>
      );
    }

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {detail.issues && detail.issues.length > 0 && (
          <div>
            <Title level={5} type="danger" style={{ color: '#ff4d4f' }}>
              <AlertOutlined /> 存在问题
            </Title>
            <List
              size="small"
              dataSource={detail.issues}
              renderItem={(item) => (
                <List.Item>
                  <Text type="danger">• {item}</Text>
                </List.Item>
              )}
            />
          </div>
        )}
        {detail.suggestions && detail.suggestions.length > 0 && (
          <div>
            <Title level={5} style={{ color: '#52c41a' }}>
              <BulbOutlined /> 优化建议
            </Title>
            <List
              size="small"
              dataSource={detail.suggestions}
              renderItem={(item) => (
                <List.Item>
                  <Text style={{ color: '#52c41a' }}>• {item}</Text>
                </List.Item>
              )}
            />
          </div>
        )}
      </Space>
    );
  };

  const items = categories.map((cat) => ({
    key: cat.key,
    label: cat.label,
    children: renderCategoryContent(results[cat.key]),
  }));

  // 如果 status 是 loading 或 processing，显示处理中状态
  if (status === 'processing' || status === 'running') {
     return <Empty description="一致性检查正在进行中..." image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <Card bordered={false}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around', marginBottom: 24 }}>
        <div style={{ textAlign: 'center' }}>
          <Progress
            type="circle"
            percent={score || 0}
            strokeColor={{
              '0%': '#ff4d4f',
              '100%': '#52c41a',
            }}
          />
          <div style={{ marginTop: 8 }}>
            <Text strong>综合一致性评分</Text>
          </div>
        </div>
        <div style={{ textAlign: 'left', minWidth: '200px' }}>
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary">检查状态</Text>
            <div style={{ marginTop: 4 }}>
                <Tag color={status === 'completed' || status === 'passed' ? 'green' : (status === 'failed' ? 'red' : 'blue')}>
                    {status === 'completed' || status === 'passed' ? '检查通过' : (status === 'failed' ? '检查未通过' : status)}
                </Tag>
            </div>
          </div>
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              该评分基于 AI 对剧本逻辑、角色设定、时间轴、场景及对白的综合评估。
            </Text>
          </div>
        </div>
      </div>

      <Tabs defaultActiveKey="logic" items={items} />
    </Card>
  );
};

export default ConsistencyResult;
