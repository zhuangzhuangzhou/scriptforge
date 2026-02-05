import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, Sparkles, X, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  id: string;
  role: 'user' | 'ai';
  text: string;
  type?: 'text' | 'action_result';
}

interface AICopilotProps {
  visible: boolean;
  onClose: () => void;
  context: string; // 'CONFIG' | 'PLOT' | 'SCRIPT'
}

const SUGGESTIONS = {
  CONFIG: ['分析当前小说风格', '推荐适合的改编模型', '评估预估集数合理性'],
  PLOT: ['检查当前批次的剧情漏洞', '分析主角的情感弧光', '生成分集悬念建议'],
  SCRIPT: ['优化这段对话的潜台词', '增加环境描写的画面感', '转换为黑色电影风格'],
};

const AICopilot: React.FC<AICopilotProps> = ({ visible, onClose, context }) => {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'ai', text: '你好，我是你的 AI 编剧助手。我可以帮你梳理剧情、优化对白或检查逻辑漏洞。请问有什么可以帮你的？' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, visible]);

  const handleSend = async (text: string = input) => {
    if (!text.trim()) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    // Mock AI Response
    setTimeout(() => {
      const aiMsg: Message = { 
        id: (Date.now() + 1).toString(), 
        role: 'ai', 
        text: `收到，正在基于上下文 [${context}] 进行分析...\n\n这是一个模拟的智能回复。在实际系统中，我将调用大模型 API 来处理您的请求：“${text}”。` 
      };
      setMessages(prev => [...prev, aiMsg]);
      setIsTyping(false);
    }, 1500);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed top-16 right-0 bottom-0 w-80 md:w-96 bg-slate-900/95 backdrop-blur-xl border-l border-slate-700/50 shadow-2xl z-30 flex flex-col"
        >
          {/* Header */}
          <div className="h-14 border-b border-slate-800 flex items-center justify-between px-4 bg-gradient-to-r from-slate-900 to-slate-800">
            <div className="flex items-center gap-2 text-cyan-400">
              <Bot size={20} />
              <span className="font-semibold text-white">AI Copilot</span>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
              <X size={18} />
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4" ref={scrollRef}>
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  msg.role === 'ai' ? 'bg-cyan-600/20 text-cyan-400' : 'bg-slate-700 text-slate-300'
                }`}>
                  {msg.role === 'ai' ? <Bot size={16} /> : <User size={16} />}
                </div>
                <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed max-w-[85%] ${
                  msg.role === 'ai' 
                    ? 'bg-slate-800 border border-slate-700 text-slate-200' 
                    : 'bg-cyan-600 text-white'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-3">
                 <div className="w-8 h-8 rounded-full bg-cyan-600/20 flex items-center justify-center shrink-0 text-cyan-400">
                    <Bot size={16} />
                 </div>
                 <div className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                 </div>
              </div>
            )}
          </div>

          {/* Suggestions & Input */}
          <div className="p-4 border-t border-slate-800 bg-slate-900">
            {/* Contextual Suggestions */}
            <div className="flex gap-2 overflow-x-auto pb-3 mb-1 no-scrollbar">
              {SUGGESTIONS[context as keyof typeof SUGGESTIONS]?.map((sug, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(sug)}
                  className="whitespace-nowrap px-3 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-300 transition-colors flex items-center gap-1.5 group"
                >
                  <Sparkles size={10} className="text-amber-400 group-hover:text-amber-300" />
                  {sug}
                </button>
              ))}
            </div>

            {/* Input Field */}
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="输入指令或询问..."
                className="w-full bg-slate-800/50 border border-slate-700 rounded-xl pl-4 pr-12 py-3 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
              />
              <button 
                onClick={() => handleSend()}
                disabled={!input.trim() || isTyping}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:hover:bg-cyan-600"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AICopilot;
