import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Select, Button, Space, Progress, Tag, Typography, Input, List, Divider, message } from 'antd';
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface Pipeline {
  id: string;
  name: string;
  description?: string;
  stages_config?: Array<{ name?: string }>;
  is_default?: boolean;
}

interface Batch {
  id: string;
  batch_number: number;
  start_chapter: number;
  end_chapter: number;
}

interface Execution {
  id: string;
  status: string;
  progress: number;
  current_stage?: string;
  current_step?: string;
  error_message?: string;
  result?: any;
}

interface ExecutionLog {
  id: string;
  stage?: string;
  event: string;
  message?: string;
  detail?: any;
  created_at?: string;
}

const PipelineExecution: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>();
  const [breakdownId, setBreakdownId] = useState<string>('');
  const [executionId, setExecutionId] = useState<string>();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPipelines();
    loadBatches();
  }, []);

  const loadPipelines = async () => {
    try {
      const res = await api.get('/pipelines');
      const list = [
        ...(res.data.user_pipelines || []),
        ...(res.data.default_pipelines || [])
      ];
      setPipelines(list);
      if (list.length > 0) {
        setSelectedPipelineId(list[0].id);
      }
    } catch (error) {
      message.error('加载Pipeline失败');
    }
  };

  const loadBatches = async () => {
    if (!projectId) return;
    try {
      const res = await api.get(`/projects/${projectId}/batches`);
      setBatches(res.data || []);
      if (res.data && res.data.length > 0) {
        setSelectedBatchId(res.data[0].id);
      }
    } catch (error) {
      message.error('加载批次失败');
    }
  };

  const selectedPipeline = useMemo(() => {
    return pipelines.find(p => p.id === selectedPipelineId);
  }, [pipelines, selectedPipelineId]);

  const stageNames = useMemo(() => {
    const stages = selectedPipeline?.stages_config || [];
    return stages.map(s => s.name).filter(Boolean) as string[];
  }, [selectedPipeline]);

  const needsBreakdownId = useMemo(() => {
    return stageNames.includes('script') && !stageNames.includes('breakdown');
  }, [stageNames]);

  const startExecution = async () => {
    if (!projectId || !selectedPipelineId) return;
    if (!selectedBatchId) {
      message.warning('请选择批次');
      return;
    }
    if (needsBreakdownId && !breakdownId) {
      message.warning('请输入 breakdown_id');
      return;
    }

    setLoading(true);
    try {
      const res = await api.post(`/pipelines/${selectedPipelineId}/execute`, {
        project_id: projectId,
        batch_id: selectedBatchId,
        breakdown_id: needsBreakdownId ? breakdownId : undefined
      });
      setExecutionId(res.data.execution_id);
      message.success('Pipeline已启动');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '启动失败');
    } finally {
      setLoading(false);
    }
  };

  const loadExecution = async () => {
    if (!selectedPipelineId || !executionId) return;
    try {
      const res = await api.get(`/pipelines/${selectedPipelineId}/executions/${executionId}`);
      setExecution(res.data);
    } catch (error) {
      message.error('加载执行状态失败');
    }
  };

  const loadLogs = async () => {
    if (!selectedPipelineId || !executionId) return;
    try {
      const res = await api.get(`/pipelines/${selectedPipelineId}/executions/${executionId}/logs`);
      setLogs(res.data.logs || []);
    } catch (error) {
      message.error('加载执行日志失败');
    }
  };

  useEffect(() => {
    if (!executionId || !selectedPipelineId) return;

    loadExecution();
    loadLogs();

    const timer = setInterval(() => {
      loadExecution();
      loadLogs();
    }, 2000);

    return () => clearInterval(timer);
  }, [executionId, selectedPipelineId]);

  const statusColor = (status?: string) => {
    if (status === 'completed') return 'success';
    if (status === 'failed') return 'error';
    if (status === 'running') return 'processing';
    return 'default';
  };

  return (
    <div>
      <Title level={4} style={{ marginTop: 0 }}>Pipeline 执行</Title>
      <Card bordered={false}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Space wrap>
            <div>
              <Text type="secondary">选择Pipeline</Text>
              <Select
                style={{ width: 260 }}
                value={selectedPipelineId}
                onChange={setSelectedPipelineId}
              >
                {pipelines.map(p => (
                  <Option key={p.id} value={p.id}>
                    {p.name}{p.is_default ? ' (默认)' : ''}
                  </Option>
                ))}
              </Select>
            </div>
            <div>
              <Text type="secondary">选择批次</Text>
              <Select
                style={{ width: 260 }}
                value={selectedBatchId}
                onChange={setSelectedBatchId}
              >
                {batches.map(b => (
                  <Option key={b.id} value={b.id}>
                    批次 {b.batch_number} ({b.start_chapter}-{b.end_chapter})
                  </Option>
                ))}
              </Select>
            </div>
            {needsBreakdownId && (
              <div>
                <Text type="secondary">Breakdown ID</Text>
                <Input
                  style={{ width: 260 }}
                  value={breakdownId}
                  onChange={(e) => setBreakdownId(e.target.value)}
                  placeholder="输入 breakdown_id"
                />
              </div>
            )}
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={startExecution}
              loading={loading}
            >
              执行 Pipeline
            </Button>
          </Space>

          <Divider />

          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Space>
              <Tag color={statusColor(execution?.status)}>{execution?.status || 'idle'}</Tag>
              {execution?.current_stage && (
                <Tag color="geekblue">{execution.current_stage}</Tag>
              )}
              <Text type="secondary">{execution?.current_step || '尚未开始'}</Text>
              <Button size="small" icon={<ReloadOutlined />} onClick={() => { loadExecution(); loadLogs(); }}>
                刷新
              </Button>
            </Space>
            <Progress percent={execution?.progress || 0} />
            {execution?.error_message && (
              <Text type="danger">错误: {execution.error_message}</Text>
            )}
          </Space>
        </Space>
      </Card>

      <Card title="执行结果" style={{ marginTop: 16 }} bordered={false}>
        <pre style={{ whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(execution?.result || {}, null, 2)}
        </pre>
      </Card>

      <Card title="执行日志" style={{ marginTop: 16 }} bordered={false}>
        <List
          dataSource={logs}
          renderItem={(log) => (
            <List.Item>
              <Space direction="vertical" size={0}>
                <Text>
                  <Tag>{log.stage || 'pipeline'}</Tag>
                  <Tag color="blue">{log.event}</Tag>
                  {log.message}
                </Text>
                {log.detail && (
                  <Text type="secondary">
                    {typeof log.detail === 'string' ? log.detail : JSON.stringify(log.detail)}
                  </Text>
                )}
                {log.created_at && (
                  <Text type="secondary">{log.created_at}</Text>
                )}
              </Space>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default PipelineExecution;
