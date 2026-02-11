// 工作流编辑器类型定义

// 工作流步骤
export interface WorkflowStep {
  id: string;
  skill: string;
  inputs: Record<string, string>;
  output_key: string;
  condition?: string;
  on_fail?: 'stop' | 'skip';
  max_retries?: number;
}

// 工作流配置
export interface WorkflowConfig {
  type: 'sequential' | 'loop';
  max_iterations?: number;
  exit_condition?: string;
  steps: WorkflowStep[];
}

// Skill 信息（用于选择器）
export interface SkillInfo {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  category: string;
  input_schema?: Record<string, InputSchemaField>;
  output_schema?: Record<string, unknown>;
}

// 输入字段 schema
export interface InputSchemaField {
  type: string;
  description?: string;
  default?: unknown;
}

// 编辑器 Props
export interface WorkflowEditorProps {
  value: WorkflowConfig;
  onChange: (value: WorkflowConfig) => void;
  availableSkills: SkillInfo[];
}

// 步骤节点 Props
export interface StepNodeProps {
  step: WorkflowStep;
  index: number;
  isSelected: boolean;
  skillInfo?: SkillInfo;
  onSelect: () => void;
  onDelete: () => void;
}

// 配置面板 Props
export interface StepConfigPanelProps {
  step: WorkflowStep | null;
  availableSkills: SkillInfo[];
  existingStepIds: string[];
  onChange: (step: WorkflowStep) => void;
}
