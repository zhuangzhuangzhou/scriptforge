import React from 'react';
import { Sparkles, Plus } from 'lucide-react';

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

const SectionTitle = ({ title, description }: { title: string, description: string }) => (
  <div className="mb-6">
    <h2 className="text-xl font-bold text-white mb-1">{title}</h2>
    <p className="text-sm text-slate-400">{description}</p>
  </div>
);

const SkillsTab: React.FC<SkillsTabProps> = ({
  skills
}) => {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <SectionTitle title="技能库 (Skill Library)" description="为 Agent 挂载专业的编剧理论与技巧。" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {skills.map(skill => (
          <div key={skill.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-purple-500/30 transition-all shadow-lg">
            <div className="flex items-center gap-2 mb-2 text-purple-400">
              <Sparkles size={16} />
              <h4 className="font-semibold text-white">{skill.name}</h4>
            </div>
            <p className="text-xs text-slate-400 mb-3">{skill.desc}</p>
            <div className="text-[10px] text-slate-500 border-t border-slate-800 pt-2 flex justify-between">
              <span>Trigger: {skill.trigger}</span>
              <span className="text-green-400">Enabled</span>
            </div>
          </div>
        ))}
        <button className="border border-dashed border-slate-700 rounded-xl p-5 flex flex-col items-center justify-center text-slate-500 hover:text-white hover:border-slate-500 transition-colors gap-2 shadow-inner">
          <Plus size={24} />
          <span className="text-xs">Add Custom Skill</span>
        </button>
      </div>
    </div>
  );
};

export default SkillsTab;
