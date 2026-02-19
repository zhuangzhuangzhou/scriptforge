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
      // RAW 模式显示所有非 formatted 类型的日志
      return log.type !== 'formatted';
    }
    return log.type === 'formatted';
  });

  // 获取日志类型的中文标签和颜色
  const getLogTypeInfo = (type: string): { label: string; colorClass: string } => {
    const typeMap: Record<string, { label: string; colorClass: string }> = {
      info: { label: 'INFO', colorClass: 'text-blue-400' },
      success: { label: 'SUCCESS', colorClass: 'text-green-400' },
      warning: { label: 'WARN', colorClass: 'text-amber-400' },
      error: { label: 'ERROR', colorClass: 'text-red-400' },
      thinking: { label: 'THINK', colorClass: 'text-cyan-400' },
      llm_call: { label: 'LLM', colorClass: 'text-purple-400' },
      stream: { label: 'STREAM', colorClass: 'text-pink-400' },
      formatted: { label: 'FMT', colorClass: 'text-slate-400' },
    };
    return typeMap[type] || { label: type.toUpperCase(), colorClass: 'text-slate-400' };
  };

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

    const lines = text.split(/\r?\n/);

    const isDividerLine = (line: string) => /^-+\s*$/.test(line.trim());
    const isBreakdownLine = (line: string) => /剧集拆解\s*Agent\s*正在运行中/.test(line);
    const isQALine = (line: string) => /质量检查\s*Agent\s*正在运行中/.test(line);
    const getSectionType = (line: string, index: number, allLines: string[]) => {
      if (isBreakdownLine(line)) return 'breakdown';
      if (isQALine(line)) return 'qa';
      if (isDividerLine(line)) {
        if (index > 0 && isBreakdownLine(allLines[index - 1])) return 'breakdown';
        if (index + 1 < allLines.length && isBreakdownLine(allLines[index + 1])) return 'breakdown';
        if (index > 0 && isQALine(allLines[index - 1])) return 'qa';
        if (index + 1 < allLines.length && isQALine(allLines[index + 1])) return 'qa';
      }
      return null;
    };

    const renderFormattedLine = (line: string, index: number, allLines: string[]) => {
      const trimmed = line.trim();
      const sectionType = getSectionType(line, index, allLines);

      if (isDividerLine(trimmed)) {
        const dividerClass =
          sectionType === 'breakdown'
            ? 'text-amber-300/80'
            : sectionType === 'qa'
              ? 'text-sky-300/80'
              : 'text-slate-500/70';
        return <span className={dividerClass}>------</span>;
      }

      if (sectionType === 'breakdown' && isBreakdownLine(trimmed)) {
        return (
          <span className="inline-flex items-center px-2 py-0.5 text-amber-200 bg-amber-500/15 border border-amber-400/40">
            {trimmed}
          </span>
        );
      }

      if (sectionType === 'qa' && isQALine(trimmed)) {
        return (
          <span className="inline-flex items-center gap-2 px-2.5 py-0.5 text-sky-50 bg-gradient-to-r from-sky-600/40 via-sky-500/25 to-sky-600/40 border border-sky-300/60 shadow-[0_0_0_1px_rgba(56,189,248,0.25)]">
            <span className="h-1.5 w-1.5 bg-sky-300 rounded-full animate-pulse" />
            <span className="tracking-wide">{trimmed}</span>
          </span>
        );
      }

      // 处理质检维度格式：【维度1】冲突强度评估  评分 75 通过
      const qaDimensionRegex = /【维度\s*(\d+)】\s*([^\n]+?)\s*评分\s*[:：]?\s*(\d+)\s*(通过|未通过|失败)/g;
      if (qaDimensionRegex.test(trimmed)) {
        qaDimensionRegex.lastIndex = 0;
        const parts: React.ReactNode[] = [];
        let lastIndex = 0;
        let match;

        while ((match = qaDimensionRegex.exec(trimmed)) !== null) {
          if (match.index > lastIndex) {
            parts.push(trimmed.slice(lastIndex, match.index));
          }

          const [, dimensionNum, dimensionName, score, status] = match;
          const isPassed = status === '通过';
          parts.push(
            <span key={match.index} className="inline-flex items-center gap-1">
              <span className="text-violet-300">【维度{dimensionNum}】</span>
              <span className="text-slate-200">{dimensionName}</span>
              <span className="text-slate-500">评分</span>
              <span className="text-slate-200">{score}</span>
              <span className={isPassed ? 'text-emerald-300' : 'text-red-300'}>
                {status}
              </span>
            </span>
          );

          lastIndex = match.index + match[0].length;
        }

        if (lastIndex < trimmed.length) {
          parts.push(trimmed.slice(lastIndex));
        }

        return parts;
      }

      // 处理质检总体格式（兼容旧版【总体】评分格式与新版“质量检查 Agent 运行结束”格式）
      const qaSummaryRegexes = [
        /质量检查\s*Agent\s*运行结束\s*评分\s*[:：]?\s*(\d+)\s*(通过|未通过|失败)/,
        /【总体】\s*评分\s*[:：]?\s*(\d+)\s*(通过|未通过|失败)/
      ];
      let summaryMatch: RegExpMatchArray | null = null;
      for (const regex of qaSummaryRegexes) {
        const match = trimmed.match(regex);
        if (match) {
          summaryMatch = match;
          break;
        }
      }
      if (summaryMatch) {
        const score = parseInt(summaryMatch[1], 10);
        const status = summaryMatch[2];
        const scoreClass = score >= 80 ? 'text-emerald-300' : score >= 60 ? 'text-amber-300' : 'text-red-300';
        const statusClass = status === '通过' ? 'text-emerald-300' : 'text-red-300';
        const dividerClass = 'text-sky-300/80';
        return (
          <>
            <span className={dividerClass}>------</span>
            <br />
            <span className="inline-flex items-center gap-2 px-2.5 py-0.5 text-sky-50 bg-gradient-to-r from-sky-600/40 via-sky-500/25 to-sky-600/40 border border-sky-300/60 shadow-[0_0_0_1px_rgba(56,189,248,0.25)]">
              <span className="h-1.5 w-1.5 bg-sky-300 rounded-full animate-pulse" />
              <span className="tracking-wide">质量检查 Agent 运行结束</span>
              <span className="text-slate-300">评分</span>
              <span className={scoreClass}>{summaryMatch[1]}</span>
              <span className={statusClass}>{status}</span>
            </span>
            <br />
            <span className={dividerClass}>------</span>
          </>
        );
      }

      // 处理【】包裹的关键动作
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      const bracketRegex = /【([^】]+)】/g;
      let match;

      while ((match = bracketRegex.exec(trimmed)) !== null) {
        if (match.index > lastIndex) {
          parts.push(renderTextWithColors(trimmed.slice(lastIndex, match.index)));
        }

        const content = match[1];
        let colorClass = 'text-slate-200';

        if (content.includes('第') && content.includes('集')) {
          colorClass = 'text-purple-400';
        }

        parts.push(
          <span key={match.index} className={colorClass}>
            【{content}】
          </span>
        );

        lastIndex = match.index + match[0].length;
      }

      if (lastIndex < trimmed.length) {
        parts.push(renderTextWithColors(trimmed.slice(lastIndex)));
      }

      return parts.length > 0 ? parts : trimmed;
    };

    const renderedLines = lines.map((line, index) => renderFormattedLine(line, index, lines));
    return renderedLines.flatMap((node, index) =>
      index === 0
        ? [<React.Fragment key={index}>{node}</React.Fragment>]
        : [<br key={`br-${index}`} />, <React.Fragment key={index}>{node}</React.Fragment>]
    );
  };

  // 渲染带颜色的文本（场景、角色、剧情、钩子）
  const renderTextWithColors = (text: string): React.ReactNode => {
    return text;
  };

  const buildStatusInfo = () => {
    const taskName = currentStep
      .replace(/🚀/g, '')
      .replace(/✅/g, '')
      .replace(/❌/g, '')
      .replace(/⚠️/g, '')
      .replace(/◈/g, '')
      .trim();
    const total = _totalRounds > 0 ? `/${_totalRounds}` : '';

    const roundTone = (() => {
      const totalRounds = _totalRounds > 0 ? _totalRounds : 1;
      const base = 'bg-slate-800/80 text-slate-200 border-slate-700';
      if (totalRounds <= 1 || currentRound <= 1) return base;
      const ratio = Math.min(1, Math.max(0, (currentRound - 1) / (totalRounds - 1)));
      const bands = [
        base,
        'bg-slate-800/80 text-slate-200 border-slate-600',
        'bg-slate-800/80 text-slate-100 border-slate-500',
        'bg-slate-800/80 text-slate-100 border-slate-400'
      ];
      const idx = Math.min(bands.length - 1, Math.round(ratio * (bands.length - 1)));
      return bands[idx];
    })();

    return (
      <div className="flex flex-wrap items-center gap-2">
        {batchNumber > 0 && (
          <span className="px-2.5 py-0.5 rounded bg-slate-800/80 text-slate-200 border border-slate-700 text-[11px]">
            拆解批次：{batchNumber}
          </span>
        )}
        {taskName && (
          <span className="px-2.5 py-0.5 rounded bg-slate-800/80 text-slate-200 border border-slate-700 text-[11px]">
            当前任务: {normalizeTaskName(taskName)}
          </span>
        )}
        <span className="px-2.5 py-0.5 rounded bg-slate-800/80 text-slate-200 border border-slate-700 text-[11px]">
          进度: {progress}%
        </span>
        {currentRound > 0 && (
          <span className={`px-2.5 py-0.5 rounded border text-[11px] ${roundTone}`}>
            {currentRound}{total} 轮
          </span>
        )}
      </div>
    );
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
          {isProcessing && (
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-[10px] text-green-400">运行中</span>
            </span>
          )}

          {/* 进度和状态显示移至上区 */}
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {/* RAW / Formatted 切换按钮 */}
          {!isMinimized && (
            <div className="flex mr-2 items-center" onClick={(e) => e.stopPropagation()}>
              <div className="relative flex items-center w-[104px] h-6 rounded-full bg-slate-800/80 border border-slate-700 p-[1px]">
                <span
                  className={`absolute left-[1px] top-[1px] h-[20px] w-[50px] rounded-full bg-teal-500/35 border border-teal-400/50 shadow-sm transition-transform duration-200 ${
                    viewMode === 'raw' ? 'translate-x-[50px]' : 'translate-x-0'
                  }`}
                />
                <button
                  onClick={() => setViewMode('formatted')}
                  className={`relative z-10 w-[50px] h-6 text-[10px] tracking-wide transition-colors ${
                    viewMode === 'formatted' ? 'text-teal-100' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Format
                </button>
                <button
                  onClick={() => setViewMode('raw')}
                  className={`relative z-10 w-[50px] h-6 text-[10px] tracking-wide transition-colors ${
                    viewMode === 'raw' ? 'text-teal-100' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Raw
                </button>
              </div>
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

          {/* 状态/进度面板 */}
          <div className="px-4 py-2 bg-slate-900/80 border-b border-slate-800">
            <div className="text-[11px] leading-4 text-slate-300">
              {buildStatusInfo()}
            </div>
          </div>

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
                    {/* RAW 模式：显示日志类型标签 */}
                    {viewMode === 'raw' && (
                      <span className={`inline-block text-[9px] font-mono font-bold mr-2 px-1 rounded ${getLogTypeInfo(log.type).colorClass} bg-slate-800/80`}>
                        {getLogTypeInfo(log.type).label}
                      </span>
                    )}
                    <div
                      className="flex items-start gap-2 group cursor-pointer"
                      onClick={() => log.detail && toggleLogDetail(log.id)}
                    >
                      {viewMode !== 'raw' && <Zap size={12} className="text-cyan-400 mt-0.5 flex-shrink-0" />}
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
                            {/* RAW 模式默认展开 detail */}
                            {viewMode === 'raw' ? (
                              <div className="mt-1 p-2 bg-slate-900/50 rounded border border-slate-700/50 text-slate-400">
                                <pre className="whitespace-pre-wrap break-words">
                                  {JSON.stringify(log.detail, null, 2)}
                                </pre>
                              </div>
                            ) : (
                              expandedLogs.has(log.id) && (
                                <div className="mt-1 p-2 bg-slate-900/50 rounded border border-slate-700/50 text-slate-400">
                                  <pre className="whitespace-pre-wrap break-words">
                                    {JSON.stringify(log.detail, null, 2)}
                                  </pre>
                                </div>
                              )
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* 普通日志 */
                  <div className="flex-1 min-w-0">
                    {/* RAW 模式：显示日志类型标签 */}
                    {viewMode === 'raw' && (
                      <span className={`inline-block text-[9px] font-mono font-bold mr-2 px-1 rounded ${getLogTypeInfo(log.type).colorClass} bg-slate-800/80`}>
                        {getLogTypeInfo(log.type).label}
                      </span>
                    )}
                    <span className={`break-words ${
                      log.type === 'error' ? 'text-red-400' :
                      log.type === 'success' ? 'text-green-400' :
                      log.type === 'warning' ? 'text-amber-400' :
                      log.type === 'thinking' ? 'text-cyan-300 italic' :
                      log.type === 'stream' ? 'text-purple-300 font-normal whitespace-pre-wrap leading-relaxed' :
                      log.type === 'formatted' ? 'text-slate-200 font-normal whitespace-pre-wrap leading-relaxed' :
                      'text-slate-300'
                    }`}>
                      {log.type === 'thinking' && <span className="mr-1">◈</span>}
                      {log.type === 'stream' && viewMode === 'raw' && <br />}
                      {log.type === 'stream' && <span className="mr-2 text-purple-400">▸</span>}
                      {log.type === 'formatted'
                        ? renderFormattedContent(log.message)
                        : normalizeTaskName(log.message)
                      }
                    </span>
                    {/* RAW 模式：显示 detail 内容 */}
                    {viewMode === 'raw' && log.detail && (
                      <div
                        className="mt-1 ml-4 p-2 bg-slate-900/50 rounded border border-slate-700/50 text-slate-400 text-[10px] cursor-pointer hover:bg-slate-800/50"
                        onClick={() => toggleLogDetail(log.id)}
                      >
                        {expandedLogs.has(log.id) ? (
                          <pre className="whitespace-pre-wrap break-words text-slate-300">
                            {JSON.stringify(log.detail, null, 2)}
                          </pre>
                        ) : (
                          <span className="text-slate-500">[点击展开 detail: {JSON.stringify(log.detail)}]</span>
                        )}
                      </div>
                    )}
                  </div>
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
