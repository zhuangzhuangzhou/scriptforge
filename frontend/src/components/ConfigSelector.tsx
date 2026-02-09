import React, { useState, useEffect } from 'react';
import { Loader2, Info } from 'lucide-react';
import { GlassSelect } from './ui/GlassSelect';
import { breakdownApi } from '../services/api';
import { message, Select } from 'antd';

interface ConfigOption {
  key: string;
  description: string;
  is_custom: boolean;
}

interface ConfigSelectorProps {
  value?: {
    adaptMethodKey?: string;
    qualityRuleKey?: string;
    outputStyleKey?: string;
  };
  onChange?: (value: {
    adaptMethodKey: string;
    qualityRuleKey: string;
    outputStyleKey: string;
  }) => void;
  disabled?: boolean;
}

const ConfigSelector: React.FC<ConfigSelectorProps> = ({
  value = {},
  onChange,
  disabled = false
}) => {
  const [loading, setLoading] = useState(false);
  const [configs, setConfigs] = useState<{
    adapt_methods: ConfigOption[];
    quality_rules: ConfigOption[];
    output_styles: ConfigOption[];
  }>({
    adapt_methods: [],
    quality_rules: [],
    output_styles: []
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const response = await breakdownApi.getAvailableConfigs();
      if (response.data) {
        setConfigs(response.data);
      }
    } catch (error) {
      console.error('加载配置失败:', error);
      message.error('无法加载配置列表');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: 'adaptMethodKey' | 'qualityRuleKey' | 'outputStyleKey', val: string) => {
    const newValue = {
      adaptMethodKey: value.adaptMethodKey || 'adapt_method_default',
      qualityRuleKey: value.qualityRuleKey || 'qa_breakdown_default',
      outputStyleKey: value.outputStyleKey || 'output_style_default',
      [field]: val
    };
    onChange?.(newValue);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6 text-slate-500 gap-2">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-xs">加载配置...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 适配方法 */}
      <div>
        <label className="flex items-center gap-2 mb-2 text-xs text-slate-300">
          <span className="font-medium">适配方法 (Adapt Method)</span>
          <div className="group relative">
            <Info size={12} className="text-slate-500 cursor-help" />
            <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-slate-900 border border-slate-700 rounded-lg text-[10px] text-slate-400 z-50">
              决定如何提取冲突（⭐⭐⭐/⭐⭐/⭐）、识别情绪钩子、应用压缩策略
            </div>
          </div>
        </label>
        <GlassSelect
          value={value.adaptMethodKey || 'adapt_method_default'}
          onChange={(val) => handleChange('adaptMethodKey', val as string)}
          className="w-full"
          disabled={disabled}
          placeholder="选择适配方法"
        >
          {configs.adapt_methods.map((cfg) => (
            <Select.Option key={cfg.key} value={cfg.key}>
              <div className="flex flex-col">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-slate-200">{cfg.key}</span>
                  {cfg.is_custom ? (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                      自定义
                    </span>
                  ) : (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                      系统默认
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">
                  {cfg.description}
                </div>
              </div>
            </Select.Option>
          ))}
        </GlassSelect>
      </div>

      {/* 质检规则 */}
      <div>
        <label className="flex items-center gap-2 mb-2 text-xs text-slate-300">
          <span className="font-medium">质检规则 (Quality Rule)</span>
          <div className="group relative">
            <Info size={12} className="text-slate-500 cursor-help" />
            <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-slate-900 border border-slate-700 rounded-lg text-[10px] text-slate-400 z-50">
              8维度质量检查标准，决定拆解结果的通过阈值
            </div>
          </div>
        </label>
        <GlassSelect
          value={value.qualityRuleKey || 'qa_breakdown_default'}
          onChange={(val) => handleChange('qualityRuleKey', val as string)}
          className="w-full"
          disabled={disabled}
          placeholder="选择质检规则"
        >
          {configs.quality_rules.map((cfg) => (
            <Select.Option key={cfg.key} value={cfg.key}>
              <div className="flex flex-col">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-slate-200">{cfg.key}</span>
                  {cfg.is_custom ? (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                      自定义
                    </span>
                  ) : (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                      系统默认
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">
                  {cfg.description}
                </div>
              </div>
            </Select.Option>
          ))}
        </GlassSelect>
      </div>

      {/* 输出风格 */}
      <div>
        <label className="flex items-center gap-2 mb-2 text-xs text-slate-300">
          <span className="font-medium">输出风格 (Output Style)</span>
          <div className="group relative">
            <Info size={12} className="text-slate-500 cursor-help" />
            <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-slate-900 border border-slate-700 rounded-lg text-[10px] text-slate-400 z-50">
              剧本输出的风格规范（起承转钩、视觉化优先、快节奏无尿点）
            </div>
          </div>
        </label>
        <GlassSelect
          value={value.outputStyleKey || 'output_style_default'}
          onChange={(val) => handleChange('outputStyleKey', val as string)}
          className="w-full"
          disabled={disabled}
          placeholder="选择输出风格"
        >
          {configs.output_styles.map((cfg) => (
            <Select.Option key={cfg.key} value={cfg.key}>
              <div className="flex flex-col">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-slate-200">{cfg.key}</span>
                  {cfg.is_custom ? (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                      自定义
                    </span>
                  ) : (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                      系统默认
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">
                  {cfg.description}
                </div>
              </div>
            </Select.Option>
          ))}
        </GlassSelect>
      </div>
    </div>
  );
};

export default ConfigSelector;
