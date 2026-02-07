import React, { useEffect, useState } from 'react';
import { Sparkles, BrainCircuit, Check, Loader2 } from 'lucide-react';
import { skillsApi } from '../services/api';
import { Skill } from '../types';
import { message } from 'antd';

interface SkillSelectorProps {
    category: 'breakdown' | 'script';
    selectedSkillIds: string[];
    onChange: (skillIds: string[]) => void;
    disabled?: boolean;
}

const SkillSelector: React.FC<SkillSelectorProps> = ({ category, selectedSkillIds, onChange, disabled }) => {
    const [skills, setSkills] = useState<Skill[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadSkills();
    }, [category]);

    const loadSkills = async () => {
        setLoading(true);
        try {
            const res = await skillsApi.getAvailableSkills(category);
            if (res.data && res.data.skills) {
                setSkills(res.data.skills);
            }
        } catch (err) {
            console.error('加载技能失败:', err);
            message.error('无法加载技能列表');
        } finally {
            setLoading(false);
        }
    };

    const toggleSkill = (id: string) => {
        if (disabled) return;
        if (selectedSkillIds.includes(id)) {
            onChange(selectedSkillIds.filter(sid => sid !== id));
        } else {
            onChange([...selectedSkillIds, id]);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-6 text-slate-500 gap-2">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-xs">加载技能库...</span>
            </div>
        );
    }

    if (!skills || skills.length === 0) {
        return (
            <div className="text-center p-4 text-slate-500 bg-slate-900/50 rounded-lg border border-slate-800 text-xs">
                暂无可用技能
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
            {skills.map(skill => {
                const isSelected = selectedSkillIds.includes(skill.id);
                return (
                    <div
                        key={skill.id}
                        onClick={() => toggleSkill(skill.id)}
                        className={`
                            relative flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer group select-none
                            ${isSelected
                                ? 'bg-cyan-500/10 border-cyan-500/50 shadow-[0_0_15px_-3px_rgba(6,182,212,0.15)]'
                                : 'bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-800/60'
                            }
                            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                        `}
                    >
                        {/* Checkbox Indicator */}
                        <div className={`
                            w-4 h-4 mt-0.5 rounded flex items-center justify-center border transition-all shrink-0
                            ${isSelected
                                ? 'bg-cyan-500 border-cyan-500 text-white'
                                : 'bg-slate-950 border-slate-700 group-hover:border-slate-500'
                            }
                        `}>
                            {isSelected && <Check size={10} strokeWidth={4} />}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                                <span className={`text-xs font-bold ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                                    {skill.display_name}
                                </span>
                                {skill.is_template_based && (
                                    <span className="text-[9px] px-1 py-0 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 leading-none">
                                        T
                                    </span>
                                )}
                            </div>
                            <p className="text-[10px] text-slate-500 leading-tight line-clamp-2">
                                {skill.description || '暂无描述'}
                            </p>
                        </div>

                        {/* Type Icon */}
                         <div className={`
                            shrink-0 text-slate-600 group-hover:text-slate-500 transition-colors
                        `}>
                            {skill.is_builtin ? <Sparkles size={14} /> : <BrainCircuit size={14} />}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default SkillSelector;