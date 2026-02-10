import React, { useEffect, useRef, useState } from 'react';
import { Terminal, X, ChevronDown, ChevronUp, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'thinking' | 'llm_call' | 'stream';
  message: string;
  detail?: any;
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

// 格式化流式内容，美化 JSON 显示
const formatStreamContent = (content: string): React.ReactNode => {
  try {
    // 尝试解析 JSON
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const json = JSON.parse(jsonMatch[0]);
      return (
        <div className="space-y-1">
          {Object.entries(json).map(([key, value]) => (
            <div key={key} className="flex gap-2">
              <span className="text-cyan-400 font-semibold">{key}:</span>
              <span className="text-slate-300">{JSON.stringify(value)}</span>
            </div>
          ))}
        </div>
      );
    }
  } catch (e) {
    // 不是 JSON，直接返回原文
  }
  return content;
};

interface ConsoleLoggerProps {
  logs: LogEntry[];
  llmStats?: LLMCallStats;
  visible: boolean;
  isProcessing: boolean;
  progress?: number;
  currentStep?: string;
  onClose: () => void;
}

const ConsoleLogger: React.FC<ConsoleLoggerProps> = ({
  logs,
  llmStats,
  visible,
  isProcessing,
  progress = 0,
  currentStep = '',
  onClose
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  // 调试日志
  useEffect(() => {
    console.log('[ConsoleLogger] Props 更新:', {
      isProcessing,
      progress,
      currentStep,
      visible
    });
  }, [isProcessing, progress, currentStep, visible]);

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

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current && !isMinimized && visible) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isMinimized, visible]);

  if (!visible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 50 }}
      className={`fixed bottom-4 right-4 z-50 flex flex-col bg-slate-900 border border-slate-700 shadow-2xl rounded-xl overflow-hidden transition-all duration-300 ${
        isMinimized ? 'w-64 h-12' : 'w-96 md:w-[500px] h-80'
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

           {/* 进度和步骤显示 */}
           {isProcessing && currentStep && (
              <div className="flex items-center gap-2 ml-2 flex-1 min-w-0">
                <span className="flex h-2 w-2 relative flex-shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                </span>
                <span className="text-xs text-cyan-400 font-mono flex-shrink-0">{progress}%</span>
                <span className="text-xs text-slate-400 truncate">{currentStep}</span>
              </div>
           )}

           {isProcessing && !currentStep && (
              <span className="flex h-2 w-2 relative ml-2 flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>
           )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
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
            className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-2 bg-slate-950/80 backdrop-blur"
          >
            {logs.length === 0 && (
              <div className="text-slate-500 italic opacity-50">Waiting for agent tasks...</div>
            )}
            {logs.map((log) => (
              <div key={log.id} className="flex gap-2 items-start">
                <span className="text-slate-600 shrink-0 select-none">[{log.timestamp}]</span>

                {/* LLM 调用日志 */}
                {log.type === 'llm_call' ? (
                  <div className="flex-1 min-w-0">
                    <div
                      className="flex items-start gap-2 group cursor-pointer"
                      onClick={() => log.detail && toggleLogDetail(log.id)}
                    >
                      <Zap size={14} className="text-cyan-400 mt-0.5 flex-shrink-0" />
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
                  <span className={`break-words ${
                    log.type === 'error' ? 'text-red-400' :
                    log.type === 'success' ? 'text-green-400' :
                    log.type === 'warning' ? 'text-amber-400' :
                    log.type === 'thinking' ? 'text-cyan-300 italic' :
                    log.type === 'stream' ? 'text-purple-300 font-normal whitespace-pre-wrap leading-relaxed' :
                    'text-slate-300'
                  }`}>
                    {log.type === 'thinking' && <span className="mr-1">◈</span>}
                    {log.type === 'stream' && <span className="mr-2 text-purple-400">▸</span>}
                    {/* 格式化 JSON 显示 */}
                    {log.type === 'stream' ? formatStreamContent(log.message) : log.message}
                  </span>
                )}
              </div>
            ))}
            {isProcessing && (
              <div className="flex gap-2 items-start animate-pulse">
                <span className="text-slate-600 select-none">[Running]</span>
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
