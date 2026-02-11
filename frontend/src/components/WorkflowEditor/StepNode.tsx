import React from 'react';
import { Card, Tag, Button, Tooltip } from 'antd';
import { DeleteOutlined, HolderOutlined, WarningOutlined } from '@ant-design/icons';
import type { StepNodeProps } from './types';

const StepNode: React.FC<StepNodeProps> = ({
  step,
  index,
  isSelected,
  skillInfo,
  onSelect,
  onDelete,
}) => {
  const inputKeys = Object.keys(step.inputs);
  const hasCondition = !!step.condition;
  const isSkipOnFail = step.on_fail === 'skip';

  return (
    <Card
      size="small"
      className={`cursor-pointer transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-500/10'
          : 'border-slate-600 hover:border-slate-500'
      }`}
      onClick={onSelect}
      styles={{
        body: { padding: '12px' },
      }}
    >
      <div className="flex items-start gap-3">
        {/* 拖拽手柄 */}
        <div className="cursor-grab text-slate-500 hover:text-slate-300 mt-1">
          <HolderOutlined />
        </div>

        {/* 主内容 */}
        <div className="flex-1 min-w-0">
          {/* 标题行 */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-slate-400 text-sm">{index + 1}.</span>
            <span className="font-medium text-slate-200">
              {skillInfo?.display_name || step.skill || '未选择 Skill'}
            </span>
            {!step.skill && (
              <Tooltip title="请选择 Skill">
                <WarningOutlined className="text-yellow-500" />
              </Tooltip>
            )}
          </div>

          {/* ID 和输出 */}
          <div className="text-xs text-slate-400 mb-2">
            <span className="text-slate-500">ID:</span> {step.id}
            {step.output_key && (
              <>
                <span className="mx-2">→</span>
                <span className="text-green-400">{step.output_key}</span>
              </>
            )}
          </div>

          {/* 输入参数预览 */}
          {inputKeys.length > 0 && (
            <div className="text-xs text-slate-500 mb-2">
              <span>输入: </span>
              {inputKeys.slice(0, 2).map((key, i) => (
                <span key={key}>
                  {i > 0 && ', '}
                  <code className="text-slate-400">{key}</code>
                </span>
              ))}
              {inputKeys.length > 2 && (
                <span className="text-slate-600"> +{inputKeys.length - 2}</span>
              )}
            </div>
          )}

          {/* 标签 */}
          <div className="flex flex-wrap gap-1">
            {hasCondition && (
              <Tooltip title={step.condition}>
                <Tag color="purple" className="text-xs">
                  条件执行
                </Tag>
              </Tooltip>
            )}
            {isSkipOnFail && (
              <Tag color="orange" className="text-xs">
                失败跳过
              </Tag>
            )}
            {step.max_retries && step.max_retries > 1 && (
              <Tag color="blue" className="text-xs">
                重试 {step.max_retries}
              </Tag>
            )}
          </div>
        </div>

        {/* 删除按钮 */}
        <Button
          type="text"
          size="small"
          danger
          icon={<DeleteOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        />
      </div>
    </Card>
  );
};

export default StepNode;
