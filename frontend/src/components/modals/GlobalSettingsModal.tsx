import React, { useState, useEffect } from 'react';
import { Cpu, Scissors, Save, Server, Key, Plus, Sliders, Globe, Check, Crown, Info, Lock, Edit2, Trash2, Library, FileText, Copy, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import { message } from 'antd';
import { UserTier } from '../../types';
import api from '../../services/api';

interface GlobalSettingsModalProps {
  onClose: () => void;
  userTier: UserTier;
}

type SettingsTab = 'MODEL' | 'SKILL_LIB' | 'SPLIT' | 'PROMPTS';

const MODEL_RATES: Record<string, { in: number; out: number }> = {
  'DeepNarrative-Pro-v2 (Recommended)': { in: 10.00, out: 30.00 },
  'GPT-4o': { in: 5.00, out: 15.00 },
  'Claude 3.5 Sonnet': { in: 3.00, out: 15.00 },
  'Gemini-1.5-Pro': { in: 3.50, out: 10.50 },
  'Gemini-1.5-Flash': { in: 0.35, out: 1.05 },
  'Screenplay-Writer-v4': { in: 2.00, out: 6.00 },
};

const GlobalSettingsModal: React.FC<GlobalSettingsModalProps> = ({ onClose, userTier }) => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('MODEL');
  const isEnterprise = userTier === 'ENTERPRISE';
  const isStudioOrHigher = userTier === 'STUDIO' || userTier === 'ENTERPRISE';

  // Mock states for demonstration
  const [modelConfig, setModelConfig] = useState({
    reasoningModel: 'DeepNarrative-Pro-v2 (Recommended)',
    generationModel: 'Gemini-1.5-Pro',
    apiKey: 'sk-************************',
    temperature: 0.7,
    customModelName: '',
    customEndpoint: '',
    customApiKey: ''
  });

  const [skillLibs, setSkillLibs] = useState([
    { id: 1, name: '通用戏剧冲突库', type: 'system', description: '包含常见的36种戏剧冲突模式', enabled: true },
    { id: 2, name: '好莱坞节拍表', type: 'system', description: '布莱克·斯奈德的救猫咪节拍表', enabled: true },
    { id: 3, name: '我的悬疑模板', type: 'custom', description: '个人总结的悬疑反转技巧', enabled: true },
  ]);

  const [editingLib, setEditingLib] = useState<number | null>(null);

  // 提示词模板状态
  const [templates, setTemplates] = useState<any[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<any | null>(null);
  const [templateContent, setTemplateContent] = useState('');

  // 加载提示词模板
  useEffect(() => {
    if (activeTab === 'PROMPTS') {
      loadTemplates();
    }
  }, [activeTab]);

  const loadTemplates = async () => {
    setLoadingTemplates(true);
    try {
      const response = await api.get('/ai-resources', { params: { category: 'breakdown_prompt' } });
      setTemplates(response.data.items || response.data || []);
    } catch (error: unknown) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleCloneTemplate = async (template: any) => {
    try {
      await api.post(`/ai-resources/${template.id}/clone`);
      message.success('已复制，可以开始编辑');
      loadTemplates();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '复制失败');
    }
  };

  const handleEditTemplate = async (template: any) => {
    try {
      const response = await api.get(`/ai-resources/${template.id}`);
      setEditingTemplate(response.data);
      setTemplateContent(response.data.content || '');
    } catch (error: unknown) {
      message.error('加载模板失败');
    }
  };

  const handleSaveTemplate = async () => {
    if (!editingTemplate) return;
    try {
      await api.put(`/ai-resources/${editingTemplate.id}`, {
        ...editingTemplate,
        content: templateContent,
      });
      message.success('保存成功');
      setEditingTemplate(null);
      loadTemplates();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '保存失败');
    }
  };

  const handleDeleteTemplate = async (template: any) => {
    if (!confirm('确定要删除这个模板吗？')) return;
    try {
      await api.delete(`/ai-resources/${template.id}`);
      message.success('删除成功');
      loadTemplates();
    } catch (error: unknown) {
      message.error('删除失败');
    }
  };

  const toggleLib = (id: number) => {
    setSkillLibs(prev => prev.map(lib => lib.id === id ? { ...lib, enabled: !lib.enabled } : lib));
  };

  const deleteLib = (id: number) => {
      if (confirm('确定要删除这个技能库吗？')) {
          setSkillLibs(prev => prev.filter(lib => lib.id !== id));
      }
  };
  
  const handleAddLib = () => {
      if (!isStudioOrHigher) {
          alert('自定义技能库仅限工作室版及以上用户。');
          return;
      }
      const newLib = { id: Date.now(), name: '新技能库', type: 'custom', description: '描述...', enabled: true };
      setSkillLibs([...skillLibs, newLib]);
      setEditingLib(newLib.id);
  };

  const renderCostInfo = (modelName: string) => {
    const rate = MODEL_RATES[modelName];
    if (!rate) return null;
    return (
        <div className="flex items-center gap-4 text-xs mt-2 px-1 animate-in fade-in duration-300">
            <span className="text-slate-500 flex items-center gap-1.5">
                <Info size={10} />
                Input: <span className="text-slate-300 font-mono">${rate.in.toFixed(2)}</span> / 1M tokens
            </span>
            <span className="text-slate-500">
                Output: <span className="text-slate-300 font-mono">${rate.out.toFixed(2)}</span> / 1M tokens
            </span>
        </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative bg-slate-900 border border-slate-800 w-full max-w-4xl h-[600px] rounded-2xl shadow-2xl overflow-hidden flex"
      >
        {/* Sidebar Navigation */}
        <div className="w-64 bg-slate-900/50 border-r border-slate-800 p-4 flex flex-col gap-2">
          <div className="mb-6 px-2">
            <h2 className="text-lg font-bold text-white">全局设置</h2>
            <p className="text-xs text-slate-500">System Configuration</p>
          </div>
          
          <button 
            onClick={() => setActiveTab('MODEL')}
            className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === 'MODEL' 
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Cpu size={18} />
            模型配置
          </button>
          
          <button 
            onClick={() => setActiveTab('SKILL_LIB')}
            className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === 'SKILL_LIB' 
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Library size={18} />
            技能库配置
          </button>
          
          <button
            onClick={() => setActiveTab('SPLIT')}
            className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === 'SPLIT'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Scissors size={18} />
            拆分配置
          </button>

          <button
            onClick={() => setActiveTab('PROMPTS')}
            className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === 'PROMPTS'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <FileText size={18} />
            提示词模板
          </button>

          <div className="mt-auto pt-4 border-t border-slate-800">
             <button onClick={onClose} className="w-full py-2.5 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 text-sm transition-colors">
               取消 / 关闭
             </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col bg-slate-950/50">
          <div className="h-16 border-b border-slate-800 flex items-center justify-between px-8">
            <h3 className="text-lg font-medium text-white">
              {activeTab === 'MODEL' && '大模型与推理引擎'}
              {activeTab === 'SKILL_LIB' && '技能库 (Skill Libraries)'}
              {activeTab === 'SPLIT' && '智能文本拆分策略'}
              {activeTab === 'PROMPTS' && (editingTemplate ? '编辑提示词模板' : '提示词模板管理')}
            </h3>
            <button 
              className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm shadow-lg shadow-cyan-500/20 transition-all"
              onClick={onClose}
            >
              <Save size={16} />
              保存设置
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-8">
            
            {/* MODEL TAB */}
            {activeTab === 'MODEL' && (
              <div className="space-y-8 max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-cyan-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <Server size={14} /> 核心模型选择
                  </h4>
                  
                  <div className="space-y-2">
                    <label className="text-sm text-slate-300">推理模型 (Reasoning Agent)</label>
                    <p className="text-xs text-slate-500 mb-2">负责剧情拆解、逻辑检查和复杂任务规划。</p>
                    <select 
                      value={modelConfig.reasoningModel}
                      onChange={(e) => setModelConfig({...modelConfig, reasoningModel: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                    >
                      {Object.keys(MODEL_RATES).map(name => (
                         <option key={name} value={name}>{name}</option>
                      ))}
                      {modelConfig.customModelName && <option value="custom">{modelConfig.customModelName} (Custom)</option>}
                    </select>
                    {renderCostInfo(modelConfig.reasoningModel)}
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-slate-300">生成模型 (Creative Agent)</label>
                    <p className="text-xs text-slate-500 mb-2">负责具体剧本正文撰写、对白生成。</p>
                    <select 
                      value={modelConfig.generationModel}
                      onChange={(e) => setModelConfig({...modelConfig, generationModel: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                    >
                      {Object.keys(MODEL_RATES).map(name => (
                         <option key={name} value={name}>{name}</option>
                      ))}
                      {modelConfig.customModelName && <option value="custom">{modelConfig.customModelName} (Custom)</option>}
                    </select>
                    {renderCostInfo(modelConfig.generationModel)}
                  </div>
                </div>

                <div className="pt-6 border-t border-slate-800 space-y-4">
                   <h4 className="text-sm font-medium text-cyan-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <Key size={14} /> 接口鉴权
                  </h4>
                   <div className="space-y-2">
                    <label className="text-sm text-slate-300">Global API Key</label>
                    <input 
                      type="password"
                      value={modelConfig.apiKey}
                      onChange={(e) => setModelConfig({...modelConfig, apiKey: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-400 focus:ring-1 focus:ring-cyan-500 outline-none font-mono"
                    />
                  </div>
                   <div className="space-y-2">
                    <label className="text-sm text-slate-300">Temperature (Creativity)</label>
                    <div className="flex items-center gap-4">
                        <input 
                            type="range" 
                            min="0" max="1" step="0.1"
                            value={modelConfig.temperature}
                            onChange={(e) => setModelConfig({...modelConfig, temperature: parseFloat(e.target.value)})}
                            className="flex-1 h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                        />
                        <span className="text-sm font-mono text-cyan-400 w-8">{modelConfig.temperature}</span>
                    </div>
                  </div>
                </div>

                {/* Custom Model Config */}
                <div className="pt-6 border-t border-slate-800 space-y-4">
                    <div className="flex items-center justify-between mb-4">
                        <h4 className="text-sm font-medium text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                            <Globe size={14} /> 自定义模型 API
                        </h4>
                        {!isEnterprise && (
                             <div className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-bold border border-slate-700 flex items-center gap-1">
                                <Lock size={10} />
                                <span>企业版功能</span>
                            </div>
                        )}
                        {isEnterprise && (
                             <div className="px-2 py-0.5 rounded bg-amber-600/20 text-amber-500 text-[10px] font-bold border border-amber-600/30 flex items-center gap-1">
                                <Crown size={12} fill="currentColor" />
                                <span>已启用</span>
                            </div>
                        )}
                    </div>
                    
                    <div className={`p-1 rounded-xl transition-opacity ${!isEnterprise ? 'opacity-50 pointer-events-none' : ''}`}>
                        <div className="bg-slate-900/80 rounded-[11px] p-5 space-y-4 border border-slate-800 relative overflow-hidden">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-sm text-slate-300">模型名称 (Model Name)</label>
                                    <input 
                                        type="text"
                                        placeholder="e.g. Llama-3-70b-Groq"
                                        value={modelConfig.customModelName}
                                        onChange={(e) => setModelConfig({...modelConfig, customModelName: e.target.value})}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:ring-1 focus:ring-amber-500/50 outline-none transition-all placeholder:text-slate-600"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm text-slate-300">API Endpoint</label>
                                    <input 
                                        type="text"
                                        placeholder="https://api.example.com/v1"
                                        value={modelConfig.customEndpoint}
                                        onChange={(e) => setModelConfig({...modelConfig, customEndpoint: e.target.value})}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:ring-1 focus:ring-amber-500/50 outline-none font-mono transition-all placeholder:text-slate-600"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm text-slate-300">API Key (Optional override)</label>
                                <input 
                                    type="password"
                                    placeholder="sk-..."
                                    value={modelConfig.customApiKey}
                                    onChange={(e) => setModelConfig({...modelConfig, customApiKey: e.target.value})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-400 focus:ring-1 focus:ring-amber-500/50 outline-none font-mono transition-all placeholder:text-slate-600"
                                />
                                <p className="text-xs text-slate-500">此 Key 仅用于自定义模型请求。若留空则尝试使用全局 API Key。</p>
                            </div>
                        </div>
                    </div>
                </div>
              </div>
            )}

            {/* SKILL LIBRARY TAB */}
            {activeTab === 'SKILL_LIB' && (
              <div className="space-y-8 max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="flex justify-between items-end mb-4">
                    <div>
                        <h4 className="text-sm font-medium text-white">技能库管理</h4>
                        <p className="text-xs text-slate-500 mt-1">管理通用技能模板与个人经验库。</p>
                    </div>
                    <button 
                        onClick={handleAddLib}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                            isStudioOrHigher 
                            ? 'bg-cyan-600/10 border-cyan-500/50 text-cyan-400 hover:bg-cyan-600/20' 
                            : 'bg-slate-800 border-slate-700 text-slate-500 hover:text-slate-400 cursor-not-allowed'
                        }`}
                        title={!isStudioOrHigher ? "Requires Studio Plan or Higher" : ""}
                    >
                        {!isStudioOrHigher && <Lock size={10} className="text-amber-500" />}
                        <Plus size={12} /> 新增技能库
                    </button>
                </div>

                <div className="space-y-4">
                     <div className="space-y-3">
                        {skillLibs.map((lib) => (
                            <div key={lib.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 transition-all hover:border-slate-700">
                                {editingLib === lib.id ? (
                                    <div className="space-y-3">
                                        <div className="flex gap-2">
                                            <input 
                                                type="text" 
                                                value={lib.name}
                                                onChange={(e) => setSkillLibs(skillLibs.map(l => l.id === lib.id ? {...l, name: e.target.value} : l))}
                                                className="flex-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                                            />
                                            <button onClick={() => setEditingLib(null)} className="px-3 py-1 bg-cyan-600 text-white text-xs rounded">完成</button>
                                        </div>
                                        <input 
                                            type="text" 
                                            value={lib.description}
                                            onChange={(e) => setSkillLibs(skillLibs.map(l => l.id === lib.id ? {...l, description: e.target.value} : l))}
                                            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-300 focus:ring-1 focus:ring-cyan-500 outline-none"
                                        />
                                    </div>
                                ) : (
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-start gap-3">
                                            <div className={`mt-1 w-8 h-8 rounded flex items-center justify-center text-xs font-bold ${
                                                lib.type === 'system' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-cyan-500/10 text-cyan-400'
                                            }`}>
                                                {lib.type === 'system' ? 'SYS' : 'USR'}
                                            </div>
                                            <div>
                                                <h5 className="text-sm font-medium text-slate-200 flex items-center gap-2">
                                                    {lib.name}
                                                    {lib.type === 'system' && <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-[10px]">官方</span>}
                                                </h5>
                                                <p className="text-xs text-slate-500 mt-1">{lib.description}</p>
                                            </div>
                                        </div>
                                        
                                        <div className="flex items-center gap-2">
                                            <button 
                                                onClick={() => toggleLib(lib.id)}
                                                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                                                    lib.enabled ? 'bg-cyan-600' : 'bg-slate-700'
                                                }`}
                                            >
                                                <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${lib.enabled ? 'translate-x-4' : 'translate-x-0'}`} />
                                            </button>
                                            
                                            {lib.type === 'custom' && (
                                                <>
                                                    <button onClick={() => setEditingLib(lib.id)} className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded">
                                                        <Edit2 size={12} />
                                                    </button>
                                                    <button onClick={() => deleteLib(lib.id)} className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded">
                                                        <Trash2 size={12} />
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                     </div>
                </div>

                <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                    <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">How it works</h5>
                    <p className="text-xs text-slate-400 leading-relaxed">
                        启用技能库后，Agent 在执行任务时将自动检索库中相关的技巧模式（Patterns）。系统库由官方定期更新，包含行业标准的剧作理论；自定义库允许您沉淀个人的创作经验。
                    </p>
                </div>
              </div>
            )}

            {/* SPLIT TAB */}
            {activeTab === 'SPLIT' && (
              <div className="space-y-8 max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-cyan-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <Scissors size={14} /> 默认拆分策略
                  </h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     <div className="bg-cyan-900/20 border border-cyan-500/50 rounded-xl p-4 cursor-pointer relative">
                        <div className="absolute top-3 right-3 text-cyan-400"><Check size={16} /></div>
                        <h5 className="text-white font-medium mb-1">智能语义拆分</h5>
                        <p className="text-xs text-slate-400">AI 自动识别场景转换、时间跳跃点进行切分，保持剧情完整性。</p>
                     </div>
                     <div className="bg-slate-900 border border-slate-800 hover:border-slate-600 rounded-xl p-4 cursor-pointer">
                        <h5 className="text-slate-300 font-medium mb-1">按字数/Token 硬切分</h5>
                        <p className="text-xs text-slate-500">每 2000 字切分为一个处理单元，适合超长篇小说初步处理。</p>
                     </div>
                  </div>
                </div>

                <div className="space-y-4 pt-4 border-t border-slate-800">
                    <h4 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                        <Sliders size={14} /> 高级参数
                    </h4>
                    <div className="space-y-3">
                         <div className="flex items-center justify-between">
                             <span className="text-sm text-slate-400">上下文重叠 (Overlap)</span>
                             <span className="text-sm font-mono text-cyan-400">200 Tokens</span>
                         </div>
                         <div className="w-full bg-slate-800 rounded-full h-1.5">
                             <div className="bg-slate-600 h-1.5 rounded-full w-[10%]"></div>
                         </div>
                         <p className="text-xs text-slate-600">在每个切片前后保留上下文，防止关键信息在切分点丢失。</p>
                    </div>

                    <div className="space-y-2 mt-4">
                        <label className="text-sm text-slate-400">忽略模式 (Regex)</label>
                        <input 
                            type="text" 
                            defaultValue="^Copyright.*|^注：.*"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 font-mono focus:ring-1 focus:ring-cyan-500 outline-none"
                        />
                        <p className="text-xs text-slate-600">匹配到的行将在拆分前被自动过滤。</p>
                    </div>
                </div>
              </div>
            )}

            {/* PROMPTS TAB */}
            {activeTab === 'PROMPTS' && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
                {editingTemplate ? (
                  /* 编辑模式 */
                  <div className="space-y-4">
                    <button
                      onClick={() => setEditingTemplate(null)}
                      className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                      <ArrowLeft size={16} /> 返回列表
                    </button>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs text-slate-400 uppercase font-bold">显示名称</label>
                        <input
                          type="text"
                          value={editingTemplate.display_name}
                          onChange={(e) => setEditingTemplate({...editingTemplate, display_name: e.target.value})}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs text-slate-400 uppercase font-bold">描述</label>
                        <input
                          type="text"
                          value={editingTemplate.description || ''}
                          onChange={(e) => setEditingTemplate({...editingTemplate, description: e.target.value})}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-slate-400 uppercase font-bold">模板内容</label>
                        <span className="text-[10px] text-slate-500">可用变量: {'{{chapters_text}}'}</span>
                      </div>
                      <textarea
                        value={templateContent}
                        onChange={(e) => setTemplateContent(e.target.value)}
                        rows={12}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-300 font-mono focus:ring-1 focus:ring-cyan-500 outline-none resize-none"
                        placeholder="输入提示词内容..."
                      />
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                      <button
                        onClick={() => setEditingTemplate(null)}
                        className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                      >
                        取消
                      </button>
                      <button
                        onClick={handleSaveTemplate}
                        className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm flex items-center gap-2"
                      >
                        <Save size={14} /> 保存
                      </button>
                    </div>
                  </div>
                ) : (
                  /* 列表模式 */
                  <>
                    <div className="flex justify-between items-end">
                      <div>
                        <h4 className="text-sm font-medium text-white">拆解提示词模板</h4>
                        <p className="text-xs text-slate-500 mt-1">自定义剧情拆解各步骤的提示词</p>
                      </div>
                    </div>

                    {loadingTemplates ? (
                      <div className="text-center py-8 text-slate-500">加载中...</div>
                    ) : (
                      <div className="space-y-3">
                        {templates.map((template) => (
                          <div key={template.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-all">
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-3">
                                <div className={`mt-1 w-8 h-8 rounded flex items-center justify-center text-xs font-bold ${
                                  template.is_builtin ? 'bg-indigo-500/10 text-indigo-400' : 'bg-cyan-500/10 text-cyan-400'
                                }`}>
                                  <FileText size={14} />
                                </div>
                                <div>
                                  <h5 className="text-sm font-medium text-slate-200 flex items-center gap-2">
                                    {template.display_name}
                                    {template.is_builtin && <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-[10px]">系统</span>}
                                  </h5>
                                  <p className="text-xs text-slate-500 mt-1">{template.description}</p>
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                {template.is_builtin ? (
                                  <button
                                    onClick={() => handleCloneTemplate(template)}
                                    className="p-1.5 text-slate-500 hover:text-cyan-400 hover:bg-slate-800 rounded flex items-center gap-1"
                                    title="复制为我的模板"
                                  >
                                    <Copy size={12} />
                                  </button>
                                ) : (
                                  <>
                                    <button
                                      onClick={() => handleEditTemplate(template)}
                                      className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded"
                                      title="编辑"
                                    >
                                      <Edit2 size={12} />
                                    </button>
                                    <button
                                      onClick={() => handleDeleteTemplate(template)}
                                      className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded"
                                      title="删除"
                                    >
                                      <Trash2 size={12} />
                                    </button>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}

                        {templates.length === 0 && (
                          <div className="text-center py-8 text-slate-500">
                            暂无提示词模板
                          </div>
                        )}
                      </div>
                    )}

                    <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                      <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">使用说明</h5>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        系统内置提示词不可直接编辑，点击复制按钮创建自己的版本后即可自定义。在项目配置中可以选择使用哪个提示词版本。
                      </p>
                    </div>
                  </>
                )}
              </div>
            )}

          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default GlobalSettingsModal;
