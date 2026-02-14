import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Select, Table, Tabs, Spin, Empty } from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
  PercentageOutlined, BarChartOutlined, ReloadOutlined
} from '@ant-design/icons';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart
} from 'recharts';
import { adminAnalyticsApi } from '../../../services/api';

const { Option } = Select;

// 类型定义
interface OverviewData {
  period: string;
  total: number;
  passed: number;
  failed: number;
  pending: number;
  pass_rate: number;
  avg_score: number;
  avg_retry: number;
}

interface ModelData {
  provider: string;
  model_name: string;
  display_name: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
}

interface ResourceData {
  resource_id: string;
  name: string;
  display_name: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
}

interface DistributionItem {
  range: string;
  label: string;
  count: number;
  color: string;
}

interface TrendItem {
  date: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
}

interface RetryStatItem {
  retry_count: string;
  count: number;
  color: string;
}

const AnalyticsPage: React.FC = () => {
  const [period, setPeriod] = useState<string>('week');
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [modelData, setModelData] = useState<ModelData[]>([]);
  const [resourceData, setResourceData] = useState<ResourceData[]>([]);
  const [distribution, setDistribution] = useState<DistributionItem[]>([]);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [retryStats, setRetryStats] = useState<{ stats: RetryStatItem[]; avg_retry: number } | null>(null);

  // 加载数据
  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewRes, modelRes, resourceRes, distRes, trendRes, retryRes] = await Promise.all([
        adminAnalyticsApi.getBreakdownOverview(period),
        adminAnalyticsApi.getBreakdownByModel(period),
        adminAnalyticsApi.getBreakdownByResource(period),
        adminAnalyticsApi.getScoreDistribution(period),
        adminAnalyticsApi.getBreakdownTrend(period),
        adminAnalyticsApi.getRetryStats(period)
      ]);

      setOverview(overviewRes.data);
      setModelData(modelRes.data.models || []);
      setResourceData(resourceRes.data.resources || []);
      setDistribution(distRes.data.distribution || []);
      setTrend(trendRes.data.trend || []);
      setRetryStats(retryRes.data);
    } catch (error) {
      console.error('获取分析数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [period]);

  // 模型表格列
  const modelColumns = [
    {
      title: '模型',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string) => <span className="text-cyan-400">{text}</span>
    },
    {
      title: '总数',
      dataIndex: 'total',
      key: 'total',
      sorter: (a: ModelData, b: ModelData) => a.total - b.total
    },
    {
      title: '通过',
      dataIndex: 'passed',
      key: 'passed',
      render: (val: number) => <span className="text-green-400">{val}</span>
    },
    {
      title: '失败',
      dataIndex: 'failed',
      key: 'failed',
      render: (val: number) => <span className="text-red-400">{val}</span>
    },
    {
      title: '通过率',
      dataIndex: 'pass_rate',
      key: 'pass_rate',
      sorter: (a: ModelData, b: ModelData) => a.pass_rate - b.pass_rate,
      render: (val: number) => (
        <span className={val >= 80 ? 'text-green-400' : val >= 60 ? 'text-yellow-400' : 'text-red-400'}>
          {val}%
        </span>
      )
    },
    {
      title: '平均分',
      dataIndex: 'avg_score',
      key: 'avg_score',
      sorter: (a: ModelData, b: ModelData) => a.avg_score - b.avg_score,
      render: (val: number) => <span className="text-slate-300">{val}</span>
    }
  ];

  // 资源表格列
  const resourceColumns = [
    {
      title: '方法论',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string) => <span className="text-purple-400">{text}</span>
    },
    {
      title: '总数',
      dataIndex: 'total',
      key: 'total',
      sorter: (a: ResourceData, b: ResourceData) => a.total - b.total
    },
    {
      title: '通过',
      dataIndex: 'passed',
      key: 'passed',
      render: (val: number) => <span className="text-green-400">{val}</span>
    },
    {
      title: '失败',
      dataIndex: 'failed',
      key: 'failed',
      render: (val: number) => <span className="text-red-400">{val}</span>
    },
    {
      title: '通过率',
      dataIndex: 'pass_rate',
      key: 'pass_rate',
      sorter: (a: ResourceData, b: ResourceData) => a.pass_rate - b.pass_rate,
      render: (val: number) => (
        <span className={val >= 80 ? 'text-green-400' : val >= 60 ? 'text-yellow-400' : 'text-red-400'}>
          {val}%
        </span>
      )
    },
    {
      title: '平均分',
      dataIndex: 'avg_score',
      key: 'avg_score',
      sorter: (a: ResourceData, b: ResourceData) => a.avg_score - b.avg_score,
      render: (val: number) => <span className="text-slate-300">{val}</span>
    }
  ];

  // 格式化日期
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    if (period === 'day') {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
  };

  // Tab 内容
  const tabItems = [
    {
      key: 'model',
      label: '模型分析',
      children: (
        <div className="space-y-6">
          {/* 模型柱状图 */}
          <Card bordered={false} className="bg-slate-800">
            <h4 className="text-slate-300 mb-4">各模型质检通过率对比</h4>
            {modelData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={modelData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="model_name" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Legend />
                  <Bar dataKey="passed" name="通过" fill="#22c55e" />
                  <Bar dataKey="failed" name="失败" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>

          {/* 模型表格 */}
          <Card bordered={false} className="bg-slate-800">
            <h4 className="text-slate-300 mb-4">模型详细数据</h4>
            <Table
              dataSource={modelData}
              columns={modelColumns}
              rowKey="display_name"
              pagination={false}
              className="ant-table-dark-glass"
            />
          </Card>
        </div>
      )
    },
    {
      key: 'resource',
      label: '模板分析',
      children: (
        <div className="space-y-6">
          {/* 资源柱状图 */}
          <Card bordered={false} className="bg-slate-800">
            <h4 className="text-slate-300 mb-4">各方法论质检通过率对比</h4>
            {resourceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={resourceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="display_name" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Legend />
                  <Bar dataKey="passed" name="通过" fill="#22c55e" />
                  <Bar dataKey="failed" name="失败" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>

          {/* 资源表格 */}
          <Card bordered={false} className="bg-slate-800">
            <h4 className="text-slate-300 mb-4">方法论详细数据</h4>
            <Table
              dataSource={resourceData}
              columns={resourceColumns}
              rowKey="resource_id"
              pagination={false}
              className="ant-table-dark-glass"
            />
          </Card>
        </div>
      )
    },
    {
      key: 'distribution',
      label: '分数分布',
      children: (
        <Card bordered={false} className="bg-slate-800">
          <h4 className="text-slate-300 mb-4">质检分数分布</h4>
          {distribution.length > 0 ? (
            <div className="flex flex-col lg:flex-row gap-8">
              {/* 饼图 */}
              <div className="flex-1">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={distribution.filter(d => d.count > 0)}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="count"
                      nameKey="label"
                    >
                      {distribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* 柱状图 */}
              <div className="flex-1">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={distribution} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                    <YAxis dataKey="label" type="category" stroke="#94a3b8" fontSize={12} width={60} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                    />
                    <Bar dataKey="count" name="数量">
                      {distribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <Empty description="暂无数据" />
          )}
        </Card>
      )
    },
    {
      key: 'trend',
      label: '趋势分析',
      children: (
        <Card bordered={false} className="bg-slate-800">
          <h4 className="text-slate-300 mb-4">拆解任务趋势</h4>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tickFormatter={formatDate} stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                  labelFormatter={formatDate}
                />
                <Legend />
                <Area type="monotone" dataKey="total" name="总数" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                <Area type="monotone" dataKey="passed" name="通过" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                <Area type="monotone" dataKey="failed" name="失败" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <Empty description="暂无数据" />
          )}
        </Card>
      )
    },
    {
      key: 'retry',
      label: '重试统计',
      children: (
        <Card bordered={false} className="bg-slate-800">
          <h4 className="text-slate-300 mb-4">重试次数分布</h4>
          {retryStats && retryStats.stats.length > 0 ? (
            <div className="flex flex-col lg:flex-row gap-8">
              {/* 柱状图 */}
              <div className="flex-1">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={retryStats.stats}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="retry_count" stroke="#94a3b8" fontSize={12} />
                    <YAxis stroke="#94a3b8" fontSize={12} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                    />
                    <Bar dataKey="count" name="数量">
                      {retryStats.stats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* 统计信息 */}
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <p className="text-slate-400 mb-2">平均重试次数</p>
                  <p className="text-5xl font-bold text-cyan-400">{retryStats.avg_retry}</p>
                  <p className="text-slate-500 mt-2">次/任务</p>
                </div>
              </div>
            </div>
          ) : (
            <Empty description="暂无数据" />
          )}
        </Card>
      )
    }
  ];

  return (
    <div className="p-6 h-full overflow-y-auto">
      {/* 标题栏 */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-100">数据分析</h1>
        <div className="flex items-center gap-4">
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 120 }}
            popupClassName="dark-glass-dropdown"
          >
            <Option value="day">今日</Option>
            <Option value="week">本周</Option>
            <Option value="month">本月</Option>
            <Option value="quarter">本季度</Option>
            <Option value="year">本年</Option>
          </Select>
          <button
            onClick={fetchData}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg flex items-center gap-2 transition-colors"
          >
            <ReloadOutlined spin={loading} />
            刷新
          </button>
        </div>
      </div>

      <Spin spinning={loading}>
        {/* 概览卡片 */}
        <Row gutter={[16, 16]} className="mb-6">
          <Col xs={24} sm={12} lg={4}>
            <Card bordered={false} className="bg-slate-800">
              <Statistic
                title={<span className="text-slate-400">总拆解数</span>}
                value={overview?.total || 0}
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#3b82f6' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card bordered={false} className="bg-slate-800">
              <Statistic
                title={<span className="text-slate-400">通过数</span>}
                value={overview?.passed || 0}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#22c55e' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card bordered={false} className="bg-slate-800">
              <Statistic
                title={<span className="text-slate-400">失败数</span>}
                value={overview?.failed || 0}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#ef4444' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card bordered={false} className="bg-slate-800">
              <Statistic
                title={<span className="text-slate-400">通过率</span>}
                value={overview?.pass_rate || 0}
                suffix="%"
                prefix={<PercentageOutlined />}
                valueStyle={{ color: '#f59e0b' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card bordered={false} className="bg-slate-800">
              <Statistic
                title={<span className="text-slate-400">平均分</span>}
                value={overview?.avg_score || 0}
                valueStyle={{ color: '#8b5cf6' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card bordered={false} className="bg-slate-800">
              <Statistic
                title={<span className="text-slate-400">平均重试</span>}
                value={overview?.avg_retry || 0}
                suffix="次"
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#ec4899' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 详细分析 Tabs */}
        <Card bordered={false} className="bg-slate-800">
          <Tabs items={tabItems} className="analytics-tabs" />
        </Card>
      </Spin>

      {/* 自定义样式 */}
      <style>{`
        .analytics-tabs .ant-tabs-tab {
          color: #94a3b8;
        }
        .analytics-tabs .ant-tabs-tab:hover {
          color: #e2e8f0;
        }
        .analytics-tabs .ant-tabs-tab-active .ant-tabs-tab-btn {
          color: #22d3ee !important;
        }
        .analytics-tabs .ant-tabs-ink-bar {
          background: #22d3ee;
        }
        .analytics-tabs .ant-tabs-nav::before {
          border-bottom-color: #334155;
        }
        .bg-slate-800.ant-card,
        .bg-slate-800 .ant-card-body {
          background: rgb(30 41 59) !important;
        }
        .bg-slate-800 .ant-statistic-title {
          color: #94a3b8;
        }
        .bg-slate-800 .ant-empty-description {
          color: #64748b;
        }
      `}</style>
    </div>
  );
};

export default AnalyticsPage;
