import React, { useState } from 'react';
import { X, Save, Cpu, Thermometer, Brain, Zap, Search, Database, Code, Info } from 'lucide-react';
import { motion } from 'framer-motion';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: string;
  model: string;
  desc: string;
  temperature?: number;
  systemPrompt?: string;
  tools?: string[];
}

interface AgentConfigModalProps {
  agent: Agent;
  onClose: () => void;
  onSave: (updatedAgent: Agent) => void;
}

const AgentConfigModal: React.FC<AgentConfigModalProps> = ({ agent, onClose, onSave }) => {
  const [formData, setFormData] = useState<Agent>({
    ...agent,
    temperature: agent.temperature || 0.7,
    systemPrompt: agent.systemPrompt || "You are a helpful AI assistant specialized in screenwriting...",
    tools: agent.tools || ['knowledge_base']
  });

  const toggleTool = (tool: string) => {
    setFormData(prev => ({
        ...prev,
        tools: prev.tools?.includes(tool) 
            ? prev.tools.filter(t => t !== tool)
            : [...(prev.tools || []), tool]
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative bg-slate-900 border border-slate-800 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/50">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 border border-cyan-500/20">
                    <Cpu size={20} />
                </div>
                <div>
                    <h2 className="text-lg font-bold text-white">配置智能体</h2>
                    <p className="text-xs text-slate-500">{agent.name} · {agent.role}</p>
                </div>
            </div>
            <button onClick={onClose} className="text-slate-500 hover:text-white"><X size={20} /></button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
            
            {/* Context Tip */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 flex items-start gap-3">
                <Info size={16} className="text-blue-400 shrink-0 mt-0.5" />
                <p className="text-xs text-blue-200 leading-relaxed">
                    这些参数将作为额外的上下文或指令传递给 Agent，直接影响其在工作流中的行为模式和输出质量。
                </p>
            </div>

            {/* Model & Parameters */}
            <div className="space-y-4">
                <h3 className="text-sm font-medium text-white flex items-center gap-2">
                    <Zap size={16} className="text-amber-400"/> 模型参数 (Model Parameters)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-xs text-slate-400">基座模型</label>
                        <select 
                            value={formData.model}
                            onChange={e => setFormData({...formData, model: e.target.value})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                        >
                            <option>DeepNarrative-Pro</option>
                            <option>Claude 3.5 Sonnet</option>
                            <option>GPT-4o</option>
                            <option>Gemini-1.5-Pro</option>
                        </select>
                    </div>
                     <div className="space-y-2">
                        <div className="flex justify-between">
                             <label className="text-xs text-slate-400 flex items-center gap-1"><Thermometer size={12}/> 温度 (Temperature)</label>
                             <span className="text-xs font-mono text-cyan-400">{formData.temperature}</span>
                        </div>
                        <input 
                            type="range" min="0" max="1" step="0.1"
                            value={formData.temperature}
                            onChange={e => setFormData({...formData, temperature: parseFloat(e.target.value)})}
                            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                        />
                    </div>
                </div>
            </div>

            {/* System Prompt */}
            <div className="space-y-3">
                 <h3 className="text-sm font-medium text-white flex items-center gap-2">
                    <Brain size={16} className="text-purple-400"/> 系统指令 (System Prompt)
                </h3>
                <div className="relative">
                    <textarea 
                        value={formData.systemPrompt}
                        onChange={e => setFormData({...formData, systemPrompt: e.target.value})}
                        className="w-full h-40 bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm font-mono text-slate-300 focus:ring-1 focus:ring-cyan-500 outline-none resize-none leading-relaxed"
                        placeholder="Define the agent's persona and core instructions..."
                    />
                </div>
            </div>

            {/* Tools */}
             <div className="space-y-3">
                 <h3 className="text-sm font-medium text-white flex items-center gap-2">
                    <Database size={16} className="text-green-400"/> 工具能力 (Capabilities)
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div 
                        onClick={() => toggleTool('knowledge_base')}
                        className={`p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-colors ${
                            formData.tools?.includes('knowledge_base') 
                            ? 'bg-blue-500/10 border-blue-500/50' 
                            : 'bg-slate-800 border-slate-700 hover:border-slate-600'
                        }`}
                    >
                         <div className={`p-1.5 rounded ${formData.tools?.includes('knowledge_base') ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-400'}`}><Database size={14}/></div>
                         <span className={`text-sm ${formData.tools?.includes('knowledge_base') ? 'text-blue-100' : 'text-slate-400'}`}>RAG 知识库检索</span>
                    </div>

                    <div 
                        onClick={() => toggleTool('web_search')}
                        className={`p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-colors ${
                            formData.tools?.includes('web_search') 
                            ? 'bg-blue-500/10 border-blue-500/50' 
                            : 'bg-slate-800 border-slate-700 hover:border-slate-600'
                        }`}
                    >
                         <div className={`p-1.5 rounded ${formData.tools?.includes('web_search') ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-400'}`}><Search size={14}/></div>
                         <span className={`text-sm ${formData.tools?.includes('web_search') ? 'text-blue-100' : 'text-slate-400'}`}>联网搜索</span>
                    </div>

                    <div 
                        onClick={() => toggleTool('code_interpreter')}
                        className={`p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-colors ${
                            formData.tools?.includes('code_interpreter') 
                            ? 'bg-blue-500/10 border-blue-500/50' 
                            : 'bg-slate-800 border-slate-700 hover:border-slate-600'
                        }`}
                    >
                         <div className={`p-1.5 rounded ${formData.tools?.includes('code_interpreter') ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-400'}`}><Code size={14}/></div>
                         <span className={`text-sm ${formData.tools?.includes('code_interpreter') ? 'text-blue-100' : 'text-slate-400'}`}>代码解释器</span>
                    </div>
                </div>
            </div>

        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3">
             <button onClick={onClose} className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">取消</button>
             <button 
                onClick={() => onSave(formData)}
                className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg flex items-center gap-2 shadow-lg shadow-cyan-500/20"
             >
                <Save size={16} /> 保存配置
             </button>
        </div>

      </motion.div>
    </div>
  );
};

export default AgentConfigModal;
