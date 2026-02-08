import React from 'react';
import { BrainCircuit, Settings, Plus, Cpu } from 'lucide-react';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: string;
  model: string;
  desc: string;
  temperature: number;
  tools: string[];
}

interface AgentsTabProps {
  agents: Agent[];
  onSelectAgent: (agent: Agent) => void;
}

const SectionTitle = ({ title, description }: { title: string, description: string }) => (
  <div className="mb-6">
    <h2 className="text-xl font-bold text-white mb-1">{title}</h2>
    <p className="text-sm text-slate-400">{description}</p>
  </div>
);

const AgentsTab: React.FC<AgentsTabProps> = ({
  agents,
  onSelectAgent
}) => {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="flex justify-between items-start">
        <SectionTitle title="智能体编排 (Agent Orchestration)" description="配置负责不同任务的 AI 智能体。" />
        <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs transition-colors border border-slate-700">
          <Plus size={14} /> Add Agent
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents.map(agent => (
          <div key={agent.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-cyan-500/30 transition-all group shadow-lg">
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  agent.status === 'active' ? 'bg-cyan-900/20 text-cyan-400' : 'bg-slate-800 text-slate-500'
                }`}>
                  <BrainCircuit size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-white">{agent.name}</h4>
                  <span className="text-xs text-slate-500">{agent.role}</span>
                </div>
              </div>
              <button
                onClick={() => onSelectAgent(agent)}
                className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded transition-colors"
              >
                <Settings size={16} />
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-4 h-8 line-clamp-2">{agent.desc}</p>
            <div className="flex items-center gap-2 text-[10px] text-slate-500 bg-slate-950/50 p-2 rounded-lg">
              <Cpu size={12} /> Model: <span className="text-slate-300">{agent.model}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentsTab;
