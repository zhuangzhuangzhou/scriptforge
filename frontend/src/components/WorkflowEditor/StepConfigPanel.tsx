import React, { useMemo } from 'react';
import { Form, Input, Select, InputNumber, Button, Divider, Empty, AutoComplete } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { StepConfigPanelProps, WorkflowStep } from './types';
import SkillSelector from './SkillSelector';
import { extractVariableRefs } from './utils';

const StepConfigPanel: React.FC<StepConfigPanelProps & { allSteps: WorkflowStep[]; currentStepIndex: number }> = ({
  step,
  availableSkills,
  existingStepIds,
  allSteps,
  currentStepIndex,
  onChange,
}) => {
  // 获取当前选中 Skill 的信息
  const selectedSkill = useMemo(() => {
    if (!step?.skill) return null;
    return availableSkills.find((s) => s.name === step.skill);
  }, [step?.skill, availableSkills]);

  // 可用的变量引用（只包含当前步骤之前的步骤）
  const variableRefs = useMemo(() => {
    const previousSteps = currentStepIndex > 0 ? allSteps.slice(0, currentStepIndex) : [];
    return extractVariableRefs(previousSteps);
  }, [allSteps, currentStepIndex]);

  // 根据 Skill 的 input_schema 生成输入字段
  const inputFields = useMemo(() => {
    if (!step) return [];
    if (selectedSkill?.input_schema) {
      return Object.entries(selectedSkill.input_schema).map(([key, schema]) => ({
        key,
        description: schema.description || key,
        type: schema.type,
      }));
    }
    // 如果没有 schema，使用当前 inputs 的 keys
    return Object.keys(step.inputs).map((key) => ({
      key,
      description: key,
      type: 'string',
    }));
  }, [selectedSkill, step]);

  if (!step) {
    return (
      <div className="h-full flex items-center justify-center">
        <Empty description="选择一个步骤进行编辑" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  const handleChange = (field: keyof WorkflowStep, value: unknown) => {
    onChange({ ...step, [field]: value });
  };

  const handleInputChange = (key: string, value: string) => {
    onChange({
      ...step,
      inputs: { ...step.inputs, [key]: value },
    });
  };

  const handleRemoveInput = (key: string) => {
    const newInputs = { ...step.inputs };
    delete newInputs[key];
    onChange({ ...step, inputs: newInputs });
  };

  const handleAddInput = () => {
    const existingKeys = Object.keys(step.inputs);
    let index = 1;
    let newKey = `param_${index}`;
    while (existingKeys.includes(newKey)) {
      index++;
      newKey = `param_${index}`;
    }
    onChange({
      ...step,
      inputs: { ...step.inputs, [newKey]: '' },
    });
  };

  // 当 Skill 变化时，自动填充 input_schema 的字段
  const handleSkillChange = (skillName: string) => {
    const skill = availableSkills.find((s) => s.name === skillName);
    const newInputs: Record<string, string> = {};

    if (skill?.input_schema) {
      Object.keys(skill.input_schema).forEach((key) => {
        newInputs[key] = step.inputs[key] || '';
      });
    }

    onChange({
      ...step,
      skill: skillName,
      inputs: newInputs,
      output_key: step.output_key || skillName.replace(/_/g, '_') + '_result',
    });
  };

  return (
    <div className="h-full overflow-y-auto p-4">
      <h3 className="text-lg font-medium text-slate-200 mb-4">步骤配置</h3>

      <Form layout="vertical" size="small">
        {/* 步骤 ID */}
        <Form.Item
          label="步骤 ID"
          required
          validateStatus={existingStepIds.filter((id) => id === step.id).length > 1 ? 'error' : ''}
          help={existingStepIds.filter((id) => id === step.id).length > 1 ? 'ID 重复' : ''}
        >
          <Input
            value={step.id}
            onChange={(e) => handleChange('id', e.target.value)}
            placeholder="唯一标识，如 breakdown"
          />
        </Form.Item>

        {/* Skill 选择 */}
        <Form.Item label="Skill" required>
          <SkillSelector
            value={step.skill}
            onChange={handleSkillChange}
            skills={availableSkills}
          />
          {selectedSkill?.description && (
            <div className="text-xs text-slate-500 mt-1">{selectedSkill.description}</div>
          )}
        </Form.Item>

        <Divider className="my-3 border-slate-700" />

        {/* 输入参数 */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-300">输入参数</span>
            {!selectedSkill?.input_schema && (
              <Button
                type="text"
                size="small"
                icon={<PlusOutlined />}
                onClick={handleAddInput}
              >
                添加
              </Button>
            )}
          </div>

          {inputFields.length === 0 ? (
            <div className="text-xs text-slate-500">请先选择 Skill</div>
          ) : (
            <div className="space-y-2">
              {inputFields.map(({ key, description }) => (
                <div key={key}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-slate-400">{key}</span>
                    {description !== key && (
                      <span className="text-xs text-slate-600">({description})</span>
                    )}
                    {!selectedSkill?.input_schema && (
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleRemoveInput(key)}
                        className="ml-auto"
                      />
                    )}
                  </div>
                  <AutoComplete
                    value={step.inputs[key] || ''}
                    onChange={(value) => handleInputChange(key, value)}
                    options={variableRefs.map((ref) => ({ value: ref }))}
                    placeholder="输入值或变量引用 ${...}"
                    className="w-full"
                    filterOption={(input, option) =>
                      option?.value.toLowerCase().includes(input.toLowerCase()) ?? false
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        <Divider className="my-3 border-slate-700" />

        {/* 输出键名 */}
        <Form.Item label="输出键名" required>
          <Input
            value={step.output_key}
            onChange={(e) => handleChange('output_key', e.target.value)}
            placeholder="结果存储的键名"
          />
        </Form.Item>

        {/* 条件表达式 */}
        <Form.Item label="条件表达式" extra="可选，满足条件时才执行此步骤">
          <Input
            value={step.condition || ''}
            onChange={(e) => handleChange('condition', e.target.value || undefined)}
            placeholder="如: qa_result.status == 'FAIL'"
          />
        </Form.Item>

        {/* 失败策略 */}
        <Form.Item label="失败策略">
          <Select
            value={step.on_fail || 'stop'}
            onChange={(value) => handleChange('on_fail', value)}
          >
            <Select.Option value="stop">停止执行</Select.Option>
            <Select.Option value="skip">跳过继续</Select.Option>
          </Select>
        </Form.Item>

        {/* 最大重试次数 */}
        <Form.Item label="最大重试次数">
          <InputNumber
            value={step.max_retries || 1}
            onChange={(value) => handleChange('max_retries', value)}
            min={1}
            max={5}
            className="w-full"
          />
        </Form.Item>
      </Form>
    </div>
  );
};

export default StepConfigPanel;
