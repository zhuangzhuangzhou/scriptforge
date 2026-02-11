// 工作流编辑器工具函数

import type { WorkflowConfig, WorkflowStep } from './types';

// 默认工作流配置
export const createDefaultWorkflow = (): WorkflowConfig => ({
  type: 'sequential',
  steps: [],
});

// 创建新步骤
export const createNewStep = (existingIds: string[]): WorkflowStep => {
  let index = 1;
  let id = `step_${index}`;
  while (existingIds.includes(id)) {
    index++;
    id = `step_${index}`;
  }
  return {
    id,
    skill: '',
    inputs: {},
    output_key: '',
    on_fail: 'stop',
    max_retries: 1,
  };
};

// 验证工作流配置
export const validateWorkflow = (workflow: WorkflowConfig): string[] => {
  const errors: string[] = [];

  if (!workflow.steps || workflow.steps.length === 0) {
    errors.push('工作流至少需要一个步骤');
  }

  const stepIds = new Set<string>();
  workflow.steps.forEach((step, index) => {
    if (!step.id) {
      errors.push(`步骤 ${index + 1}: 缺少 ID`);
    } else if (stepIds.has(step.id)) {
      errors.push(`步骤 ${index + 1}: ID "${step.id}" 重复`);
    } else {
      stepIds.add(step.id);
    }

    if (!step.skill) {
      errors.push(`步骤 ${index + 1}: 未选择 Skill`);
    }

    if (!step.output_key) {
      errors.push(`步骤 ${index + 1}: 缺少输出键名`);
    }
  });

  if (workflow.type === 'loop') {
    if (!workflow.max_iterations || workflow.max_iterations < 1) {
      errors.push('循环模式需要设置最大迭代次数');
    }
    if (!workflow.exit_condition) {
      errors.push('循环模式需要设置退出条件');
    }
  }

  return errors;
};

// JSON 字符串转工作流配置
export const parseWorkflowJson = (json: string): WorkflowConfig | null => {
  try {
    const parsed = JSON.parse(json);
    return {
      type: parsed.type || 'sequential',
      max_iterations: parsed.max_iterations,
      exit_condition: parsed.exit_condition,
      steps: Array.isArray(parsed.steps) ? parsed.steps : [],
    };
  } catch {
    return null;
  }
};

// 工作流配置转 JSON 字符串
export const stringifyWorkflow = (workflow: WorkflowConfig): string => {
  const output: Record<string, unknown> = {
    type: workflow.type,
    steps: workflow.steps,
  };

  if (workflow.type === 'loop') {
    output.max_iterations = workflow.max_iterations;
    output.exit_condition = workflow.exit_condition;
  }

  return JSON.stringify(output, null, 2);
};

// 提取变量引用（用于自动补全提示）
export const extractVariableRefs = (steps: WorkflowStep[]): string[] => {
  const refs: string[] = ['${context.chapters_text}', '${context.adapt_method}'];

  steps.forEach((step) => {
    if (step.output_key) {
      refs.push(`\${${step.id}.${step.output_key}}`);
    }
  });

  return refs;
};

// 截断文本显示
export const truncateText = (text: string, maxLength: number = 30): string => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};
