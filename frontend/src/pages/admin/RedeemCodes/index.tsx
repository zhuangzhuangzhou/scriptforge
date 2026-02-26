import React, { useState, useEffect } from 'react';
import { Gift, Plus, Copy, Trash2, Eye, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react';
import { message, Tooltip, Tag, Popconfirm } from 'antd';
import { GlassTable } from '../../../components/ui/GlassTable';
import { GlassModal } from '../../../components/ui/GlassModal';
import { redeemApi } from '../../../services/api';
import { TIER_NAMES } from '../../../constants/tier';

interface RedeemCode {
  id: string;
  code: string;
  type: 'credits' | 'tier_upgrade';
  credits: number;
  tier: string | null;
  tier_days: number;
  max_uses: number;
  used_count: number;
  is_active: boolean;
  expires_at: string | null;
  note: string | null;
  created_at: string;
}

const RedeemCodesPage: React.FC = () => {
  const [codes, setCodes] = useState<RedeemCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('');

  // 创建弹窗状态
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({
    type: 'credits' as 'credits' | 'tier_upgrade',
    credits: 500,
    tier: 'CREATOR',
    tier_days: 30,
    max_uses: 1,
    count: 1,
    note: '',
    code: '',
  });

  // 详情弹窗
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedCode, setSelectedCode] = useState<any>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const pageSize = 20;

  const fetchCodes = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: pageSize };
      if (typeFilter) params.type = typeFilter;
      if (activeFilter !== '') params.is_active = activeFilter === 'true';

      const response = await redeemApi.admin.list(params);
      setCodes(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      message.error('获取兑换码列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCodes();
  }, [page, typeFilter, activeFilter]);

  const handleCreate = async () => {
    if (createForm.type === 'credits' && createForm.credits <= 0) {
      message.warning('请设置积分数量');
      return;
    }

    setCreating(true);
    try {
      const response = await redeemApi.admin.create({
        type: createForm.type,
        credits: createForm.type === 'credits' ? createForm.credits : undefined,
        tier: createForm.type === 'tier_upgrade' ? createForm.tier : undefined,
        tier_days: createForm.tier_days,
        max_uses: createForm.max_uses,
        count: createForm.count,
        note: createForm.note || undefined,
        code: createForm.code || undefined,
      });

      message.success(`成功创建 ${response.data.count} 个兑换码`);
      setCreateModalOpen(false);
      setCreateForm({
        type: 'credits',
        credits: 500,
        tier: 'CREATOR',
        tier_days: 30,
        max_uses: 1,
        count: 1,
        note: '',
        code: '',
      });
      fetchCodes();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const handleToggleActive = async (code: RedeemCode) => {
    try {
      await redeemApi.admin.update(code.id, { is_active: !code.is_active });
      message.success(code.is_active ? '已停用' : '已启用');
      fetchCodes();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDelete = async (code: RedeemCode) => {
    try {
      await redeemApi.admin.delete(code.id);
      message.success('删除成功');
      fetchCodes();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  const handleViewDetail = async (code: RedeemCode) => {
    setSelectedCode(null);
    setDetailModalOpen(true);
    setLoadingDetail(true);
    try {
      const response = await redeemApi.admin.get(code.id);
      setSelectedCode(response.data);
    } catch (error) {
      message.error('获取详情失败');
      setDetailModalOpen(false);
    } finally {
      setLoadingDetail(false);
    }
  };

  const copyCode = (codeStr: string) => {
    navigator.clipboard.writeText(codeStr);
    message.success('已复制到剪贴板');
  };

  // GlassTable 列定义
  const columns = [
    {
      title: '兑换码',
      dataIndex: 'code',
      key: 'code',
      width: 180,
      render: (code: string) => (
        <div className="flex items-center gap-2">
          <code className="font-mono text-sm text-cyan-400 bg-slate-800 px-2 py-1 rounded">
            {code}
          </code>
          <button
            onClick={() => copyCode(code)}
            className="text-slate-500 hover:text-white transition-colors"
          >
            <Copy size={14} />
          </button>
        </div>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 80,
      render: (type: string) => (
        <Tag color={type === 'credits' ? 'green' : 'purple'}>
          {type === 'credits' ? '积分' : '升级'}
        </Tag>
      ),
    },
    {
      title: '内容',
      key: 'content',
      width: 150,
      render: (_: any, record: RedeemCode) => (
        record.type === 'credits' ? (
          <span className="text-emerald-400 font-medium">+{record.credits.toLocaleString()} 积分</span>
        ) : (
          <span className="text-purple-400 font-medium">{TIER_NAMES[record.tier || ''] || record.tier}</span>
        )
      ),
    },
    {
      title: '使用情况',
      key: 'usage',
      width: 100,
      render: (_: any, record: RedeemCode) => (
        <span className={record.used_count >= record.max_uses && record.max_uses > 0 ? 'text-red-400' : 'text-slate-300'}>
          {record.used_count} / {record.max_uses === 0 ? '∞' : record.max_uses}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (is_active: boolean) => (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
          is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'
        }`}>
          {is_active ? '启用' : '停用'}
        </span>
      ),
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 120,
      render: (expires_at: string | null) => (
        <span className="text-slate-400">
          {expires_at ? new Date(expires_at).toLocaleDateString() : '永不过期'}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right' as const,
      render: (_: any, record: RedeemCode) => (
        <div className="flex items-center justify-end gap-2">
          <Tooltip title="查看详情">
            <button
              onClick={() => handleViewDetail(record)}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
            >
              <Eye size={16} />
            </button>
          </Tooltip>
          <Tooltip title={record.is_active ? '停用' : '启用'}>
            <button
              onClick={() => handleToggleActive(record)}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
            >
              {record.is_active ? <ToggleRight size={16} className="text-emerald-400" /> : <ToggleLeft size={16} />}
            </button>
          </Tooltip>
          {record.used_count === 0 && (
            <Popconfirm
              title="确定删除此兑换码？"
              onConfirm={() => handleDelete(record)}
              okText="删除"
              cancelText="取消"
            >
              <button className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded transition-colors">
                <Trash2 size={16} />
              </button>
            </Popconfirm>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center">
              <Gift className="text-emerald-400" size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">兑换码管理</h1>
              <p className="text-sm text-slate-400">创建和管理兑换码</p>
            </div>
          </div>

          <button
            onClick={() => setCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors"
          >
            <Plus size={18} />
            创建兑换码
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-4">
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">全部类型</option>
            <option value="credits">积分充值</option>
            <option value="tier_upgrade">等级升级</option>
          </select>

          <select
            value={activeFilter}
            onChange={(e) => { setActiveFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">全部状态</option>
            <option value="true">已启用</option>
            <option value="false">已停用</option>
          </select>

          <div className="text-sm text-slate-400">
            共 {total} 条记录
          </div>
        </div>

        {/* Table */}
        <GlassTable
          dataSource={codes}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: (p) => setPage(p),
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条`,
          }}
          scroll={{ x: 900 }}
          locale={{ emptyText: '暂无兑换码' }}
        />
      </div>

      {/* Create Modal */}
      <GlassModal
        title="创建兑换码"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
        width={480}
      >
        <div className="space-y-4 py-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">兑换类型</label>
            <select
              value={createForm.type}
              onChange={(e) => setCreateForm({ ...createForm, type: e.target.value as any })}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="credits">积分充值</option>
              <option value="tier_upgrade">等级升级</option>
            </select>
          </div>

          {createForm.type === 'credits' ? (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">积分数量</label>
              <input
                type="number"
                value={createForm.credits}
                onChange={(e) => setCreateForm({ ...createForm, credits: parseInt(e.target.value) || 0 })}
                min={1}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">升级到等级</label>
              <select
                value={createForm.tier}
                onChange={(e) => setCreateForm({ ...createForm, tier: e.target.value })}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="CREATOR">创作者版</option>
                <option value="STUDIO">工作室版</option>
                <option value="ENTERPRISE">企业版</option>
              </select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">最大使用次数</label>
              <input
                type="number"
                value={createForm.max_uses}
                onChange={(e) => setCreateForm({ ...createForm, max_uses: parseInt(e.target.value) || 0 })}
                min={0}
                placeholder="0 = 无限"
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              />
              <p className="text-xs text-slate-500 mt-1">0 表示无限制</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">批量生成数量</label>
              <input
                type="number"
                value={createForm.count}
                onChange={(e) => setCreateForm({ ...createForm, count: Math.min(100, Math.max(1, parseInt(e.target.value) || 1)) })}
                min={1}
                max={100}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">自定义兑换码（可选）</label>
            <input
              type="text"
              value={createForm.code}
              onChange={(e) => setCreateForm({ ...createForm, code: e.target.value.toUpperCase() })}
              placeholder="留空自动生成"
              maxLength={32}
              disabled={createForm.count > 1}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500 disabled:opacity-50 font-mono uppercase"
            />
            {createForm.count > 1 && (
              <p className="text-xs text-slate-500 mt-1">批量生成时不支持自定义兑换码</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">备注（可选）</label>
            <input
              type="text"
              value={createForm.note}
              onChange={(e) => setCreateForm({ ...createForm, note: e.target.value })}
              placeholder="例如：活动赠送、VIP 客户"
              maxLength={200}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>
      </GlassModal>

      {/* Detail Modal */}
      <GlassModal
        title="兑换码详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={600}
      >
        {loadingDetail ? (
          <div className="py-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-slate-400 mx-auto" />
          </div>
        ) : selectedCode && (
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl">
              <code className="font-mono text-xl text-cyan-400">{selectedCode.code}</code>
              <button
                onClick={() => copyCode(selectedCode.code)}
                className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
              >
                <Copy size={14} />
                复制
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-slate-500 mb-1">类型</div>
                <div className="text-white">{selectedCode.type === 'credits' ? '积分充值' : '等级升级'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">内容</div>
                <div className="text-white">
                  {selectedCode.type === 'credits' ? `+${selectedCode.credits} 积分` : TIER_NAMES[selectedCode.tier] || selectedCode.tier}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">使用情况</div>
                <div className="text-white">{selectedCode.used_count} / {selectedCode.max_uses === 0 ? '∞' : selectedCode.max_uses}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">状态</div>
                <div className={selectedCode.is_active ? 'text-emerald-400' : 'text-slate-400'}>
                  {selectedCode.is_active ? '启用中' : '已停用'}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">过期时间</div>
                <div className="text-white">{selectedCode.expires_at ? new Date(selectedCode.expires_at).toLocaleString() : '永不过期'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">创建时间</div>
                <div className="text-white">{new Date(selectedCode.created_at).toLocaleString()}</div>
              </div>
            </div>

            {selectedCode.note && (
              <div>
                <div className="text-xs text-slate-500 mb-1">备注</div>
                <div className="text-slate-300">{selectedCode.note}</div>
              </div>
            )}

            {selectedCode.records && selectedCode.records.length > 0 && (
              <div>
                <div className="text-sm font-medium text-white mb-2">使用记录</div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedCode.records.map((record: any) => (
                    <div key={record.id} className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg text-sm">
                      <div>
                        <span className="text-white">{record.username}</span>
                        {record.credits_granted > 0 && (
                          <span className="text-emerald-400 ml-2">+{record.credits_granted} 积分</span>
                        )}
                        {record.tier_after && record.tier_after !== record.tier_before && (
                          <span className="text-purple-400 ml-2">{record.tier_before} → {record.tier_after}</span>
                        )}
                      </div>
                      <div className="text-slate-500">{new Date(record.created_at).toLocaleString()}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </GlassModal>
    </div>
  );
};

export default RedeemCodesPage;
