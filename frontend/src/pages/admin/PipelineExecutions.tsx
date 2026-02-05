import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Space, Button, Modal, Typography, Select, Input, message, Descriptions, InputNumber } from 'antd';
import { ReloadOutlined, FileSearchOutlined, InfoCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const { Text } = Typography;
const { Option } = Select;

interface ExecutionRow {
  id: string;
  pipeline_id: string;
  pipeline_name?: string;
  project_id?: string;
  project_name?: string;
  status: string;
  progress: number;
  current_stage?: string;
  current_step?: string;
  error_message?: string;
  created_at?: string;
  completed_at?: string;
}

interface ExecutionLog {
  id: string;
  stage?: string;
  event: string;
  message?: string;
  detail?: any;
  created_at?: string;
}

const PipelineExecutions: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [executions, setExecutions] = useState<ExecutionRow[]>([]);
  const [status, setStatus] = useState<string>();
  const [pipelineId, setPipelineId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [logsVisible, setLogsVisible] = useState(false);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [logEventFilter, setLogEventFilter] = useState<string>();
  const [logStageFilter, setLogStageFilter] = useState<string>();
  const [logLimit, setLogLimit] = useState<number>(100);

  const loadExecutions = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/pipelines/executions', {
        params: {
          status,
          pipeline_id: pipelineId || undefined,
          project_id: projectId || undefined,
          skip: 0,
          limit: 50
        }
      });
      setExecutions(res.data.executions || []);
    } catch (error) {
      message.error('加载执行列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async (executionId: string) => {
    try {
      const res = await api.get(`/admin/pipelines/executions/${executionId}/logs`, {
        params: { skip: 0, limit: logLimit }
      });
      setLogs(res.data.logs || []);
      setLogsVisible(true);
      setSelectedExecutionId(executionId);
    } catch (error) {
      message.error('加载执行日志失败');
    }
  };

  const loadLogsWithFilter = async () => {
    if (!selectedExecutionId) return;
    try {
      const res = await api.get(`/admin/pipelines/executions/${selectedExecutionId}/logs`, {
        params: {
          skip: 0,
          limit: logLimit
        }
      });
      setLogs(res.data.logs || []);
    } catch (error) {
      message.error('加载执行日志失败');
    }
  };

  const loadDetail = async (executionId: string) => {
    setDetailLoading(true);
    try {
      const res = await api.get(`/admin/pipelines/executions/${executionId}`);
      setDetail(res.data);
      setDetailVisible(true);
      setSelectedExecutionId(executionId);
      setLogEventFilter(undefined);
      setLogStageFilter(undefined);
    } catch (error) {
      message.error('加载执行详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      loadExecutions();
    }
  }, [user?.role]);

  if (user?.role !== 'admin') {
    return (
      <Card bordered={false}>
        <Text type="danger">无权限访问管理员视图</Text>
      </Card>
    );
  }

  const statusColor = (value: string) => {
    if (value === 'completed') return 'success';
    if (value === 'failed') return 'error';
    if (value === 'running') return 'processing';
    return 'default';
  };

  const columns = [
    {
      title: '执行ID',
      dataIndex: 'id',
      key: 'id',
      ellipsis: true
    },
    {
      title: 'Pipeline',
      dataIndex: 'pipeline_name',
      key: 'pipeline_name',
      render: (_: string, record: ExecutionRow) => (
        <Space direction="vertical" size={0}>
          <span>{record.pipeline_name || '未知'}</span>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.pipeline_id}</Text>
        </Space>
      )
    },
    {
      title: '项目',
      dataIndex: 'project_name',
      key: 'project_name',
      render: (_: string, record: ExecutionRow) => (
        <Space direction="vertical" size={0}>
          <span>{record.project_name || '未知'}</span>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.project_id}</Text>
        </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag>
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress'
    },
    {
      title: '当前阶段',
      dataIndex: 'current_stage',
      key: 'current_stage'
    },
    {
      title: '当前步骤',
      dataIndex: 'current_step',
      key: 'current_step'
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: ExecutionRow) => (
        <Space>
          <Button
            size="small"
            icon={<InfoCircleOutlined />}
            onClick={() => loadDetail(record.id)}
          >
            查看详情
          </Button>
          <Button
            size="small"
            icon={<FileSearchOutlined />}
            onClick={() => loadLogs(record.id)}
          >
            查看日志
          </Button>
        </Space>
      )
    }
  ];

  const summary = () => {
    const byEvent: Record<string, number> = {};
    const byStage: Record<string, number> = {};
    logs.forEach((log) => {
      const event = log.event || 'unknown';
      const stage = log.stage || 'pipeline';
      byEvent[event] = (byEvent[event] || 0) + 1;
      byStage[stage] = (byStage[stage] || 0) + 1;
    });
    return { byEvent, byStage };
  };

  const filteredLogs = logs.filter((log) => {
    if (logEventFilter && log.event !== logEventFilter) return false;
    if (logStageFilter && log.stage !== logStageFilter) return false;
    return true;
  });

  return (
    <div>
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            allowClear
            placeholder="状态过滤"
            style={{ width: 160 }}
            value={status}
            onChange={setStatus}
          >
            <Option value="pending">pending</Option>
            <Option value="running">running</Option>
            <Option value="completed">completed</Option>
            <Option value="failed">failed</Option>
          </Select>
          <Input
            placeholder="Pipeline ID"
            style={{ width: 220 }}
            value={pipelineId}
            onChange={(e) => setPipelineId(e.target.value)}
          />
          <Input
            placeholder="Project ID"
            style={{ width: 220 }}
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          />
          <Button type="primary" onClick={loadExecutions} loading={loading}>
            查询
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadExecutions}>
            刷新
          </Button>
        </Space>
      </Card>

      <Card bordered={false}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={executions}
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title="执行详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={900}
      >
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="执行ID">{detail?.id}</Descriptions.Item>
          <Descriptions.Item label="Pipeline">{detail?.pipeline_name || detail?.pipeline_id}</Descriptions.Item>
          <Descriptions.Item label="项目">{detail?.project_name || detail?.project_id}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusColor(detail?.status)}>{detail?.status || '-'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="进度">{detail?.progress ?? 0}</Descriptions.Item>
          <Descriptions.Item label="当前阶段">{detail?.current_stage || '-'}</Descriptions.Item>
          <Descriptions.Item label="当前步骤">{detail?.current_step || '-'}</Descriptions.Item>
          <Descriptions.Item label="开始时间">{detail?.started_at || '-'}</Descriptions.Item>
          <Descriptions.Item label="完成时间">{detail?.completed_at || '-'}</Descriptions.Item>
          <Descriptions.Item label="错误信息" span={2}>
            {detail?.error_message || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="结果" span={2}>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {detail?.result ? JSON.stringify(detail.result, null, 2) : '{}'}
            </pre>
          </Descriptions.Item>
        </Descriptions>
        {detailLoading && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            加载中...
          </Text>
        )}
      </Modal>

      <Modal
        title="执行日志"
        open={logsVisible}
        onCancel={() => setLogsVisible(false)}
        footer={null}
        width={800}
      >
        <Space style={{ marginBottom: 12 }} wrap>
          <Select
            allowClear
            placeholder="事件过滤"
            style={{ width: 200 }}
            value={logEventFilter}
            onChange={setLogEventFilter}
          >
            {Array.from(new Set(logs.map((l) => l.event))).map((event) => (
              <Option key={event} value={event}>{event}</Option>
            ))}
          </Select>
          <Select
            allowClear
            placeholder="阶段过滤"
            style={{ width: 200 }}
            value={logStageFilter}
            onChange={setLogStageFilter}
          >
            {Array.from(new Set(logs.map((l) => l.stage || 'pipeline'))).map((stage) => (
              <Option key={stage} value={stage}>{stage}</Option>
            ))}
          </Select>
          <InputNumber
            min={10}
            max={500}
            value={logLimit}
            onChange={(value) => setLogLimit(value || 100)}
          />
          <Button onClick={loadLogsWithFilter}>刷新日志</Button>
        </Space>

        <Space style={{ marginBottom: 12 }} wrap>
          {Object.entries(summary().byEvent).map(([event, count]) => (
            <Tag key={event} color="blue">{event}: {count}</Tag>
          ))}
          {Object.entries(summary().byStage).map(([stage, count]) => (
            <Tag key={stage} color="geekblue">{stage}: {count}</Tag>
          ))}
        </Space>

        <Table
          rowKey="id"
          dataSource={filteredLogs}
          pagination={false}
          columns={[
            { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 200 },
            { title: '阶段', dataIndex: 'stage', key: 'stage', width: 120 },
            { title: '事件', dataIndex: 'event', key: 'event', width: 160 },
            { title: '消息', dataIndex: 'message', key: 'message' }
          ]}
        />
        {selectedExecutionId && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            执行ID：{selectedExecutionId}
          </Text>
        )}
      </Modal>
    </div>
  );
};

export default PipelineExecutions;
