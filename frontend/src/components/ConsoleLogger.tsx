import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal, X, ChevronDown, ChevronUp, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'thinking' | 'llm_call' | 'stream' | 'formatted';
  message: string;
  detail?: any;
  finalized?: boolean; // 标记流式日志是否已完成
}

export interface LLMCallStats {
  total: number;
  stages: Array<{
    stage: string;
    validator: string;
    status: string;
    score?: number;
    timestamp?: string;
  }>;
}

interface ConsoleLoggerProps {
  logs: LogEntry[];
  llmStats?: LLMCallStats;
  visible: boolean;
  isProcessing: boolean;
  progress?: number;
  currentStep?: string;
  currentRound?: number;
  totalRounds?: number;
  batchNumber?: number;
  onClose: () => void;
}

const ConsoleLogger: React.FC<ConsoleLoggerProps> = ({
  logs,
  llmStats,
  visible,
  isProcessing,
  progress = 0,
  currentStep = '',
  currentRound = 0,
  totalRounds: _totalRounds = 0,
  batchNumber = 0,
  onClose
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'raw' | 'formatted'>('formatted');
  const [userScrolled, setUserScrolled] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastScrollTopRef = useRef(0);

  const toggleLogDetail = (logId: string) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  // 检测用户是否手动滚动
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    // 如果用户向上滚动，标记为手动滚动
    if (scrollTop < lastScrollTopRef.current && !isAtBottom) {
      setUserScrolled(true);
    }

    // 如果用户滚动到底部，重置标记
    if (isAtBottom) {
      setUserScrolled(false);
    }

    lastScrollTopRef.current = scrollTop;
  }, []);

  // 自动滚动到底部（仅当用户没有手动滚动时）
  useEffect(() => {
    if (scrollRef.current && !isMinimized && visible && !userScrolled) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isMinimized, visible, userScrolled]);

  // 根据视图模式过滤日志
  const filteredLogs = logs.filter(log => {
    if (viewMode === 'raw') {
      // RAW 模式：隐藏格式化日志，显示原始 stream
      return log.type !== 'formatted';
    } else {
      // Formatted 模式：隐藏原始 stream，显示格式化日志
      return log.type !== 'stream';
    }
  });

  if (!visible) return null;

  // 统一名称映射函数
  const normalizeTaskName = (text: string): string => {
    return text
      .replace(/网文改编剧情拆解/g, '剧集拆解')
      .replace(/剧情拆解质量校验/g, '质量检查')
      .replace(/剧情拆解/g, '剧集拆解')
      .replace(/质量校验/g, '质量检查');
  };

  // 渲染格式化内容（颜色丰富化）
  const renderFormattedContent = (message: string) => {
    // 先统一名称
    let text = normalizeTaskName(message);

    // 去掉开头的 ◆ 符号
    text = text.replace(/^◆\s*/, '');

    // 处理质检维度格式：【维度名】xxx 得分:90 状态:通过
    const qaDimensionRegex = /【([^】]+)】\s*([^\s]+)\s*得分[:：]\s*(\d+)\s*状态[:：]\s*(通过|未通过|失败)/g;
    if (qaDimensionRegex.test(text)) {
      qaDimensionRegex.lastIndex = 0;
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;

      while ((match = qaDimensionRegex.exec(text)) !== null) {
        // 添加匹配之前的文本
        if (match.index > lastIndex) {
          parts.push(text.slice(lastIndex, match.index));
        }

        const [, dimensionNum, dimensionName, score, status] = match;
        const isPassed = status === '通过';
        const scoreNum = parseInt(score, 10);

        parts.push(
          <span key={match.index} className="inline-flex items-center gap-1">
            <span className="text-purple-400">【{dimensionNum}】</span>
            <span className="text-slate-300">{dimensionName}</span>
            <span className="text-slate-500">得分:</span>
            <span className={scoreNum >= 80 ? 'text-green-400' : scoreNum >= 60 ? 'text-yellow-400' : 'text-red-400'}>
              {score}
            </span>
            <span className="text-slate-500">状态:</span>
            <span className={isPassed ? 'text-green-400' : 'text-red-400'}>
              {status}
            </span>
          </span>
        );

        lastIndex = match.index + match[0].length;
      }

      // 添加剩余文本
      if (lastIndex < text.length) {
        parts.push(text.slice(lastIndex));
      }

      return parts;
    }

    // 处理【】包裹的关键动作
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    const bracketRegex = /【([^】]+)】/g;
    let match;

    while ((match = bracketRegex.exec(text)) !== null) {
      // 添加【】之前的文本
      if (match.index > lastIndex) {
        parts.push(renderTextWithColors(text.slice(lastIndex, match.index)));
      }

      // 根据内容决定颜色
      const content = match[1];
      let colorClass = 'text-cyan-400'; // 默认颜色

      if (content.includes('通过') || content.includes('成功') || content.includes('完成')) {
        colorClass = 'text-green-400';
      } else if (content.includes('失败') || content.includes('错误')) {
        colorClass = 'text-red-400';
      } else if (content.includes('警告') || content.includes('跳过')) {
        colorClass = 'text-yellow-400';
      } else if (content.includes('第') && content.includes('集')) {
        colorClass = 'text-purple-400 font-semibold';
      } else if (content.includes('维度') || content.match(/^维度\d+$/)) {
        colorClass = 'text-purple-400';
      }

      parts.push(
        <span key={match.index} className={colorClass}>
          【{content}】
        </span>
      );

      lastIndex = match.index + match[0].length;
    }

    // 添加剩余文本
    if (lastIndex < text.length) {
      parts.push(renderTextWithColors(text.slice(lastIndex)));
    }

    return parts.length > 0 ? parts : text;
  };

  // 渲染带颜色的文本（场景、角色、剧情、钩子）
  const renderTextWithColors = (text: string): React.ReactNode => {
    // 检测并着色特定关键词
    const patterns = [
      { regex: /(场景[:：]\s*)([^\n,，]+)/g, labelClass: 'text-slate-400', valueClass: 'text-blue-300' },
      { regex: /(角色[:：]\s*)([^\n,，]+)/g, labelClass: 'text-slate-400', valueClass: 'text-amber-300' },
      { regex: /(剧情[:：]\s*)([^\n,，]+)/g, labelClass: 'text-slate-400', valueClass: 'text-emerald-300' },
      { regex: /(钩子[:：]\s*)([^\n,，]+)/g, labelClass: 'text-slate-400', valueClass: 'text-pink-300' },
      { regex: /(剧情钩子[:：]\s*)([^\n,，]+)/g, labelClass: 'text-slate-400', valueClass: 'text-pink-300' },
      { regex: /(事件[:：]\s*)([^\n,，]+)/g, labelClass: 'text-slate-400', valueClass: 'text-emerald-300' },
      { regex: /(钩子类型[:：]\s*)([^\n,，]+)/g, labelClass: 'text-slate-400', valueClass: 'text-pink-300' },
    ];

    // 简单处理：直接返回文本，复杂着色在 CSS 中处理
    for (const pattern of patterns) {
      if (pattern.regex.test(text)) {
        // 重置 regex
        pattern.regex.lastIndex = 0;
        return text;
      }
    }

    return text;
  };

  // 构建标题信息
  // 格式: 批次:2   当前任务:剧集拆解/质量检查  次数:1
  const buildHeaderInfo = () => {
    const parts: string[] = [];

    // 批次号
    if (batchNumber > 0) {
      parts.push(`批次:${batchNumber}`);
    }

    // 当前任务
    if (currentStep) {
      // 提取任务名称（去掉 emoji 和前缀）
      const taskName = currentStep
        .replace(/🚀/g, '')
        .replace(/✅/g, '')
        .replace(/❌/g, '')
        .replace(/⚠️/g, '')
        .replace(/◈/g, '')
        .trim();

      // 统一名称映射
      let displayName = taskName;
      if (taskName.includes('网文改编剧情拆解') || taskName.includes('剧情拆解') || taskName.includes('剧集拆解')) {
        displayName = '剧集拆解';
      } else if (taskName.includes('剧情拆解质量校验') || taskName.includes('质量校验') || taskName.includes('质量检查') || taskName.includes('质检')) {
        displayName = '质量检查';
      }

      parts.push(`当前任务:${displayName}`);
    }

    // 次数
    if (currentRound > 0) {
      parts.push(`次数:${currentRound}`);
    }

    return parts.join('   ');
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 50 }}
      className={`fixed bottom-4 right-4 z-50 flex flex-col bg-slate-900 border border-slate-700 shadow-2xl rounded-xl overflow-hidden transition-all duration-300 ${
        isMinimized ? 'w-72 h-12' : 'w-96 md:w-[560px] h-96'
      }`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 bg-slate-800 border-b border-slate-700 cursor-pointer"
        onClick={() => setIsMinimized(!isMinimized)}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Terminal size={14} className="text-cyan-400 flex-shrink-0" />
          <span className="text-xs font-medium text-slate-300 flex-shrink-0">System Console</span>

          {/* 进度和状态显示 */}
          {isProcessing && (
            <div className="flex items-center gap-2 ml-2 flex-1 min-w-0">
              {/* 闪烁指示器 */}
              <span className="flex h-2 w-2 relative flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>

              {/* 批次和任务信息 */}
              <span className="text-xs text-slate-400 truncate">
                {buildHeaderInfo()}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {/* RAW / Formatted 切换按钮 */}
          {!isMinimized && (
            <div className="flex mr-2" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => setViewMode('formatted')}
                className={`px-2 py-0.5 text-[10px] rounded-l border transition-colors ${
                  viewMode === 'formatted'
                    ? 'bg-cyan-600 text-white border-cyan-600'
                    : 'bg-slate-700 text-slate-400 border-slate-600 hover:bg-slate-600'
                }`}
              >
                Format
              </button>
              <button
                onClick={() => setViewMode('raw')}
                className={`px-2 py-0.5 text-[10px] rounded-r border-t border-r border-b transition-colors ${
                  viewMode === 'raw'
                    ? 'bg-cyan-600 text-white border-cyan-600'
                    : 'bg-slate-700 text-slate-400 border-slate-600 hover:bg-slate-600'
                }`}
              >
                RAW
              </button>
            </div>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); setIsMinimized(!isMinimized); }}
            className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white"
          >
            {isMinimized ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onClose(); }}
            className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Logs Content */}
      {!isMinimized && (
        <>
          {/* LLM 调用统计面板 */}
          {llmStats && llmStats.total > 0 && (
            <div className="px-3 py-2 bg-cyan-500/10 border-b border-cyan-500/20">
              <div className="flex items-center justify-between text-xs">
                <span className="text-cyan-300 flex items-center gap-1">
                  <Zap size={12} className="text-cyan-400" />
                  LLM 调用统计
                </span>
                <span className="text-cyan-400 font-mono font-semibold">{llmStats.total} 次</span>
              </div>
              {llmStats.stages.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {llmStats.stages.map((stage, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-slate-800/80 rounded text-[10px] text-slate-400 border border-slate-700/50"
                    >
                      {stage.stage}: <span className={stage.status === 'passed' ? 'text-green-400' : 'text-red-400'}>
                        {stage.status}
                      </span>
                      {stage.score !== undefined && (
                        <span className="ml-1 text-cyan-400">({stage.score})</span>
                      )}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 日志内容 */}
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-1 bg-slate-950/80 backdrop-blur"
          >
            {filteredLogs.length === 0 && (
              <div className="text-slate-500 italic opacity-50">Waiting for agent tasks...</div>
            )}
            {filteredLogs.map((log) => (
              <div key={log.id} className="flex gap-2 items-start">
                <span className="text-slate-600 shrink-0 select-none text-[10px]">[{log.timestamp}]</span>

                {/* LLM 调用日志 */}
                {log.type === 'llm_call' ? (
                  <div className="flex-1 min-w-0">
                    <div
                      className="flex items-start gap-2 group cursor-pointer"
                      onClick={() => log.detail && toggleLogDetail(log.id)}
                    >
                      <Zap size={12} className="text-cyan-400 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-cyan-300 text-xs break-words">{log.message}</div>
                        {log.detail && (
                          <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
                            {log.detail.status && (
                              <span className={log.detail.status === 'passed' ? 'text-green-400' : 'text-red-400'}>
                                {log.detail.status}
                              </span>
                            )}
                            {log.detail.score !== undefined && (
                              <span className="ml-2 text-cyan-400">Score: {log.detail.score}</span>
                            )}
                            {expandedLogs.has(log.id) && (
                              <div className="mt-1 p-2 bg-slate-900/50 rounded border border-slate-700/50 text-slate-400">
                                <pre className="whitespace-pre-wrap break-words">
                                  {JSON.stringify(log.detail, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* 普通日志 */
                  <span className={`break-words flex-1 ${
                    log.type === 'error' ? 'text-red-400' :
                    log.type === 'success' ? 'text-green-400' :
                    log.type === 'warning' ? 'text-amber-400' :
                    log.type === 'thinking' ? 'text-cyan-300 italic' :
                    log.type === 'stream' ? 'text-purple-300 font-normal whitespace-pre-wrap leading-relaxed' :
                    log.type === 'formatted' ? 'text-slate-200 font-normal whitespace-pre-wrap leading-relaxed' :
                    'text-slate-300'
                  }`}>
                    {log.type === 'thinking' && <span className="mr-1">◈</span>}
                    {log.type === 'stream' && <span className="mr-2 text-purple-400">▸</span>}
                    {log.type === 'formatted'
                      ? renderFormattedContent(log.message)
                      : normalizeTaskName(log.message)
                    }
                  </span>
                )}
              </div>
            ))}
            {isProcessing && (
              <div className="flex gap-2 items-start animate-pulse">
                <span className="text-slate-600 select-none text-[10px]">[Running]</span>
                <span className="text-cyan-500">_</span>
              </div>
            )}
          </div>
        </>
      )}
    </motion.div>
  );
};

export default ConsoleLogger;
