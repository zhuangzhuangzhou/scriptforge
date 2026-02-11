import React from 'react';
import { Button, Empty } from 'antd';
import { PlusOutlined, ArrowDownOutlined } from '@ant-design/icons';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { WorkflowStep, SkillInfo } from './types';
import StepNode from './StepNode';

interface WorkflowCanvasProps {
  steps: WorkflowStep[];
  selectedStepId: string | null;
  availableSkills: SkillInfo[];
  onStepsChange: (steps: WorkflowStep[]) => void;
  onSelectStep: (stepId: string | null) => void;
  onAddStep: () => void;
}

// 可排序的步骤项
const SortableStepItem: React.FC<{
  step: WorkflowStep;
  index: number;
  isSelected: boolean;
  skillInfo?: SkillInfo;
  onSelect: () => void;
  onDelete: () => void;
}> = ({ step, index, isSelected, skillInfo, onSelect, onDelete }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: step.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <StepNode
        step={step}
        index={index}
        isSelected={isSelected}
        skillInfo={skillInfo}
        onSelect={onSelect}
        onDelete={onDelete}
      />
    </div>
  );
};

const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  steps,
  selectedStepId,
  availableSkills,
  onStepsChange,
  onSelectStep,
  onAddStep,
}) => {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = steps.findIndex((s) => s.id === active.id);
      const newIndex = steps.findIndex((s) => s.id === over.id);
      onStepsChange(arrayMove(steps, oldIndex, newIndex));
    }
  };

  const handleDeleteStep = (stepId: string) => {
    onStepsChange(steps.filter((s) => s.id !== stepId));
    if (selectedStepId === stepId) {
      onSelectStep(null);
    }
  };

  const getSkillInfo = (skillName: string) => {
    return availableSkills.find((s) => s.name === skillName);
  };

  if (steps.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400">
        <Empty description="暂无步骤" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onAddStep}
          className="mt-4"
        >
          添加第一个步骤
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={steps.map((s) => s.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <SortableStepItem
                  step={step}
                  index={index}
                  isSelected={selectedStepId === step.id}
                  skillInfo={getSkillInfo(step.skill)}
                  onSelect={() => onSelectStep(step.id)}
                  onDelete={() => handleDeleteStep(step.id)}
                />
                {index < steps.length - 1 && (
                  <div className="flex justify-center py-1">
                    <ArrowDownOutlined className="text-slate-600" />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* 添加步骤按钮 */}
      <div className="mt-4 flex justify-center">
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={onAddStep}
          className="w-full max-w-xs"
        >
          添加步骤
        </Button>
      </div>
    </div>
  );
};

export default WorkflowCanvas;
