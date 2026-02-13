import React, { useState, useEffect, useCallback } from 'react';
import { Button, Tag, message, Tooltip } from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassRangePicker } from '../../../components/ui/GlassDatePicker';

interface APILogEntry {
  id: string;
  method: string;
  path: string;
  query_params: string | null;
  user_id: string | null;
  username: string | null;
  user_ip: string;
  user_agent: string;
  status_code: number;
  response_time: number;
  error_message: string | null;
  created_at: string | null;
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
  const [pageSize, setPageSize] = useState(50);

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
    </div>
  );
};

export default APILogsTab;
