import React, { useState, useEffect, useCallback } from 'react';
import { Button, Tag, message, Descriptions, Tooltip } from 'antd';
import { ReloadOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassRangePicker } from '../../../components/ui/GlassDatePicker';
import { GlassModal } from '../../../components/ui/GlassModal';

interface LLMLogEntry {
  id: string;
  task_id: string | null;
  user_id: string | null;
  username: string | null;
  provider: string;
  model_name: string;
  skill_name: string | null;
  stage: string | null;
  prompt_preview: string;
  response_preview: string | null;
  prompt_tokens: number | null;
  response_tokens: number | null;
  total_tokens: number | null;
  latency_ms: number | null;
  status: string;
  error_message: string | null;
  created_at: string | null;
}

interface LLMLogDetail {
  id: string;
  task_id: string | null;
  user_id: string | null;
  username: string | null;
  project_id: string | null;
  provider: string;
  model_name: string;
  skill_name: string | null;
  stage: string | null;
  prompt: string;
  response: string | null;
  prompt_tokens: number | null;
  response_tokens: number | null;
  total_tokens: number | null;
  temperature: number | null;
  max_tokens: number | null;
  latency_ms: number | null;
  status: string;
  error_message: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
}

interface LLMLogStats {
  total_calls: number;
  success_calls: number;
  error_calls: number;
  total_tokens: number;
  avg_latency_ms: number;
  calls_by_provider: Record<string, number>;
  top_models: Array<{ model: string; count: number }>;
  top_skills: Array<{ skill: string; count: number }>;
}

const LLMLogsTab: React.FC = () => {
  const [logs, setLogs] = useState<LLMLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<LLMLogStats | null>(null);

  // 筛选条件
  const [provider, setProvider] = useState<string | undefined>(undefined);
  const [modelName, setModelName] = useState('');
  const [skillName, setSkillName] = useState('');
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // 详情弹窗
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<LLMLogDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 加载日志列表
  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        skip: (page - 1) * pageSize,
        limit: pageSize
      };

      if (provider) params.provider = provider;
      if (modelName) params.model_name = modelName;
      if (skillName) params.skill_name = skillName;
      if (status) params.status = status;
      if (dateRange) {
        params.date_from = dateRange[0].format('YYYY-MM-DD');
        params.date_to = dateRange[1].format('YYYY-MM-DD');
      }

      const response = await api.get('/admin/llm-logs', { params });
      setLogs(response.data.logs);
      setTotal(response.data.total);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载 LLM 日志失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, provider, modelName, skillName, status, dateRange]);

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const response = await api.get('/admin/llm-logs/stats/summary', { params: { period: 'day' } });
      setStats(response.data);
    } catch (error) {
      console.error('加载 LLM 统计失败:', error);
    }
  }, []);

  // 加载详情
  const loadDetail = async (logId: string) => {
    setDetailLoading(true);
    try {
      const response = await api.get(`/admin/llm-logs/${logId}`);
      setSelectedLog(response.data);
      setModalVisible(true);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleSearch = () => {
    setPage(1);
    loadLogs();
  };

  // 提供商标签
  const getProviderTag = (p: string) => {
    const colors: Record<string, string> = {
      openai: 'green',
      anthropic: 'purple',
      gemini: 'blue'
    };
    return <Tag color={colors[p] || 'default'}>{p}</Tag>;
  };

  // 状态标签
  const getStatusTag = (s: string) => {
    return s === 'success'
      ? <Tag color="success">成功</Tag>
      : <Tag color="error">失败</Tag>;
  };

  // 格式化时间
  const formatTime = (timeStr: string | null) => {
    if (!timeStr) return '-';
    return dayjs(timeStr).format('MM-DD HH:mm:ss');
  };

  // 表格列定义
  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      render: (time: string | null) => formatTime(time)
    },
    {
      title: '提供商',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      render: (p: string) => getProviderTag(p)
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 150,
      ellipsis: true,
      render: (name: string) => (
        <Tooltip title={name}>
          <span className="font-mono text-xs">{name}</span>
        </Tooltip>
      )
    },
    {
      title: 'Skill',
      dataIndex: 'skill_name',
      key: 'skill_name',
      width: 120,
      ellipsis: true,
      render: (name: string | null) => name || '-'
    },
    {
      title: 'Prompt',
      dataIndex: 'prompt_preview',
      key: 'prompt_preview',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span className="text-xs text-slate-400">{text}</span>
        </Tooltip>
      )
    },
    {
      title: 'Tokens',
      key: 'tokens',
      width: 100,
      render: (_: unknown, record: LLMLogEntry) => (
        <span className="font-mono text-xs">
          {record.total_tokens || '-'}
        </span>
      )
    },
    {
      title: '延迟',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      width: 80,
      render: (time: number | null) => time ? (
        <span className={`font-mono text-xs ${time > 5000 ? 'text-red-400' : time > 2000 ? 'text-amber-400' : 'text-green-400'}`}>
          {time}ms
        </span>
      ) : '-'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (s: string) => getStatusTag(s)
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: LLMLogEntry) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          loading={detailLoading}
          onClick={() => loadDetail(record.id)}
        >
          详情
        </Button>
      )
    }
  ];

  return (
    <div>
      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-5 gap-4 mb-6">
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">今日调用</div>
            <div className="text-2xl font-bold text-slate-100">{stats.total_calls}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">成功</div>
            <div className="text-2xl font-bold text-green-400">{stats.success_calls}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">失败</div>
            <div className="text-2xl font-bold text-red-400">{stats.error_calls}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">Token 消耗</div>
            <div className="text-2xl font-bold text-purple-400">{stats.total_tokens.toLocaleString()}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">平均延迟</div>
            <div className="text-2xl font-bold text-cyan-400">{stats.avg_latency_ms}ms</div>
          </GlassCard>
        </div>
      )}

      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <h2 className="text-xl font-bold text-slate-100">LLM 调用日志</h2>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { loadLogs(); loadStats(); }}
          >
            刷新
          </Button>
        </div>

        {/* 筛选器 */}
        <div className="mb-4 flex gap-4 flex-wrap">
          <GlassSelect
            placeholder="提供商"
            allowClear
            style={{ width: 120 }}
            onChange={setProvider}
            options={[
              { value: 'openai', label: 'OpenAI' },
              { value: 'anthropic', label: 'Anthropic' },
              { value: 'gemini', label: 'Gemini' }
            ]}
          />
          <GlassInput
            placeholder="模型名称"
            allowClear
            style={{ width: 150 }}
            onChange={(e) => setModelName(e.target.value)}
          />
          <GlassInput
            placeholder="Skill 名称"
            allowClear
            style={{ width: 150 }}
            onChange={(e) => setSkillName(e.target.value)}
          />
          <GlassSelect
            placeholder="状态"
            allowClear
            style={{ width: 100 }}
            onChange={setStatus}
            options={[
              { value: 'success', label: '成功' },
              { value: 'error', label: '失败' }
            ]}
          />
          <GlassRangePicker
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
            搜索
          </Button>
        </div>

        {/* 日志列表 */}
        <GlassTable
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            pageSizeOptions: ['20', '50', '100'],
            showTotal: (t) => `共 ${t} 条记录`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); }
          }}
          size="small"
        />

        {/* 热门统计 */}
        {stats && (stats.top_models.length > 0 || stats.top_skills.length > 0) && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            {stats.top_models.length > 0 && (
              <div className="p-4 bg-slate-800/30 rounded-lg">
                <div className="text-sm text-slate-400 mb-2">热门模型</div>
                <div className="flex flex-wrap gap-2">
                  {stats.top_models.map((item, idx) => (
                    <Tag key={idx} className="font-mono text-xs">
                      {item.model} <span className="text-cyan-400">({item.count})</span>
                    </Tag>
                  ))}
                </div>
              </div>
            )}
            {stats.top_skills.length > 0 && (
              <div className="p-4 bg-slate-800/30 rounded-lg">
                <div className="text-sm text-slate-400 mb-2">热门 Skill</div>
                <div className="flex flex-wrap gap-2">
                  {stats.top_skills.map((item, idx) => (
                    <Tag key={idx} className="font-mono text-xs">
                      {item.skill} <span className="text-purple-400">({item.count})</span>
                    </Tag>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </GlassCard>

      {/* 详情弹窗 */}
      <GlassModal
        title="LLM 调用详情"
        open={modalVisible}
        onCancel={() => { setModalVisible(false); setSelectedLog(null); }}
        width={800}
        footer={null}
      >
        {selectedLog && (
          <div className="space-y-4">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="提供商">
                {getProviderTag(selectedLog.provider)}
              </Descriptions.Item>
              <Descriptions.Item label="模型">
                <span className="font-mono text-xs">{selectedLog.model_name}</span>
              </Descriptions.Item>
              <Descriptions.Item label="Skill">
                {selectedLog.skill_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="阶段">
                {selectedLog.stage || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {getStatusTag(selectedLog.status)}
              </Descriptions.Item>
              <Descriptions.Item label="延迟">
                {selectedLog.latency_ms}ms
              </Descriptions.Item>
              <Descriptions.Item label="Prompt Tokens">
                {selectedLog.prompt_tokens || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Response Tokens">
                {selectedLog.response_tokens || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Temperature">
                {selectedLog.temperature ?? '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Max Tokens">
                {selectedLog.max_tokens || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="时间" span={2}>
                {formatTime(selectedLog.created_at)}
              </Descriptions.Item>
            </Descriptions>

            {/* Prompt */}
            <div>
              <div className="text-sm text-slate-400 mb-2">Prompt</div>
              <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg max-h-60 overflow-y-auto">
                <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono">
                  {selectedLog.prompt}
                </pre>
              </div>
            </div>

            {/* Response */}
            <div>
              <div className="text-sm text-slate-400 mb-2">Response</div>
              <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg max-h-60 overflow-y-auto">
                <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono">
                  {selectedLog.response || '(无响应)'}
                </pre>
              </div>
            </div>

            {/* 错误信息 */}
            {selectedLog.error_message && (
              <div>
                <div className="text-sm text-slate-400 mb-2">错误信息</div>
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <pre className="text-red-400 text-xs whitespace-pre-wrap font-mono">
                    {selectedLog.error_message}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </GlassModal>
    </div>
  );
};

export default LLMLogsTab;
