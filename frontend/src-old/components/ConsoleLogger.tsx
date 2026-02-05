import React, { useEffect, useRef, useState } from 'react';
import { Terminal, X, Minimize2, Maximize2, ChevronDown, ChevronUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'thinking';
  message: string;
}

interface ConsoleLoggerProps {
  logs: LogEntry[];
  visible: boolean;
  isProcessing: boolean;
  onClose: () => void;
}

const ConsoleLogger: React.FC<ConsoleLoggerProps> = ({ logs, visible, isProcessing, onClose }) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

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
        <div className="flex items-center gap-2">
           <Terminal size={14} className="text-cyan-400" />
           <span className="text-xs font-medium text-slate-300">System Console</span>
           {isProcessing && (
              <span className="flex h-2 w-2 relative ml-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>
           )}
        </div>
        <div className="flex items-center gap-1">
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
                    <span className={`break-words ${
                        log.type === 'error' ? 'text-red-400' :
                        log.type === 'success' ? 'text-green-400' :
                        log.type === 'warning' ? 'text-amber-400' :
                        log.type === 'thinking' ? 'text-cyan-300 italic' :
                        'text-slate-300'
                    }`}>
                        {log.type === 'thinking' && <span className="mr-1">◈</span>}
                        {log.message}
                    </span>
                </div>
            ))}
            {isProcessing && (
                <div className="flex gap-2 items-start animate-pulse">
                    <span className="text-slate-600 select-none">[Running]</span>
                    <span className="text-cyan-500">_</span>
                </div>
            )}
        </div>
      )}
    </motion.div>
  );
};

export default ConsoleLogger;
