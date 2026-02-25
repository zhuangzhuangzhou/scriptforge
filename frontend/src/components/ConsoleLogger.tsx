import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Terminal, X, ChevronDown, ChevronUp, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import type { LogEntry, LLMCallStats } from '../hooks/useConsoleLogger';

// ============================================================================
// 类型定义
// ============================================================================

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
  episodeNumber?: number;
  onClose: () => void;
}

// ============================================================================
// 常量配置
// ============================================================================

const LOG_TYPE_CONFIG: Record<string, { label: string; colorClass: string }> = {
  info: { label: 'INFO', colorClass: 'text-blue-400' },
  success: { label: 'SUCCESS', colorClass: 'text-green-400' },
  warning: { label: 'WARN', colorClass: 'text-amber-400' },
  error: { label: 'ERROR', colorClass: 'text-red-400' },
  thinking: { label: 'THINK', colorClass: 'text-cyan-400' },
  llm_call: { label: 'LLM', colorClass: 'text-purple-400' },
  stream: { label: 'STREAM', colorClass: 'text-pink-400' },
  formatted: { label: 'FMT', colorClass: 'text-slate-400' },
};

// 任务名称映射
const TASK_NAME_REPLACEMENTS: [RegExp, string][] = [
  [/网文改编剧情拆解/g, '剧集拆解'],
  [/剧情拆解质量校验/g, '质量检查'],
  [/剧情拆解/g, '剧集拆解'],
  [/质量校验/g, '质量检查'],
];

// ============================================================================
// 工具函数
// ============================================================================

/** 统一任务名称 */
const normalizeTaskName = (text: string): string => {
  let result = text;
  for (const [pattern, replacement] of TASK_NAME_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }
  return result;
};

/** 获取日志类型配置 */
const getLogTypeInfo = (type: string) => {
  return LOG_TYPE_CONFIG[type] || { label: type.toUpperCase(), colorClass: 'text-slate-400' };
};

/** 判断是否为关键内容（用于 Format 模式过滤） */
const isKeyContent = (log: LogEntry): boolean => {
  const msg = log.message;

  // 排除：纯 JSON 格式的原始数据
  const trimmed = msg.trim();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return false;

  // 排除：过长的内容（可能是原始数据）
  if (msg.length > 500) return false;

  // 排除：包含技术细节的日志
  if (msg.includes('token') || msg.includes('model_config') || msg.includes('batch_id')) return false;

  // 保留：任务完成/失败状态
  if (log.type === 'success' && msg.includes('完成')) return true;
  if (log.type === 'error') return true;

  // 保留：Agent 运行状态（开始/结束）
  if (msg.includes('Agent') && (msg.includes('运行结束') || msg.includes('开始运行'))) return true;

  // 保留：质检结果摘要
  if (msg.includes('【总体】') || msg.includes('质检通过') || msg.includes('质检未通过')) return true;
  if (msg.includes('质量检查') && msg.includes('评分')) return true;

  // 保留：关键进度信息
  if (msg.includes('生成完成') || msg.includes('拆解完成')) return true;

  return false;
};

/** 尝试格式化 JSON */
const tryFormatJson = (text: string): { isJson: boolean; formatted: string } => {
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    return { isJson: false, formatted: text };
  }
  try {
    const parsed = JSON.parse(trimmed);
    return { isJson: true, formatted: JSON.stringify(parsed, null, 2) };
  } catch {
    return { isJson: false, formatted: text };
  }
};

// ============================================================================
// 子组件：格式化内容渲染器
// ============================================================================

interface FormattedContentProps {
  message: string;
}

const FormattedContent: React.FC<FormattedContentProps> = ({ message }) => {
  // 预处理文本
  const text = normalizeTaskName(message).replace(/^◆\s*/, '');

  // 检测 JSON 内容
  const { isJson, formatted } = tryFormatJson(text);
  if (isJson) {
    return (
      <pre className="text-[10px] text-slate-400 bg-slate-900/50 p-2 rounded border border-slate-700/50 overflow-x-auto">
        {formatted}
      </pre>
    );
  }

  const lines = text.split(/\r?\n/);

  // 渲染单行
  const renderLine = (line: string, index: number): React.ReactNode => {
    const trimmed = line.trim();

    // 分隔线
    if (/^-+\s*$/.test(trimmed)) {
      return <span className="text-slate-500/70">------</span>;
    }

    // Agent 运行状态行
    if (/剧集拆解\s*Agent\s*正在运行中/.test(trimmed)) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 text-amber-200 bg-amber-500/15 border border-amber-400/40">
          {trimmed}
        </span>
      );
    }

    if (/质量检查\s*Agent\s*正在运行中/.test(trimmed)) {
      return (
        <span className="inline-flex items-center gap-2 px-2.5 py-0.5 text-sky-50 bg-gradient-to-r from-sky-600/40 via-sky-500/25 to-sky-600/40 border border-sky-300/60">
          <span className="h-1.5 w-1.5 bg-sky-300 rounded-full animate-pulse" />
          <span className="tracking-wide">{trimmed}</span>
        </span>
      );
    }

    // 质检维度格式：【维度1】冲突强度评估 评分 75 通过
    const dimensionMatch = trimmed.match(/【维度\s*(\d+)】\s*(.+?)\s*评分\s*[:：]?\s*(\d+)\s*(通过|未通过|失败)/);
    if (dimensionMatch) {
      const [, num, name, score, status] = dimensionMatch;
      const scoreNum = parseInt(score, 10);
      const scoreClass = scoreNum >= 80 ? 'text-emerald-400' : scoreNum >= 60 ? 'text-amber-400' : 'text-red-400';
      const statusClass = status === '通过' ? 'text-emerald-400' : 'text-red-400';

      return (
        <span className="inline-flex items-center gap-1.5">
<span className="text-violet-400 font-semibold">【维度{num}】</span>
          <span className="text-slate-100">{name}</span>
          <span className="text-slate-500 text-xs">评分</span>
          <span className={`${scoreClass} font-semibold`}>{score}</span>
          <span className={`${statusClass} font-medium`}>{status}</span>
        </span>
      );
    }

    // 质检总体格式
    const summaryMatch = trimmed.match(/(?:质量检查\s*Agent\s*运行结束|【总体】)\s*评分\s*[:：]?\s*(\d+)\s*(通过|未通过|失败)/);
    if (summaryMatch) {
      const [, score, status] = summaryMatch;
      const scoreNum = parseInt(score, 10);
      const scoreClass = scoreNum >= 80 ? 'text-emerald-300' : scoreNum >= 60 ? 'text-amber-300' : 'text-red-300';
      const statusClass = status === '通过' ? 'text-emerald-300' : 'text-red-300';

      return (
        <>
          <span className="text-sky-300/80">------</span>
          <br />
          <span className="inline-flex items-center gap-2 px-2.5 py-0.5 text-sky-50 bg-gradient-to-r from-sky-600/40 via-sky-500/25 to-sky-600/40 border border-sky-300/60">
            <span className="h-1.5 w-1.5 bg-sky-300 rounded-full animate-pulse" />
            <span className="tracking-wide">质量检查 Agent 运行结束</span>
            <span className="text-slate-300">评分</span>
            <span className={scoreClass}>{score}</span>
            <span className={statusClass}>{status}</span>
          </span>
          <br />
          <span className="text-sky-300/80">------</span>
        </>
      );
    }

    // 【】标签高亮
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    const bracketRegex = /【([^】]+)】/g;
    let match;

    while ((match = bracketRegex.exec(trimmed)) !== null) {
      if (match.index > lastIndex) {
        parts.push(trimmed.slice(lastIndex, match.index));
      }

      const content = match[1];
      const colorClass = (content.includes('第') && content.includes('集')) ? 'text-purple-400' : 'text-slate-200';

      parts.push(
        <span key={`${index}-${match.index}`} className={colorClass}>
          【{content}】
        </span>
      );

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < trimmed.length) {
      parts.push(trimmed.slice(lastIndex));
    }

    return parts.length > 0 ? parts : trimmed;
  };

  return (
    <>
      {lines.map((line, index) => (
        <React.Fragment key={index}>
          {index > 0 && <br />}
          {renderLine(line, index)}
        </React.Fragment>
      ))}
    </>
  );
};

// ============================================================================
// 子组件：状态信息栏
// ============================================================================

interface StatusInfoProps {
  episodeNumber: number;
  batchNumber: number;
  currentStep: string;
  progress: number;
  currentRound: number;
  totalRounds: number;
}

const StatusInfo: React.FC<StatusInfoProps> = ({
  episodeNumber,
  batchNumber,
  currentStep,
  progress,
  currentRound,
  totalRounds,
}) => {
  const taskName = currentStep
    .replace(/\u{1F680}|\u{2705}|\u{274C}|\u{26A0}\u{FE0F}|\u{25C8}/gu, '')
    .trim();

  const roundTone = useMemo(() => {
    const total = totalRounds > 0 ? totalRounds : 1;
    const base = 'bg-slate-800/80 text-slate-200 border-slate-700';
    if (total <= 1 || currentRound <= 1) return base;

    const ratio = Math.min(1, Math.max(0, (currentRound - 1) / (total - 1)));
    const bands = [
      base,
      'bg-slate-800/80 text-slate-200 border-slate-600',
      'bg-slate-800/80 text-slate-100 border-slate-500',
      'bg-slate-800/80 text-slate-100 border-slate-400'
    ];
    return bands[Math.min(bands.length - 1, Math.round(ratio * (bands.length - 1)))];
  }, [currentRound, totalRounds]);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {episodeNumber > 0 && (
        <span className="px-2.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[11px]">
          当前剧集：第 {episodeNumber} 集
        </span>
      )}
      {batchNumber > 0 && !episodeNumber && (
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
          {currentRound}{totalRounds > 0 ? `/${totalRounds}` : ''} 轮
        </span>
      )}
    </div>
  );
};

// ============================================================================
// 子组件：LLM 统计面板
// ============================================================================

interface LLMStatsPanelProps {
  stats: LLMCallStats;
}

const LLMStatsPanel: React.FC<LLMStatsPanelProps> = ({ stats }) => {
  if (stats.total <= 0) return null;

  return (
    <div className="px-3 py-2 bg-cyan-500/10 border-b border-cyan-500/20">
      <div className="flex items-center justify-between text-xs">
        <span className="text-cyan-300 flex items-center gap-1">
          <Zap size={12} className="text-cyan-400" />
          LLM 调用统计
        </span>
        <span className="text-cyan-400 font-mono font-semibold">{stats.total} 次</span>
      </div>
      {stats.stages.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {stats.stages.map((stage, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 bg-slate-800/80 rounded text-[10px] text-slate-400 border border-slate-700/50"
            >
              {stage.stage}:{' '}
              <span className={stage.status === 'passed' ? 'text-green-400' : 'text-red-400'}>
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
  );
};

// ============================================================================
// 子组件：日志条目
// ============================================================================

interface LogItemProps {
  log: LogEntry;
  viewMode: 'raw' | 'formatted';
  isExpanded: boolean;
  onToggleExpand: () => void;
}

const LogItem: React.FC<LogItemProps> = ({ log, viewMode, isExpanded, onToggleExpand }) => {
  const typeInfo = getLogTypeInfo(log.type);

  // LLM 调用日志
  if (log.type === 'llm_call') {
    return (
      <div className="flex gap-2 items-start">
        <span className="text-slate-600 shrink-0 select-none text-[10px]">[{log.timestamp}]</span>
        <div className="flex-1 min-w-0">
          {viewMode === 'raw' && (
            <span className={`inline-block text-[9px] font-mono font-bold mr-2 px-1 rounded ${typeInfo.colorClass} bg-slate-800/80`}>
              {typeInfo.label}
            </span>
          )}
          <div
            className="flex items-start gap-2 group cursor-pointer"
            onClick={() => log.detail && onToggleExpand()}
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
                  {(viewMode === 'raw' || isExpanded) && (
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
      </div>
    );
  }

  // 普通日志
  const logColorClass = {
    info: 'text-blue-400',
    error: 'text-red-400',
    success: 'text-green-400',
    warning: 'text-amber-400',
    thinking: 'text-cyan-300 italic',
    stream: 'text-purple-300 font-normal whitespace-pre-wrap leading-relaxed',
    formatted: 'text-slate-200 font-normal whitespace-pre-wrap leading-relaxed',
  }[log.type] || 'text-slate-300';

  return (
    <div className="flex gap-2 items-start">
      <span className="text-slate-600 shrink-0 select-none text-[10px]">[{log.timestamp}]</span>
      <div className="flex-1 min-w-0">
        {viewMode === 'raw' && (
          <span className={`inline-block text-[9px] font-mono font-bold mr-2 px-1 rounded ${typeInfo.colorClass} bg-slate-800/80`}>
            {typeInfo.label}
          </span>
        )}
        <span className={`break-words ${logColorClass}`}>
          {log.type === 'thinking' && <span className="mr-1">◈</span>}
          {log.type === 'stream' && <span className="mr-2 text-purple-400">▸</span>}
          {viewMode === 'formatted' ? (
            <FormattedContent message={log.message} />
          ) : (
            normalizeTaskName(log.message)
          )}
        </span>
        {viewMode === 'raw' && log.detail && (
          <div
            className="mt-1 ml-4 p-2 bg-slate-900/50 rounded border border-slate-700/50 text-slate-400 text-[10px] cursor-pointer hover:bg-slate-800/50"
            onClick={onToggleExpand}
          >
            {isExpanded ? (
              <pre className="whitespace-pre-wrap break-words text-slate-300">
                {JSON.stringify(log.detail, null, 2)}
              </pre>
            ) : (
              <span className="text-slate-500">[点击展开详情]</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// 主组件
// ============================================================================

const ConsoleLogger: React.FC<ConsoleLoggerProps> = ({
  logs,
  llmStats,
  visible,
  isProcessing,
  progress = 0,
  currentStep = '',
  currentRound = 0,
  totalRounds = 0,
  batchNumber = 0,
  episodeNumber = 0,
  onClose
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'raw' | 'formatted'>('formatted');
  const [userScrolled, setUserScrolled] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastScrollTopRef = useRef(0);

  // 切换日志详情展开
  const toggleLogDetail = useCallback((logId: string) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  }, []);

  // 滚动事件处理
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    // 用户向上滚动 → 停止自动滚动
    if (scrollTop < lastScrollTopRef.current && !isAtBottom) {
      setUserScrolled(true);
    }

    // 用户滚动到底部 → 恢复自动滚动
    if (isAtBottom) {
      setUserScrolled(false);
    }

    lastScrollTopRef.current = scrollTop;
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current && !isMinimized && visible && !userScrolled) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isMinimized, visible, userScrolled]);

  // 过滤日志
  const filteredLogs = useMemo(() => {
    return viewMode === 'formatted' ? logs.filter(isKeyContent) : logs;
  }, [logs, viewMode]);

  if (!visible) return null;

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
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Terminal size={14} className="text-cyan-400 flex-shrink-0" />
          <span className="text-xs font-medium text-slate-300 flex-shrink-0">System Console</span>
          {isProcessing && (
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-[10px] text-green-400">运行中</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {/* 视图模式切换 */}
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

      {/* 展开内容 */}
      {!isMinimized && (
        <>
          {/* LLM 统计面板 */}
          {llmStats && <LLMStatsPanel stats={llmStats} />}

          {/* 状态/进度面板 */}
          <div className="px-4 py-2 bg-slate-900/80 border-b border-slate-800">
            <div className="text-[11px] leading-4 text-slate-300">
              <StatusInfo
                episodeNumber={episodeNumber}
                batchNumber={batchNumber}
                currentStep={currentStep}
                progress={progress}
                currentRound={currentRound}
                totalRounds={totalRounds}
              />
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
              <LogItem
                key={log.id}
                log={log}
                viewMode={viewMode}
                isExpanded={expandedLogs.has(log.id)}
                onToggleExpand={() => toggleLogDetail(log.id)}
              />
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
