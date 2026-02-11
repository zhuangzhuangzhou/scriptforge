import React, { useState, useCallback, useMemo } from 'react';
import { Segmented, Select, InputNumber, Input, Button, Tooltip, message } from 'antd';
import { CodeOutlined, AppstoreOutlined, CopyOutlined } from '@ant-design/icons';
import MonacoEditor from '@monaco-editor/react';
import type { WorkflowConfig, WorkflowStep, SkillInfo } from './types';
import { createNewStep, parseWorkflowJson, stringifyWorkflow, validateWorkflow } from './utils';
import WorkflowCanvas from './WorkflowCanvas';
import StepConfigPanel from './StepConfigPanel';

export interface WorkflowEditorProps {
  value: WorkflowConfig;
  onChange: (value: WorkflowConfig) => void;
  availableSkills: SkillInfo[];
}

const WorkflowEditor: React.FC<WorkflowEditorProps> = ({
  value,
  onChange,
  availableSkills,
}) => {
  const [editorMode, setEditorMode] = useState<'visual' | 'json'>('visual');
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [jsonValue, setJsonValue] = useState(() => stringifyWorkflow(value));

  // 当前选中的步骤
  const selectedStep = useMemo(() => {
    if (!selectedStepId) return null;
    return value.steps.find((s) => s.id === selectedStepId) || null;
  }, [selectedStepId, value.steps]);

  // 所有步骤 ID（用于验证重复）
  const existingStepIds = useMemo(() => value.steps.map((s) => s.id), [value.steps]);

  // 切换编辑模式
  const handleModeChange = (mode: 'visual' | 'json') => {
    if (mode === 'json') {
      // 切换到 JSON 模式时，同步当前配置
      setJsonValue(stringifyWorkflow(value));
    } else {
      // 切换到可视化模式时，解析 JSON
      const parsed = parseWorkflowJson(jsonValue);
      if (parsed) {
        onChange(parsed);
        setSelectedStepId(null); // 重置选中状态
      } else {
        message.error('JSON 格式错误，无法切换到可视化模式');
        return;
      }
    }
    setEditorMode(mode);
  };

  // 更新工作流类型
  const handleTypeChange = (type: 'sequential' | 'loop') => {
    onChange({
      ...value,
      type,
      max_iterations: type === 'loop' ? (value.max_iterations || 3) : undefined,
      exit_condition: type === 'loop' ? (value.exit_condition || '') : undefined,
    });
  };

  // 更新步骤列表
  const handleStepsChange = useCallback((steps: WorkflowStep[]) => {
    onChange({ ...value, steps });
  }, [value, onChange]);

  // 添加新步骤
  const handleAddStep = useCallback(() => {
    const newStep = createNewStep(existingStepIds);
    onChange({ ...value, steps: [...value.steps, newStep] });
    setSelectedStepId(newStep.id);
  }, [value, existingStepIds, onChange]);

  // 当前选中步骤的索引（用于更新时定位）
  const selectedStepIndex = useMemo(() => {
    if (!selectedStepId) return -1;
    return value.steps.findIndex((s) => s.id === selectedStepId);
  }, [selectedStepId, value.steps]);

  // 更新单个步骤
  const handleStepChange = useCallback((updatedStep: WorkflowStep) => {
    if (selectedStepIndex === -1) return;

    const newSteps = [...value.steps];
    newSteps[selectedStepIndex] = updatedStep;

    // 如果 ID 变了，更新选中状态
    if (updatedStep.id !== selectedStepId) {
      setSelectedStepId(updatedStep.id);
    }
    onChange({ ...value, steps: newSteps });
  }, [value, selectedStepId, selectedStepIndex, onChange]);

  // JSON 编辑器变化
  const handleJsonChange = (newJson: string | undefined) => {
    setJsonValue(newJson || '{}');
    // 尝试解析并更新
    const parsed = parseWorkflowJson(newJson || '{}');
    if (parsed) {
      onChange(parsed);
    }
  };

  // 复制 JSON
  const handleCopyJson = () => {
    navigator.clipboard.writeText(stringifyWorkflow(value));
    message.success('已复制到剪贴板');
  };

  // 验证错误
  const errors = useMemo(() => validateWorkflow(value), [value]);

  return (
    <div className="h-full flex flex-col border border-slate-700 rounded-lg overflow-hidden bg-slate-900">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-800/50">
        <div className="flex items-center gap-4">
          {/* 工作流类型 */}
          <Select
            value={value.type}
            onChange={handleTypeChange}
            className="w-32"
            options={[
              { value: 'sequential', label: '顺序执行' },
              { value: 'loop', label: '循环执行' },
            ]}
          />

          {/* 循环参数（仅循环模式） */}
          {value.type === 'loop' && (
            <>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">最大迭代:</span>
                <InputNumber
                  value={value.max_iterations}
                  onChange={(v) => onChange({ ...value, max_iterations: v || 3 })}
                  min={1}
                  max={10}
                  size="small"
                  className="w-16"
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">退出条件:</span>
                <Input
                  value={value.exit_condition}
                  onChange={(e) => onChange({ ...value, exit_condition: e.target.value })}
                  placeholder="qa_result.status == 'PASS'"
                  size="small"
                  className="w-64"
                />
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* 复制 JSON */}
          <Tooltip title="复制 JSON">
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={handleCopyJson}
            />
          </Tooltip>

          {/* 编辑模式切换 */}
          <Segmented
            value={editorMode}
            onChange={(v) => handleModeChange(v as 'visual' | 'json')}
            options={[
              { value: 'visual', icon: <AppstoreOutlined />, label: '可视化' },
              { value: 'json', icon: <CodeOutlined />, label: 'JSON' },
            ]}
          />
        </div>
      </div>

      {/* 错误提示 */}
      {errors.length > 0 && editorMode === 'visual' && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/30">
          <div className="text-xs text-red-400">
            {errors.slice(0, 3).map((err, i) => (
              <div key={i}>• {err}</div>
            ))}
            {errors.length > 3 && <div>... 还有 {errors.length - 3} 个问题</div>}
          </div>
        </div>
      )}

      {/* 主内容区 */}
      <div className="flex-1 overflow-hidden">
        {editorMode === 'visual' ? (
          <div className="h-full flex">
            {/* 左侧：画布 */}
            <div className="flex-1 border-r border-slate-700">
              <WorkflowCanvas
                steps={value.steps}
                selectedStepId={selectedStepId}
                availableSkills={availableSkills}
                onStepsChange={handleStepsChange}
                onSelectStep={setSelectedStepId}
                onAddStep={handleAddStep}
              />
            </div>

            {/* 右侧：配置面板 */}
            <div className="w-80 bg-slate-800/30">
              <StepConfigPanel
                step={selectedStep}
                availableSkills={availableSkills}
                existingStepIds={existingStepIds}
                allSteps={value.steps}
                currentStepIndex={selectedStepIndex}
                onChange={handleStepChange}
              />
            </div>
          </div>
        ) : (
          <MonacoEditor
            height="100%"
            language="json"
            value={jsonValue}
            onChange={handleJsonChange}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        )}
      </div>
    </div>
  );
};

export default WorkflowEditor;
export type { WorkflowConfig, WorkflowStep, SkillInfo } from './types';
