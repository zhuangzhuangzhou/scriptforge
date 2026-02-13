import React, { useState, useCallback } from 'react';
import MonacoEditor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Tabs, Tag, Tooltip } from 'antd';
import { EyeOutlined, CodeOutlined, ExpandOutlined } from '@ant-design/icons';

// 模板变量定义
const TEMPLATE_VARIABLES = [
  { name: '{{chapters_text}}', description: '小说章节原文内容' },
  { name: '{{novel_type}}', description: '小说类型（玄幻/都市/言情等）' },
  { name: '{{batch_info}}', description: '批次信息（章节范围）' },
  { name: '{{previous_context}}', description: '前文剧情摘要' },
  { name: '{{character_list}}', description: '已出场角色列表' },
  { name: '{{plot_points}}', description: '已拆解的剧情点列表' },
  { name: '{{episode_number}}', description: '当前集数' },
  { name: '{{total_episodes}}', description: '预计总集数' },
];

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string;
  showVariables?: boolean;
  readOnly?: boolean;
}

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  height = '500px',
  showVariables = true,
  readOnly = false,
}) => {
  const [viewMode, setViewMode] = useState<'split' | 'edit' | 'preview'>('split');

  const handleEditorChange = useCallback((newValue: string | undefined) => {
    onChange(newValue || '');
  }, [onChange]);

  const insertVariable = useCallback((variable: string) => {
    onChange(value + variable);
  }, [value, onChange]);

  // 编辑器组件
  const EditorPane = (
    <div className="h-full border border-slate-700 rounded-lg overflow-hidden">
      <MonacoEditor
        height="100%"
        language="markdown"
        theme="vs-dark"
        value={value}
        onChange={handleEditorChange}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          wordWrap: 'on',
          lineNumbers: 'on',
          readOnly,
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
      />
    </div>
  );

  // 预览组件
  const PreviewPane = (
    <div
      className="h-full border border-slate-700 rounded-lg overflow-auto bg-slate-900/50 p-4"
      style={{ height }}
    >
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {value || '*暂无内容*'}
        </ReactMarkdown>
      </div>
    </div>
  );

  // 变量提示面板
  const VariablesPanel = showVariables && (
    <div className="mb-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
      <div className="text-xs text-slate-400 mb-2">可用模板变量（点击插入）：</div>
      <div className="flex flex-wrap gap-2">
        {TEMPLATE_VARIABLES.map((v) => (
          <Tooltip key={v.name} title={v.description}>
            <Tag
              className="cursor-pointer hover:bg-cyan-500/20 transition-colors"
              color="cyan"
              onClick={() => insertVariable(v.name)}
            >
              {v.name}
            </Tag>
          </Tooltip>
        ))}
      </div>
    </div>
  );

  // 视图模式切换
  const viewModeItems = [
    { key: 'split', label: <span><ExpandOutlined /> 分栏</span> },
    { key: 'edit', label: <span><CodeOutlined /> 编辑</span> },
    { key: 'preview', label: <span><EyeOutlined /> 预览</span> },
  ];

  return (
    <div className="markdown-editor">
      {VariablesPanel}

      <div className="mb-2 flex justify-end">
        <Tabs
          size="small"
          activeKey={viewMode}
          onChange={(key) => setViewMode(key as 'split' | 'edit' | 'preview')}
          items={viewModeItems}
        />
      </div>

      <div style={{ height }}>
        {viewMode === 'split' && (
          <div className="grid grid-cols-2 gap-4 h-full">
            {EditorPane}
            {PreviewPane}
          </div>
        )}
        {viewMode === 'edit' && EditorPane}
        {viewMode === 'preview' && PreviewPane}
      </div>
    </div>
  );
};

export default MarkdownEditor;
