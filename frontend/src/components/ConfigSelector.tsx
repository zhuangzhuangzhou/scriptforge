import React, { useState, useEffect } from 'react';
import { Loader2, Settings } from 'lucide-react';
import api from '../services/api';
import { message, Checkbox, Collapse, Tag, Button } from 'antd';
import { useNavigate } from 'react-router-dom';

interface AIResource {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  is_builtin: boolean;
  is_active: boolean;
}

interface ConfigSelectorProps {
  value?: string[];  // 选中的资源 ID 列表
  onChange?: (value: string[]) => void;
  disabled?: boolean;
  showManageLink?: boolean;
}

const categoryConfig: Record<string, { label: string; color: string; description: string }> = {
  methodology: {
    label: '方法论',
    color: 'blue',
    description: '改编方法论，决定如何提取冲突、识别情绪钩子、应用压缩策略',
  },
  output_style: {
    label: '输出风格',
    color: 'purple',
    description: '剧本输出的风格规范（起承转钩、视觉化优先、快节奏无尿点）',
  },
  qa_rules: {
    label: '质检标准',
    color: 'orange',
    description: '质量检查标准，决定拆解结果的通过阈值',
  },
  template: {
    label: '模板案例',
    color: 'cyan',
    description: '输出格式模板和参考示例',
  },
};

const ConfigSelector: React.FC<ConfigSelectorProps> = ({
  value = [],
  onChange,
  disabled = false,
  showManageLink = true,
}) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [resourcesByCategory, setResourcesByCategory] = useState<Record<string, AIResource[]>>({});

  useEffect(() => {
    loadResources();
  }, []);

  const loadResources = async () => {
    setLoading(true);
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

      // 如果没有选中任何模板，自动选中每个分类的第一个内置模板
      if (value.length === 0) {
        const defaultIds: string[] = [];
        for (const category of Object.keys(grouped)) {
          const builtinResource = grouped[category].find((r) => r.is_builtin);
          if (builtinResource) {
            defaultIds.push(builtinResource.id);
          }
        }
        if (defaultIds.length > 0) {
          onChange?.(defaultIds);
        }
      }
    } catch (error) {
      console.error('加载资源失败:', error);
      message.error('无法加载配置列表');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (resourceId: string, checked: boolean) => {
    if (checked) {
      onChange?.([...value, resourceId]);
    } else {
      onChange?.(value.filter((id) => id !== resourceId));
    }
  };

  const handleSelectAll = (category: string, checked: boolean) => {
    const categoryResources = resourcesByCategory[category] || [];
    const categoryIds = categoryResources.map((r) => r.id);

    if (checked) {
      // 添加该分类所有资源
      const newValue = [...new Set([...value, ...categoryIds])];
      onChange?.(newValue);
    } else {
      // 移除该分类所有资源
      onChange?.(value.filter((id) => !categoryIds.includes(id)));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6 text-slate-500 gap-2">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-xs">加载配置...</span>
      </div>
    );
  }

  const categories = Object.keys(categoryConfig).filter(
    (cat) => resourcesByCategory[cat]?.length > 0
  );

  return (
    <div className="config-selector">
      {/* 管理入口 */}
      {showManageLink && (
        <div className="flex justify-between items-center mb-3">
          <span className="text-xs text-slate-400">
            已选择 {value.length} 个模板
          </span>
          <Button
            type="link"
            size="small"
            icon={<Settings size={12} />}
            onClick={() => navigate('/user/templates')}
            className="text-xs text-slate-400 hover:text-cyan-400"
          >
            管理模板
          </Button>
        </div>
      )}

      <Collapse
        defaultActiveKey={categories}
        ghost
        className="config-collapse"
        items={categories.map((category) => {
          const config = categoryConfig[category];
          const resources = resourcesByCategory[category] || [];
          const selectedInCategory = resources.filter((r) => value.includes(r.id));
          const allSelected = selectedInCategory.length === resources.length;
          const someSelected = selectedInCategory.length > 0 && !allSelected;

          return {
            key: category,
            label: (
              <div className="flex items-center justify-between w-full pr-2">
                <div className="flex items-center gap-2">
                  <Tag color={config.color} className="m-0">
                    {config.label}
                  </Tag>
                  <span className="text-[10px] text-slate-500">
                    {config.description}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400">
                  {selectedInCategory.length}/{resources.length}
                </span>
              </div>
            ),
            children: (
              <div className="pl-2">
                {/* 全选 */}
                <div className="mb-2 pb-2 border-b border-slate-800">
                  <Checkbox
                    checked={allSelected}
                    indeterminate={someSelected}
                    onChange={(e) => handleSelectAll(category, e.target.checked)}
                    disabled={disabled}
                  >
                    <span className="text-xs text-slate-400">全选</span>
                  </Checkbox>
                </div>

                {/* 资源列表 */}
                <div className="space-y-2">
                  {resources.map((resource) => (
                    <div
                      key={resource.id}
                      className="flex items-start gap-2 p-2 rounded-lg hover:bg-slate-800/50 transition-colors"
                    >
                      <Checkbox
                        checked={value.includes(resource.id)}
                        onChange={(e) => handleToggle(resource.id, e.target.checked)}
                        disabled={disabled}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-200 font-medium">
                            {resource.display_name}
                          </span>
                          {resource.is_builtin ? (
                            <span className="text-[9px] px-1 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                              系统
                            </span>
                          ) : (
                            <span className="text-[9px] px-1 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                              我的
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">
                          {resource.description}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ),
          };
        })}
      />
    </div>
  );
};

export default ConfigSelector;
