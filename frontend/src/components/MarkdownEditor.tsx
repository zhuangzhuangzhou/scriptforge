import React, { useState, useCallback, useMemo } from 'react';
import MonacoEditor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkFrontmatter from 'remark-frontmatter';
import { Tag, Tooltip } from 'antd';
import { EyeOutlined, CodeOutlined, ExpandOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { GlassTabs } from './ui/GlassTabs';

// 提取标题生成大纲
interface TocItem {
  id: string;
  text: string;
  level: number;
}

const extractToc = (markdown: string): TocItem[] => {
  const lines = markdown.split('\n');
  const toc: TocItem[] = [];
  let inCodeBlock = false;
  let inFrontmatter = false;
  let frontmatterCount = 0;

  for (const line of lines) {
    // 跳过 frontmatter
    if (line.trim() === '---') {
      frontmatterCount++;
      if (frontmatterCount === 1) {
        inFrontmatter = true;
        continue;
      } else if (frontmatterCount === 2) {
        inFrontmatter = false;
        continue;
      }
    }
    if (inFrontmatter) continue;

    // 跳过代码块
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;

    // 匹配标题
    const match = line.match(/^(#{1,6})\s+(.+)$/);
    if (match) {
      const level = match[1].length;
      const text = match[2].trim();
      const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
      toc.push({ id, text, level });
    }
  }

  return toc;
};

// Markdown 预览样式
const MARKDOWN_STYLES = `
  .markdown-preview {
    color: #e2e8f0;
    line-height: 1.75;
    font-size: 14px;
  }

  .markdown-preview h1,
  .markdown-preview h2,
  .markdown-preview h3,
  .markdown-preview h4,
  .markdown-preview h5,
  .markdown-preview h6 {
    color: #f1f5f9;
    font-weight: 600;
    margin-top: 1.5em;
    margin-bottom: 0.75em;
    line-height: 1.3;
  }

  .markdown-preview h1 { font-size: 1.75em; border-bottom: 1px solid rgba(51, 65, 85, 0.5); padding-bottom: 0.3em; }
  .markdown-preview h2 { font-size: 1.5em; border-bottom: 1px solid rgba(51, 65, 85, 0.3); padding-bottom: 0.3em; }
  .markdown-preview h3 { font-size: 1.25em; }
  .markdown-preview h4 { font-size: 1.1em; }

  .markdown-preview p {
    margin: 1em 0;
    white-space: pre-wrap;
  }

  .markdown-preview ul,
  .markdown-preview ol {
    margin: 1em 0;
    padding-left: 2em;
  }

  .markdown-preview li {
    margin: 0.5em 0;
  }

  .markdown-preview ul { list-style-type: disc; }
  .markdown-preview ol { list-style-type: decimal; }

  .markdown-preview code {
    background: rgba(51, 65, 85, 0.5);
    color: #22d3ee;
    padding: 0.2em 0.4em;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9em;
  }

  .markdown-preview pre {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(51, 65, 85, 0.5);
    border-radius: 8px;
    padding: 1em;
    overflow-x: auto;
    margin: 1em 0;
  }

  .markdown-preview pre code {
    background: transparent;
    padding: 0;
    color: #e2e8f0;
  }

  .markdown-preview blockquote {
    border-left: 4px solid #22d3ee;
    margin: 1em 0;
    padding: 0.5em 1em;
    background: rgba(34, 211, 238, 0.05);
    color: #94a3b8;
  }

  .markdown-preview a {
    color: #22d3ee;
    text-decoration: none;
  }

  .markdown-preview a:hover {
    text-decoration: underline;
  }

  .markdown-preview table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
  }

  .markdown-preview th,
  .markdown-preview td {
    border: 1px solid rgba(51, 65, 85, 0.5);
    padding: 0.5em 1em;
    text-align: left;
  }

  .markdown-preview th {
    background: rgba(51, 65, 85, 0.3);
    font-weight: 600;
    color: #f1f5f9;
  }

  .markdown-preview tr:nth-child(even) {
    background: rgba(51, 65, 85, 0.1);
  }

  .markdown-preview hr {
    border: none;
    border-top: 1px solid rgba(51, 65, 85, 0.5);
    margin: 2em 0;
  }

  .markdown-preview img {
    max-width: 100%;
    border-radius: 8px;
  }

  .markdown-preview strong {
    color: #f1f5f9;
    font-weight: 600;
  }

  .markdown-preview em {
    color: #cbd5e1;
  }
`;

// 模板变量定义
const TEMPLATE_VARIABLES = [
  // 项目信息变量
  { name: '{{project_name}}', description: '项目名称' },
  { name: '{{project_id}}', description: '项目 ID' },
  // 系统信息变量
  { name: '{{current_date}}', description: '当前日期' },
  { name: '{{current_time}}', description: '当前时间' },
  { name: '{{user_name}}', description: '当前用户名' },
  { name: '{{user_id}}', description: '当前用户 ID' },
  // 统计数据变量
  { name: '{{chapter_count}}', description: '章节数量' },
  { name: '{{word_count}}', description: '总字数' },
  // 自定义变量
  { name: '{{custom_1}}', description: '自定义变量 1' },
  { name: '{{custom_2}}', description: '自定义变量 2' },
];

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string;
  showVariables?: boolean;
  showSplitView?: boolean;
  readOnly?: boolean;
  renderHeader?: (tabs: React.ReactNode) => React.ReactNode;
}

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  height = '500px',
  showVariables = true,
  showSplitView = true,
  readOnly = false,
  renderHeader,
}) => {
  // 根据 showSplitView 设置默认视图模式
  const defaultMode = showSplitView ? 'split' : 'edit';
  const [viewMode, setViewMode] = useState<'split' | 'edit' | 'preview'>(defaultMode);

  // 提取大纲
  const toc = useMemo(() => extractToc(value), [value]);

  // 大纲只在预览模式显示
  const showToc = viewMode === 'preview';

  const handleEditorChange = useCallback((newValue: string | undefined) => {
    onChange(newValue || '');
  }, [onChange]);

  const insertVariable = useCallback((variable: string) => {
    onChange(value + variable);
  }, [value, onChange]);

  // 滚动到指定标题
  const scrollToHeading = useCallback((id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  // 大纲面板（仅预览模式显示）
  const TocPanel = toc.length > 0 && showToc && (
    <div className="w-48 flex-shrink-0 bg-slate-900/30 border border-slate-700/50 rounded-lg ml-4 overflow-hidden">
      <div className="text-xs text-slate-400 p-3 border-b border-slate-700/50 flex items-center gap-1">
        <UnorderedListOutlined /> 大纲
      </div>
      <div className="p-2 space-y-1 overflow-auto" style={{ maxHeight: 'calc(100% - 40px)' }}>
        {toc.map((item, index) => (
          <div
            key={`${item.id}-${index}`}
            className="text-sm text-slate-400 hover:text-cyan-400 cursor-pointer truncate transition-colors py-1.5 px-2 rounded hover:bg-slate-800/50"
            style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
            onClick={() => scrollToHeading(item.id)}
            title={item.text}
          >
            {item.text}
          </div>
        ))}
      </div>
    </div>
  );

  // 编辑器组件（编辑模式不显示大纲）
  const EditorPane = () => (
    <div className="h-full">
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
    </div>
  );

  // 预览组件（带大纲）
  const PreviewPane = (
    <div className="h-full flex overflow-hidden">
      <div
        className="flex-1 border border-slate-700 rounded-lg overflow-auto bg-slate-900/50 p-4"
      >
        <style>{MARKDOWN_STYLES}</style>
        <div className="markdown-preview">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkFrontmatter]}
            components={{
              h1: ({ children }) => {
                const text = String(children);
                const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                return <h1 id={id}>{children}</h1>;
              },
              h2: ({ children }) => {
                const text = String(children);
                const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                return <h2 id={id}>{children}</h2>;
              },
              h3: ({ children }) => {
                const text = String(children);
                const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                return <h3 id={id}>{children}</h3>;
              },
              h4: ({ children }) => {
                const text = String(children);
                const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                return <h4 id={id}>{children}</h4>;
              },
              h5: ({ children }) => {
                const text = String(children);
                const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                return <h5 id={id}>{children}</h5>;
              },
              h6: ({ children }) => {
                const text = String(children);
                const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                return <h6 id={id}>{children}</h6>;
              },
            }}
          >
            {value || '*暂无内容*'}
          </ReactMarkdown>
        </div>
      </div>
      {TocPanel}
    </div>
  );

  // 变量提示面板
  const VariablesPanel = showVariables && (
    <div className="p-3 mb-4 bg-slate-800/50 rounded-lg border border-slate-700">
      <div className="text-xs text-slate-400 mb-2">可用变量（点击插入）：</div>
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
    ...(showSplitView ? [{ key: 'split', label: <span><ExpandOutlined /> 分栏</span> }] : []),
    { key: 'edit', label: <span><CodeOutlined /> 编辑</span> },
    { key: 'preview', label: <span><EyeOutlined /> 预览</span> },
  ];

  // 标签页组件（含大纲开关）
  const TabsComponent = (
    <div className="flex items-center gap-2">
      <GlassTabs
        size="small"
        activeKey={viewMode}
        onChange={(key) => setViewMode(key as 'split' | 'edit' | 'preview')}
        items={viewModeItems}
      />
    </div>
  );

  return (
    <div className="markdown-editor h-full flex flex-col">
      {renderHeader ? renderHeader(TabsComponent) : TabsComponent}

      {VariablesPanel}

      <div className="flex-1 min-h-0">
        {viewMode === 'split' && (
          <div className="grid grid-cols-2 gap-4 h-full">
            {EditorPane()}
            {PreviewPane}
          </div>
        )}
        {viewMode === 'edit' && EditorPane()}
        {viewMode === 'preview' && PreviewPane}
      </div>
    </div>
  );
};

export default MarkdownEditor;
