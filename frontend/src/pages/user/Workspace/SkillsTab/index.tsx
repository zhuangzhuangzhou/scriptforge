import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Sparkles, Loader2, Eye, Check, BookOpen, Palette, Shield, FileText, HelpCircle, Compass } from 'lucide-react';
import { GlassTabs } from '../../../../components/ui/GlassTabs';
import { GlassModal } from '../../../../components/ui/GlassModal';
import api from '../../../../services/api';
import { message } from 'antd';

interface AIResource {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  content?: string;
  is_builtin: boolean;
  is_active: boolean;
}

interface CategoryConfig {
  key: string;
  label: string;
  icon: string;
  color: string;
  description: string;
  order: number;
  default_select_all: boolean;
}

interface SkillsTabProps {
  skills?: unknown[];
}

const STORAGE_KEY = 'breakdown_config';

interface BreakdownConfig {
  selectedResourceIds: string[];
  savedAt: string;
}

// 图标映射
const iconMap: Record<string, React.ReactNode> = {
  BookOpen: <BookOpen size={16} />,
  Compass: <Compass size={16} />,
  Palette: <Palette size={16} />,
  Shield: <Shield size={16} />,
  FileText: <FileText size={16} />,
};

// 颜色映射
const colorMap: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  blue: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-400',
    glow: 'shadow-blue-500/20',
  },
  emerald: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    glow: 'shadow-emerald-500/20',
  },
  purple: {
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    text: 'text-purple-400',
    glow: 'shadow-purple-500/20',
  },
  orange: {
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    text: 'text-orange-400',
    glow: 'shadow-orange-500/20',
  },
  cyan: {
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/30',
    text: 'text-cyan-400',
    glow: 'shadow-cyan-500/20',
  },
};

// 资源卡片组件
interface ResourceCardProps {
  resource: AIResource;
  isSelected: boolean;
  color: string;
  onSelect: () => void;
  onViewDetail: () => void;
}

const ResourceCard: React.FC<ResourceCardProps> = ({
  resource,
  isSelected,
  color,
  onSelect,
  onViewDetail,
}) => {
  const colors = colorMap[color] || colorMap.cyan;

  return (
    <div
      onClick={onSelect}
      className={`
        relative group p-4 rounded-xl border transition-all duration-300 cursor-pointer
        ${isSelected
          ? `${colors.bg} ${colors.border} shadow-lg ${colors.glow}`
          : 'bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-800/60'
        }
      `}
    >
      {/* 选中指示器 */}
      <div className={`
        absolute top-3 left-3 w-5 h-5 rounded-md flex items-center justify-center border transition-all
        ${isSelected
          ? `${colors.bg} ${colors.border} ${colors.text}`
          : 'bg-slate-950 border-slate-700 group-hover:border-slate-500'
        }
      `}>
        {isSelected && <Check size={12} strokeWidth={3} />}
      </div>

      {/* 详情按钮 */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onViewDetail();
        }}
        className={`
          absolute top-3 right-3 w-7 h-7 rounded-lg flex items-center justify-center
          bg-slate-800/80 border border-slate-700 text-slate-400
          hover:bg-slate-700 hover:text-white hover:border-slate-600
          transition-all opacity-0 group-hover:opacity-100
        `}
        title="查看详情"
      >
        <Eye size={14} />
      </button>

      {/* 卡片内容 */}
      <div className="pt-6">
        <div className="flex items-center gap-2 mb-2">
          <h4 className={`font-semibold text-sm ${isSelected ? 'text-white' : 'text-slate-300'}`}>
            {resource.display_name}
          </h4>
          {resource.is_builtin ? (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              系统
            </span>
          ) : (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
              自定义
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
          {resource.description || '暂无描述'}
        </p>
      </div>
    </div>
  );
};

// 详情弹窗组件
interface DetailModalProps {
  open: boolean;
  resource: AIResource | null;
  color: string;
  categoryConfig: CategoryConfig | null;
  onClose: () => void;
}

const DetailModal: React.FC<DetailModalProps> = ({ open, resource, color, categoryConfig, onClose }) => {
  const colors = colorMap[color] || colorMap.cyan;

  return (
    <GlassModal
      open={open}
      onCancel={onClose}
      footer={null}
      width={600}
      title={
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text}`}>
            {categoryConfig ? iconMap[categoryConfig.icon] || <HelpCircle size={16} /> : <Sparkles size={16} />}
          </div>
          <span>{resource?.display_name || '详情'}</span>
        </div>
      }
    >
      {resource && (
        <div className="space-y-4">
          {/* 基本信息 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-1 rounded ${colors.bg} ${colors.text} ${colors.border} border`}>
              {categoryConfig?.label || resource.category}
            </span>
            {resource.is_builtin ? (
              <span className="text-xs px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                系统内置
              </span>
            ) : (
              <span className="text-xs px-2 py-1 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                自定义
              </span>
            )}
          </div>

          {/* 描述 */}
          <div>
            <h4 className="text-xs font-semibold text-slate-400 mb-2">描述</h4>
            <p className="text-sm text-slate-300 leading-relaxed">
              {resource.description || '暂无描述'}
            </p>
          </div>

          {/* 内容预览 */}
          {resource.content && (
            <div>
              <h4 className="text-xs font-semibold text-slate-400 mb-2">内容预览</h4>
              <div className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 max-h-[300px] overflow-y-auto">
                <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                  {resource.content}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </GlassModal>
  );
};

// 自定义事件：通知父组件保存状态变化
const SAVE_STATUS_EVENT = 'skillsTabSaveStatus';

const SkillsTab: React.FC<SkillsTabProps> = () => {
  const [categories, setCategories] = useState<CategoryConfig[]>([]);
  const [activeTab, setActiveTab] = useState<string>('methodology'); // 预设置默认值，避免初始渲染闪烁
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [resourcesByCategory, setResourcesByCategory] = useState<Record<string, AIResource[]>>({});
  const [loading, setLoading] = useState(true);
  const [detailModal, setDetailModal] = useState<{ open: boolean; resource: AIResource | null }>({
    open: false,
    resource: null,
  });
  const [hasChanges, setHasChanges] = useState(false);
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const categoriesLoadedRef = useRef(false);

  // 加载分类配置
  const loadCategories = useCallback(async () => {
    try {
      const response = await api.get('/ai-resources/categories');
      const cats: CategoryConfig[] = response.data.categories || [];
      setCategories(cats);
      // 检查预设置的默认 Tab 是否存在于返回的分类中
      const hasDefaultTab = cats.some(cat => cat.key === 'methodology');
      if (cats.length > 0 && !hasDefaultTab) {
        setActiveTab(cats[0].key);
      }
      // 如果后端返回了 methodology，就使用预设置的 activeTab
      categoriesLoadedRef.current = true;
    } catch (error) {
      console.error('加载分类失败:', error);
      // 使用默认分类作为回退
      const defaultCategories: CategoryConfig[] = [
        { key: 'methodology', label: '方法论', icon: 'BookOpen', color: 'blue', description: '改编方法论', order: 1, default_select_all: true },
        { key: 'output_style', label: '输出风格', icon: 'Palette', color: 'purple', description: '输出风格规范', order: 2, default_select_all: false },
        { key: 'qa_rules', label: '质检标准', icon: 'Shield', color: 'orange', description: '质量检查标准', order: 3, default_select_all: false },
        { key: 'template', label: '模板案例', icon: 'FileText', color: 'cyan', description: '输出格式模板', order: 4, default_select_all: false },
      ];
      setCategories(defaultCategories);
      // 保持预设置的 activeTab
      categoriesLoadedRef.current = true;
    }
  }, []);

  // 加载资源
  const loadResources = useCallback(async () => {
    try {
      const response = await api.get('/ai-resources', {
        params: { page_size: 100 },
      });
      const items: AIResource[] = response.data.items || response.data;

      // 按分类分组
      const grouped: Record<string, AIResource[]> = {};
      for (const item of items) {
        if (!item.is_active) continue;
        if (!grouped[item.category]) {
          grouped[item.category] = [];
        }
        grouped[item.category].push(item);
      }

      setResourcesByCategory(grouped);
    } catch (error) {
      console.error('加载资源失败:', error);
      message.error('无法加载配置列表');
    } finally {
      // loading 初始值就是 true，API 完成后设为 false
      setLoading(false);
    }
  }, []);

  // 加载保存的配置
  const loadSavedConfig = useCallback(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const config: BreakdownConfig = JSON.parse(saved);
        // 兼容旧格式
        if (config.selectedResourceIds) {
          setSelectedIds(config.selectedResourceIds);
        } else if ((config as unknown as { breakdownConfig?: string[] }).breakdownConfig) {
          setSelectedIds((config as unknown as { breakdownConfig: string[] }).breakdownConfig);
        }
      }
    } catch (err) {
      console.error('加载配置失败:', err);
    }
  }, []);

  useEffect(() => {
    loadCategories();
    loadResources();
    loadSavedConfig();
  }, [loadCategories, loadResources, loadSavedConfig]);

  // 自动选择默认配置（根据分类配置的 default_select_all 决定）
  useEffect(() => {
    if (!loading && selectedIds.length === 0 && Object.keys(resourcesByCategory).length > 0 && categories.length > 0) {
      const defaultIds: string[] = [];
      for (const cat of categories) {
        const resources = resourcesByCategory[cat.key] || [];
        if (cat.default_select_all) {
          // 全选该分类
          defaultIds.push(...resources.map((r) => r.id));
        } else {
          // 选第一个内置
          const builtinResource = resources.find((r) => r.is_builtin);
          if (builtinResource) {
            defaultIds.push(builtinResource.id);
          }
        }
      }
      if (defaultIds.length > 0) {
        setSelectedIds(defaultIds);
      }
    }
  }, [loading, resourcesByCategory, selectedIds.length, categories]);

  // 自动保存功能（防抖）
  useEffect(() => {
    if (!hasChanges) return;

    // 清除之前的定时器
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    // 通知父组件正在保存
    window.dispatchEvent(new CustomEvent(SAVE_STATUS_EVENT, { detail: { saving: true } }));

    // 延迟 800ms 后自动保存
    autoSaveTimerRef.current = setTimeout(() => {
      const config: BreakdownConfig = {
        selectedResourceIds: selectedIds,
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));

      // 触发配置保存事件
      window.dispatchEvent(new CustomEvent('breakdownConfigSaved', { detail: config }));

      // 通知父组件保存完成
      window.dispatchEvent(new CustomEvent(SAVE_STATUS_EVENT, { detail: { saving: false, savedAt: new Date() } }));

      setHasChanges(false);
    }, 800);

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [selectedIds, hasChanges]);

  // 切换选中状态
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
    setHasChanges(true);
  };

  // 手动保存配置（供父组件调用）
  const handleSave = useCallback(() => {
    const config: BreakdownConfig = {
      selectedResourceIds: selectedIds,
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));

    // 触发配置保存事件
    window.dispatchEvent(new CustomEvent('breakdownConfigSaved', { detail: config }));

    // 通知父组件保存完成
    window.dispatchEvent(new CustomEvent(SAVE_STATUS_EVENT, { detail: { saving: false, savedAt: new Date() } }));

    setHasChanges(false);
  }, [selectedIds]);

  // 暴露保存方法给父组件
  useEffect(() => {
    const handleManualSave = () => {
      handleSave();
    };
    window.addEventListener('skillsTabManualSave', handleManualSave);
    return () => {
      window.removeEventListener('skillsTabManualSave', handleManualSave);
    };
  }, [handleSave]);

  // 查看详情
  const handleViewDetail = (resource: AIResource) => {
    setDetailModal({ open: true, resource });
  };

  // 获取当前分类的选中数量
  const getSelectedCount = (category: string) => {
    const resources = resourcesByCategory[category] || [];
    return resources.filter((r) => selectedIds.includes(r.id)).length;
  };

  // 骨架屏组件
  const SkeletonCard = () => (
    <div className="h-28 bg-slate-800/40 rounded-xl border border-slate-700/50 animate-pulse" />
  );

  // 获取分类配置的辅助函数
  const getCategoryConfig = (key: string): CategoryConfig | undefined => {
    return categories.find((c) => c.key === key);
  };

  // 构建 Tab 项
  const tabItems = categories
    .filter((cat) => resourcesByCategory[cat.key]?.length > 0)
    .map((cat) => {
      const count = getSelectedCount(cat.key);
      const total = resourcesByCategory[cat.key]?.length || 0;
      return {
        key: cat.key,
        label: (
          <div className="flex items-center gap-2">
            {iconMap[cat.icon] || <HelpCircle size={16} />}
            <span>{cat.label}</span>
            {count > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
                {count}/{total}
              </span>
            )}
          </div>
        ),
      };
    });

  const currentConfig = getCategoryConfig(activeTab);
  const currentResources = resourcesByCategory[activeTab] || [];

  return (
    <div className="h-full overflow-y-auto px-4 md:px-6 pt-2 pb-4">
      {/* 顶部标题栏 - 紧凑布局 */}
      <div className="flex items-center justify-between gap-4 mb-4 sticky top-0 bg-slate-950/95 backdrop-blur-md z-10 py-2">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-cyan-500/20 border border-purple-500/30 flex items-center justify-center">
            <Sparkles size={16} className="text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">技能库</h2>
            <p className="text-xs text-slate-500">为 Agent 挂载专业的编剧理论与技巧</p>
          </div>
        </div>
        {/* 右上角选中数量 */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all ${
          selectedIds.length > 0
            ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
            : 'bg-slate-800/50 border-slate-700 text-slate-500'
        }`}>
          <div className={`w-2 h-2 rounded-full ${selectedIds.length > 0 ? 'bg-cyan-400 shadow-lg shadow-cyan-400/50' : 'bg-slate-600'}`} />
          <span className="text-xs font-medium">
            已选择 <span className="font-bold">{selectedIds.length}</span> 项配置
          </span>
        </div>
      </div>

      {/* Tab 切换 */}
      <div className="mb-4">
        <GlassTabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </div>

      {/* 分类描述 */}
      {currentConfig && (
        <div className={`mb-4 p-3 rounded-xl ${colorMap[currentConfig.color]?.bg} border ${colorMap[currentConfig.color]?.border}`}>
          <div className="flex items-center gap-2">
            <span className={colorMap[currentConfig.color]?.text}>{iconMap[currentConfig.icon] || <HelpCircle size={16} />}</span>
            <span className={`text-sm font-medium ${colorMap[currentConfig.color]?.text}`}>
              {currentConfig.label}
            </span>
            <span className="text-xs text-slate-500">—</span>
            <p className="text-xs text-slate-400">
              {currentConfig.description}
            </p>
          </div>
        </div>
      )}

      {/* 卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {loading ? (
          // 加载中显示骨架屏
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : currentResources.length > 0 ? (
          // 有数据时显示卡片
          currentResources.map((resource) => (
            <ResourceCard
              key={resource.id}
              resource={resource}
              isSelected={selectedIds.includes(resource.id)}
              color={currentConfig?.color || 'cyan'}
              onSelect={() => toggleSelect(resource.id)}
              onViewDetail={() => handleViewDetail(resource)}
            />
          ))
        ) : (
          // 无数据时显示空状态
          <div className="col-span-full text-center py-12 text-slate-500">
            <Sparkles size={32} className="mx-auto mb-3 opacity-50" />
            <p>暂无可用的{currentConfig?.label || '配置'}</p>
          </div>
        )}
      </div>

      {/* 详情弹窗 */}
      <DetailModal
        open={detailModal.open}
        resource={detailModal.resource}
        color={detailModal.resource ? getCategoryConfig(detailModal.resource.category)?.color || 'cyan' : 'cyan'}
        categoryConfig={detailModal.resource ? getCategoryConfig(detailModal.resource.category) || null : null}
        onClose={() => setDetailModal({ open: false, resource: null })}
      />
    </div>
  );
};

export default SkillsTab;
