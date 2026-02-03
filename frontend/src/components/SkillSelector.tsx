import React, { useState, useEffect } from 'react';
import { Card, Checkbox, Button, Collapse, Input, message } from 'antd';
import { SettingOutlined } from '@ant-design/icons';

const { Panel } = Collapse;

interface Skill {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  parameters: any;
}

interface SkillSelectorProps {
  category: string;
  projectId?: string;
  onSkillsChange?: (selectedSkills: string[]) => void;
}

const SkillSelector: React.FC<SkillSelectorProps> = ({
  category,
  projectId,
  onSkillsChange
}) => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSkills();
  }, [category]);

  const loadSkills = async () => {
    try {
      const response = await fetch(
        `/api/v1/skills/available?category=${category}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      if (!response.ok) throw new Error('加载Skills失败');
      const data = await response.json();
      setSkills(data.skills);
    } catch (error) {
      message.error('加载Skills失败');
    }
  };

  return (
    <Card title="选择Skills" className="mb-4">
      <div className="space-y-2">
        {skills.map(skill => (
          <div key={skill.id} className="border rounded p-3">
            <Checkbox
              checked={selectedSkills.includes(skill.id)}
              onChange={(e) => {
                const newSelected = e.target.checked
                  ? [...selectedSkills, skill.id]
                  : selectedSkills.filter(id => id !== skill.id);
                setSelectedSkills(newSelected);
                onSkillsChange?.(newSelected);
              }}
            >
              <strong>{skill.display_name}</strong>
            </Checkbox>
            <p className="text-sm text-gray-500 ml-6">{skill.description}</p>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default SkillSelector;
