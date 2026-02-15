import React, { useState, useEffect, useCallback } from 'react';
import { Button, Tag, message, Tooltip, Descriptions } from 'antd';
import { ReloadOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassRangePicker } from '../../../components/ui/GlassDatePicker';
import { GlassModal } from '../../../components/ui/GlassModal';

interface APILogEntry {
  id: string;
  method: string;
  path: string;
  query_params: string | null;
  request_body: string | null;  // 新增：请求体
  user_id: string | null;
  username: string | null;
  user_ip: string;
  user_agent: string;
  status_code: number;
  response_body: string | null;  // 新增：响应体
  response_time: number;
  error_message: string | null;
  created_at: string | null;
}

interface APILogDetail extends APILogEntry {
  // 详情扩展
}

interface APILogStats {
  total_requests: number;
  success_requests: number;
  error_requests: number;
  avg_response_time: number;
  requests_by_method: Record<string, number>;
  top_paths: Array<{ path: string; count: number }>;
}

const APILogsTab: React.FC = () => {
  const [logs, setLogs] = useState<APILogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<APILogStats | null>(null);

  // 筛选条件
  const [method, setMethod] = useState<string | undefined>(undefined);
  const [path, setPath] = useState('');
  const [statusCode, setStatusCode] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);  // 默认 10 条

  // 详情弹窗
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<APILogEntry | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 加载日志列表
  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        skip: (page - 1) * pageSize,
        limit: pageSize
      };

      if (method) params.method = method;
      if (path) params.path = path;
      if (statusCode) params.status_code = parseInt(statusCode);
      if (dateRange) {
        params.date_from = dateRange[0].format('YYYY-MM-DD');
        params.date_to = dateRange[1].format('YYYY-MM-DD');
      }

      const response = await api.get('/admin/api-logs', { params });
      setLogs(response.data.logs);
      setTotal(response.data.total);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载 API 日志失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, method, path, statusCode, dateRange]);

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const response = await api.get('/admin/api-logs/stats', { params: { period: 'day' } });
      setStats(response.data);
    } catch (error) {
      console.error('加载 API 统计失败:', error);
    }
  }, []);

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

  // 查看详情
  const handleViewDetail = (record: APILogEntry) => {
    setSelectedLog(record);
    setModalVisible(true);
  };

  // 状态码标签
  const getStatusCodeTag = (code: number) => {
    if (code >= 200 && code < 300) {
      return <Tag color="success">{code}</Tag>;
    } else if (code >= 400 && code < 500) {
      return <Tag color="warning">{code}</Tag>;
    } else if (code >= 500) {
      return <Tag color="error">{code}</Tag>;
    }
    return <Tag>{code}</Tag>;
  };

  // 方法标签
  const getMethodTag = (m: string) => {
    const colors: Record<string, string> = {
      GET: 'blue',
      POST: 'green',
      PUT: 'orange',
      DELETE: 'red',
      PATCH: 'purple'
    };
    return <Tag color={colors[m] || 'default'}>{m}</Tag>;
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
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (m: string) => getMethodTag(m)
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      render: (p: string) => (
        <Tooltip title={p}>
          <span className="font-mono text-xs">{p}</span>
        </Tooltip>
      )
    },
    {
      title: '状态',
      dataIndex: 'status_code',
      key: 'status_code',
      width: 80,
      render: (code: number) => getStatusCodeTag(code)
    },
    {
      title: '耗时',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 80,
      render: (time: number) => (
        <span className={`font-mono text-xs ${time > 1000 ? 'text-red-400' : time > 500 ? 'text-amber-400' : 'text-green-400'}`}>
          {time}ms
        </span>
      )
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 100,
      render: (name: string | null) => name || <span className="text-slate-500">匿名</span>
    },
    {
      title: 'IP',
      dataIndex: 'user_ip',
      key: 'user_ip',
      width: 120,
      render: (ip: string) => <span className="font-mono text-xs">{ip}</span>
    },
    {
      title: '错误',
      dataIndex: 'error_message',
      key: 'error_message',
      width: 150,
      ellipsis: true,
      render: (err: string | null) => err ? (
        <Tooltip title={err}>
          <span className="text-red-400 text-xs">{err}</span>
        </Tooltip>
      ) : '-'
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: APILogEntry) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
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
        <div className="grid grid-cols-4 gap-4 mb-6">
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">今日请求</div>
            <div className="text-2xl font-bold text-slate-100">{stats.total_requests}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">成功请求</div>
            <div className="text-2xl font-bold text-green-400">{stats.success_requests}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">错误请求</div>
            <div className="text-2xl font-bold text-red-400">{stats.error_requests}</div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="text-slate-400 text-sm mb-1">平均响应</div>
            <div className="text-2xl font-bold text-cyan-400">{stats.avg_response_time}ms</div>
          </GlassCard>
        </div>
      )}

      <GlassCard>
        <div className="mb-4 flex justify-between items-center">
          <h2 className="text-xl font-bold text-slate-100">API 请求日志</h2>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { loadLogs(); loadStats(); }}
          >
            刷新
          </Button>
        </div>

        {/* 筛选器 */}
        <div className="mb-4 flex gap-4 flex-wrap">
          <GlassInput
            placeholder="搜索路径"
            allowClear
            style={{ width: 200 }}
            prefix={<SearchOutlined className="text-slate-500" />}
            onPressEnter={handleSearch}
            onChange={(e) => setPath(e.target.value)}
          />
          <GlassSelect
            placeholder="请求方法"
            allowClear
            style={{ width: 120 }}
            onChange={setMethod}
            options={[
              { value: 'GET', label: 'GET' },
              { value: 'POST', label: 'POST' },
              { value: 'PUT', label: 'PUT' },
              { value: 'DELETE', label: 'DELETE' }
            ]}
          />
          <GlassSelect
            placeholder="状态码"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusCode}
            options={[
              { value: '200', label: '2xx 成功' },
              { value: '400', label: '4xx 客户端错误' },
              { value: '500', label: '5xx 服务端错误' }
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

        {/* 热门路径 */}
        {stats && stats.top_paths.length > 0 && (
          <div className="mt-4 p-4 bg-slate-800/30 rounded-lg">
            <div className="text-sm text-slate-400 mb-2">热门路径 Top 10</div>
            <div className="flex flex-wrap gap-2">
              {stats.top_paths.map((item, idx) => (
                <Tag key={idx} className="font-mono text-xs">
                  {item.path} <span className="text-cyan-400">({item.count})</span>
                </Tag>
              ))}
            </div>
          </div>
        )}
      </GlassCard>

      {/* 详情弹窗 */}
      <GlassModal
        title="API 请求详情"
        open={modalVisible}
        onCancel={() => { setModalVisible(false); setSelectedLog(null); }}
        width={800}
        footer={null}
      >
        {selectedLog && (
          <div className="space-y-4">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="请求ID">
                <span className="font-mono text-xs">{selectedLog.id}</span>
              </Descriptions.Item>
              <Descriptions.Item label="时间">
                {formatTime(selectedLog.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="方法">
                {getMethodTag(selectedLog.method)}
              </Descriptions.Item>
              <Descriptions.Item label="状态码">
                {getStatusCodeTag(selectedLog.status_code)}
              </Descriptions.Item>
              <Descriptions.Item label="路径" span={2}>
                <span className="font-mono text-xs">{selectedLog.path}</span>
              </Descriptions.Item>
              <Descriptions.Item label="用户">
                {selectedLog.username || <span className="text-slate-500">匿名</span>}
              </Descriptions.Item>
              <Descriptions.Item label="用户ID">
                <span className="font-mono text-xs">{selectedLog.user_id || '-'}</span>
              </Descriptions.Item>
              <Descriptions.Item label="IP地址">
                <span className="font-mono text-xs">{selectedLog.user_ip}</span>
              </Descriptions.Item>
              <Descriptions.Item label="响应时间">
                <span className={`font-mono text-xs ${selectedLog.response_time > 1000 ? 'text-red-400' : selectedLog.response_time > 500 ? 'text-amber-400' : 'text-green-400'}`}>
                  {selectedLog.response_time}ms
                </span>
              </Descriptions.Item>
            </Descriptions>

            {/* Query 参数 */}
            {selectedLog.query_params && (
              <div>
                <div className="text-sm text-slate-400 mb-2">Query 参数</div>
                <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg max-h-40 overflow-y-auto">
                  <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono">
                    {selectedLog.query_params}
                  </pre>
                </div>
              </div>
            )}

            {/* 请求体 */}
            {selectedLog.request_body && (
              <div>
                <div className="text-sm text-slate-400 mb-2">请求体</div>
                <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg max-h-60 overflow-y-auto">
                  <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono">
                    {selectedLog.request_body}
                  </pre>
                </div>
              </div>
            )}

            {/* 响应体 */}
            {selectedLog.response_body && (
              <div>
                <div className="text-sm text-slate-400 mb-2">响应体</div>
                <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg max-h-60 overflow-y-auto">
                  <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono">
                    {selectedLog.response_body}
                  </pre>
                </div>
              </div>
            )}

            {/* User Agent */}
            {selectedLog.user_agent && (
              <div>
                <div className="text-sm text-slate-400 mb-2">User Agent</div>
                <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                  <pre className="text-slate-400 text-xs whitespace-pre-wrap font-mono">
                    {selectedLog.user_agent}
                  </pre>
                </div>
              </div>
            )}

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

export default APILogsTab;
