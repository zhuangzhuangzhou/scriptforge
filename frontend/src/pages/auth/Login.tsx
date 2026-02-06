import React, { useState, useEffect } from 'react';
import { User, Lock, ArrowRight, Sparkles, Film, Wand2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd'; 
import { useAuth } from '../../context/AuthContext';
import AnimatedBackground from '../../components/AnimatedBackground';
import InputGroup from '../../components/ui/InputGroup';
import './auth.css';

const typewriterTexts = [
  "让故事跃然银幕之上",
  "AI 赋能，重塑创作灵感",
  "文字到影像的无限可能"
];

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentTextIndex, setCurrentTextIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTextIndex((prev) => (prev + 1) % typewriterTexts.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    // 前端校验
    const trimmedUsername = username.trim();
    const trimmedPassword = password.trim();

    if (!trimmedUsername) {
      message.warning('请输入账号');
      return;
    }
    if (!trimmedPassword) {
      message.warning('请输入密码');
      return;
    }

    setIsLoading(true);
    try {
      await login(trimmedUsername, trimmedPassword);
      message.success('登录成功');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setIsLoading(false);
    }
  };

  const sentence = typewriterTexts[currentTextIndex].split("");
  const typewriterVariants = { hidden: { opacity: 1 }, visible: { opacity: 1, transition: { staggerChildren: 0.08 } }, exit: { opacity: 0, transition: { duration: 0.5 } } };
  const letterVariants = { hidden: { opacity: 0, display: 'none' }, visible: { opacity: 1, display: 'inline' } };

  return (
    <div className="relative w-full h-screen flex overflow-hidden bg-slate-950 text-white font-sans selection:bg-cyan-500/30">
      <AnimatedBackground />

      <div className="relative z-10 w-full h-full flex flex-col md:flex-row">
        {/* 左侧：品牌与打字机标题 */}
        <div className="w-full md:w-1/2 lg:w-3/5 flex flex-col justify-center items-start p-8 md:p-16 lg:p-24 relative overflow-hidden">
          <div className="relative z-20 w-full max-w-2xl">
            <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-12">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-700 flex items-center justify-center shadow-[0_0_20px_rgba(8,145,178,0.4)] border border-cyan-400/20 backdrop-blur-md">
                <Film className="text-white drop-shadow-md" size={28} />
              </div>
              <h1 className="text-3xl font-bold text-white tracking-tight">AI ScriptFlow</h1>
            </motion.div>

            {/* 彩色打字机主标题 */}
            <div className="h-40 md:h-52 mb-6">
              <AnimatePresence mode="wait">
                <motion.h2 
                  key={currentTextIndex}
                  variants={typewriterVariants}
                  initial="hidden" animate="visible" exit="exit"
                  className="text-5xl md:text-6xl lg:text-7xl font-black leading-[1.1] tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 animate-gradient"
                >
                  {sentence.map((char, index) => (
                    <motion.span key={index} variants={letterVariants}>{char}</motion.span>
                  ))}
                  <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 0.8 }} className="inline-block ml-1 text-cyan-400 font-normal">|</motion.span>
                </motion.h2>
              </AnimatePresence>
            </div>

            {/* 固定辅助文案区域 */}
            <div className="h-20 mb-8 border-l-2 border-slate-700 pl-6 flex flex-col justify-center">
              <p className="text-slate-300 text-lg font-medium italic">通过下一代 AI 模型，将您的创意剧本实时转化为电影级画面。</p>
              <p className="text-slate-500 text-sm mt-2 font-mono opacity-60">Unleash infinite possibilities from text to video.</p>
            </div>

            {/* 功能标签 (恢复旧版图标样式) */}
            <div className="mt-12 flex gap-4 flex-wrap">
                <div className="px-5 py-2.5 rounded-full bg-slate-900/40 backdrop-blur-md border border-slate-700/50 flex items-center gap-2 text-sm text-slate-300 shadow-lg">
                   <Sparkles size={16} className="text-amber-400" /> 智能剧本拆解
                </div>
                <div className="px-5 py-2.5 rounded-full bg-slate-900/40 backdrop-blur-md border border-slate-700/50 flex items-center gap-2 text-sm text-slate-300 shadow-lg">
                   <Wand2 size={16} className="text-purple-400" /> 多角色 Agent
                </div>
            </div>
          </div>
        </div>

        {/* 右侧：登录卡片 */}
        <div className="w-full md:w-1/2 lg:w-2/5 flex flex-col justify-center items-center p-6 relative">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-md">
            <div className="relative backdrop-blur-xl bg-slate-900/70 border border-slate-800 shadow-2xl rounded-2xl p-8 md:p-10 overflow-hidden group hover:border-cyan-500/30 transition-all duration-500">
              {/* 鼠标触发的动态边角 */}
              <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-cyan-500/30 rounded-tl-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />
              <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-cyan-500/30 rounded-tr-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />
              <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-cyan-500/30 rounded-bl-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-cyan-500/30 rounded-br-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />

              <div className="mb-8 relative z-10 text-center">
                <h3 className="text-2xl font-bold text-white mb-2">欢迎回来</h3>
                <p className="text-slate-400 text-sm">请登录以继续您的创作之旅</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-6 relative z-10">
                <InputGroup id="username" type="text" label="账号" placeholder="用户名 / 邮箱" icon={User} value={username} onChange={(e) => setUsername(e.target.value)} />
                <div className="space-y-2">
                   <InputGroup id="password" type="password" label="密码" placeholder="请输入密码" icon={Lock} value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} type="submit" disabled={isLoading} className="w-full mt-4 relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 p-[1px] cursor-pointer">
                  <div className="relative bg-transparent h-full w-full rounded-xl px-4 py-3.5 flex items-center justify-center gap-2 group-hover:brightness-110">
                    {isLoading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><span className="font-bold text-white tracking-wide uppercase">Login</span><ArrowRight size={18} className="text-white group-hover:translate-x-1 transition-transform" /></>}
                  </div>
                </motion.button>
              </form>

              <div className="mt-8 pt-6 border-t border-slate-800 text-center relative z-10">
                <p className="text-sm text-slate-500">还没有账号? <a onClick={() => navigate('/register')} className="cursor-pointer font-medium text-cyan-400 hover:text-cyan-300 ml-1">立即注册</a></p>
              </div>
            </div>

            {/* 增加的底部政策链接 */}
            <div className="flex justify-center items-center gap-6 text-xs text-slate-500 mt-6">
               <button className="hover:text-cyan-400 transition-colors">用户协议</button>
               <span className="w-1 h-1 rounded-full bg-slate-700" />
               <button className="hover:text-cyan-400 transition-colors">隐私政策</button>
               <span className="w-1 h-1 rounded-full bg-slate-700" />
               <span className="font-mono">v2.4.0</span>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Login;
