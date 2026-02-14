import React, { useState, useEffect } from 'react';
import { Sparkles, Plus, Save, Loader2, Settings, Zap } from 'lucide-react';
import SkillSelector from '../../../../components/SkillSelector';
import ConfigSelector from '../../../../components/ConfigSelector';

interface Skill {
  id: string;
  name: string;
  trigger: string;
  desc: string;
  prompt: string;
}

interface SkillsTabProps {
  skills: Skill[];
}

const STORAGE_KEY = 'breakdown_config';

interface BreakdownConfig {
  selectedBreakdownSkills: string[];
  breakdownConfig: string[];
  savedAt: string;
}

// 毛玻璃卡片组件
const GlassCard: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = ''
}) => (
  <div className={`bg-slate-900/60 backdrop-blur-xl border border-slate-800/60 rounded-2xl shadow-xl ${className}`}>
    {children}
  </div>
);

const SkillsTab: React.FC<SkillsTabProps> = ({
  skills
}) => {
  const [selectedBreakdownSkills, setSelectedBreakdownSkills] = useState<string[]>([]);
  const [breakdownConfig, setBreakdownConfig] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  // 加载保存的配置
  useEffect(() => {
    const loadConfig = () => {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const config: BreakdownConfig = JSON.parse(saved);
          setSelectedBreakdownSkills(config.selectedBreakdownSkills || []);
          setBreakdownConfig(config.breakdownConfig || []);
        }
      } catch (err) {
        console.error('加载配置失败:', err);
      } finally {
        setLoading(false);
      }
    };

    loadConfig();
  }, []);

  // 保存配置
  const handleSave = async () => {
    setSaving(true);
    try {
      const config: BreakdownConfig = {
        selectedBreakdownSkills,
        breakdownConfig,
        savedAt: new Date().toISOString()
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));

      // 模拟保存延迟
      await new Promise(resolve => setTimeout(resolve, 500));

      // 触发自定义事件
      window.dispatchEvent(new CustomEvent('breakdownConfigSaved', { detail: config }));

      console.log('[SkillsTab] 配置已保存:', config);
    } catch (err) {
      console.error('保存配置失败:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 gap-2">
        <Loader2 size={20} className="animate-spin" />
        <span>加载配置...</span>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto animate-in fade-in slide-in-from-bottom-4 duration-300 p-4 md:p-6">
      {/* 顶部标题栏 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 sticky top-0 bg-slate-950/95 backdrop-blur-md z-10 py-4 border-b border-slate-800/50">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-cyan-500/20 border border-purple-500/30 flex items-center justify-center">
              <Sparkles size={20} className="text-purple-400" />
            </div>
            技能库
          </h2>
          <p className="text-slate-400 mt-1 ml-1">为 Agent 挂载专业的编剧理论与技巧</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save size={16} />
              保存配置
            </>
          )}
        </button>
      </div>

      <div className="space-y-6">
        {/* 拆解任务配置卡片 */}
        <GlassCard className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center">
              <Zap size={20} className="text-amber-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">拆解任务配置</h3>
              <p className="text-xs text-slate-400">选择技能和方法论来自定义拆解流程</p>
            </div>
          </div>

          {/* AI 技能选择 */}
          <div className="space-y-4">
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <Sparkles size={18} className="text-blue-400" />
                </div>
                <div>
                  <span className="font-bold block text-blue-200 mb-1">AI 技能选择</span>
                  <p className="text-xs text-blue-300 leading-relaxed">
                    不同的技能组合会影响拆解的维度和消耗的 Token。建议根据小说类型选择合适的技能。
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-slate-950/50 rounded-xl border border-slate-800/50">
              <SkillSelector
                category="breakdown"
                selectedSkillIds={selectedBreakdownSkills}
                onChange={setSelectedBreakdownSkills}
              />
            </div>
          </div>

          {/* 分割线 */}
          <div className="my-6 border-t border-slate-800/50" />

          {/* 改编方法与质检规则 */}
          <div className="space-y-4">
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <Settings size={18} className="text-purple-400" />
                </div>
                <div>
                  <span className="font-bold block text-purple-200 mb-1">改编方法与质检规则</span>
                  <p className="text-xs text-purple-300 leading-relaxed">
                    选择适配方法（冲突提取标准）、质检规则（8维度评分）和输出风格（起承转钩）。
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-slate-950/50 rounded-xl border border-slate-800/50">
              <ConfigSelector
                value={breakdownConfig}
                onChange={setBreakdownConfig}
              />
            </div>
          </div>

          {/* 配置状态提示 */}
          <div className="mt-4 pt-4 border-t border-slate-800/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${selectedBreakdownSkills.length > 0 || breakdownConfig.length > 0 ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-slate-600'}`} />
                <span className="text-xs text-slate-400">
                  {selectedBreakdownSkills.length > 0 || breakdownConfig.length > 0
                    ? `已选择 ${selectedBreakdownSkills.length} 个技能，${breakdownConfig.length} 项配置`
                    : '使用系统默认配置'}
                </span>
              </div>
              <span className="text-xs text-slate-600">
                {selectedBreakdownSkills.length > 0 || breakdownConfig.length > 0
                  ? `最后保存: ${new Date().toLocaleTimeString()}`
                  : ''}
              </span>
            </div>
          </div>
        </GlassCard>

        {/* 已挂载技能卡片 */}
        <GlassCard className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30 flex items-center justify-center">
              <Sparkles size={20} className="text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">已挂载技能</h3>
              <p className="text-xs text-slate-400">当前项目可用的 AI 技能列表</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {skills.map(skill => (
              <div
                key={skill.id}
                className="group bg-slate-950/30 border border-slate-800/50 rounded-xl p-4 hover:border-purple-500/40 hover:bg-slate-900/50 transition-all duration-300 cursor-pointer"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-cyan-500/20 border border-purple-500/30 flex items-center justify-center">
                      <Sparkles size={14} className="text-purple-400" />
                    </div>
                    <h4 className="font-semibold text-white group-hover:text-purple-300 transition-colors">{skill.name}</h4>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                    Enabled
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-3 line-clamp-2 group-hover:text-slate-300 transition-colors">{skill.desc}</p>
                <div className="flex items-center justify-between pt-3 border-t border-slate-800/50">
                  <span className="text-[10px] text-slate-500">
                    <span className="text-slate-600">Trigger:</span> {skill.trigger}
                  </span>
                </div>
              </div>
            ))}

            {/* 添加自定义技能按钮 */}
            <button className="group border-2 border-dashed border-slate-700 rounded-xl p-4 flex flex-col items-center justify-center gap-3 text-slate-500 hover:text-slate-300 hover:border-slate-600 hover:bg-slate-900/30 transition-all duration-300 min-h-[120px]">
              <div className="w-10 h-10 rounded-xl bg-slate-800/50 group-hover:bg-slate-800 flex items-center justify-center transition-colors">
                <Plus size={24} />
              </div>
              <span className="text-sm font-medium">添加自定义技能</span>
            </button>
          </div>
        </GlassCard>
      </div>
    </div>
  );
};

export default SkillsTab;
