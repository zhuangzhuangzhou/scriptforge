import React from 'react';
import { Select, Empty } from 'antd';
import type { SkillInfo } from './types';

interface SkillSelectorProps {
  value?: string;
  onChange: (value: string) => void;
  skills: SkillInfo[];
  placeholder?: string;
}

const SkillSelector: React.FC<SkillSelectorProps> = ({
  value,
  onChange,
  skills,
  placeholder = '选择 Skill',
}) => {
  // 按分类分组
  const groupedSkills = skills.reduce((acc, skill) => {
    const category = skill.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(skill);
    return acc;
  }, {} as Record<string, SkillInfo[]>);

  const categoryLabels: Record<string, string> = {
    breakdown: '剧情拆解',
    script: '剧本创作',
    qa: '质量检查',
    analysis: '分析',
    other: '其他',
  };

  if (skills.length === 0) {
    return (
      <Select
        value={value}
        placeholder={placeholder}
        disabled
        notFoundContent={<Empty description="暂无可用 Skill" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
        className="w-full"
      />
    );
  }

  return (
    <Select
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className="w-full"
      showSearch
      optionFilterProp="label"
      notFoundContent={<Empty description="未找到匹配的 Skill" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
    >
      {Object.entries(groupedSkills).map(([category, categorySkills]) => (
        <Select.OptGroup key={category} label={categoryLabels[category] || category}>
          {categorySkills.map((skill) => (
            <Select.Option key={skill.name} value={skill.name} label={skill.display_name}>
              <div>
                <div className="font-medium">{skill.display_name}</div>
                {skill.description && (
                  <div className="text-xs text-slate-400 truncate">{skill.description}</div>
                )}
              </div>
            </Select.Option>
          ))}
        </Select.OptGroup>
      ))}
    </Select>
  );
};

export default SkillSelector;
