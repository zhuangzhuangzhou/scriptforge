import React, { useState, useEffect } from 'react';
import { User, Lock, ArrowRight, Sparkles, Film, Wand2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd'; 
import { useAuth } from '../../context/AuthContext';
import AnimatedBackground from '../../components/AnimatedBackground';
import InputGroup from '../../components/InputGroup';

// Typewriter text content
const typewriterTexts = [
  "让故事跃然银幕之上",
  "AI 赋能，重塑创作灵感",
  "文字到影像的无限可能"
];

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  
  // Form State
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Animation State
  const [currentTextIndex, setCurrentTextIndex] = useState(0);

  // Typewriter effect logic
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTextIndex((prev) => (prev + 1) % typewriterTexts.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(username, password);
      localStorage.setItem('username', username);
      message.success('登录成功');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error.message || '登录失败，请检查用户名和密码');
    } finally {
      setIsLoading(false);
    }
  };

  const sentence = typewriterTexts[currentTextIndex].split("");

  const typewriterVariants = {
    hidden: { opacity: 1 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
    exit: { opacity: 0, transition: { duration: 0.5 } }
  };

  const letterVariants = {
    hidden: { opacity: 0, display: 'none' },
    visible: {
      opacity: 1,
      display: 'inline',
    },
  };

  return (
    <div className="relative w-full h-screen flex overflow-hidden bg-slate-950 text-white">
      <AnimatedBackground />

      {/* Main Container with Glassmorphism */}
      <div className="relative z-10 w-full h-full flex flex-col md:flex-row">
        
        {/* Left Side: Brand & Vision */}
        <div className="w-full md:w-1/2 lg:w-3/5 flex flex-col justify-center items-start p-8 md:p-16 lg:p-24 relative overflow-hidden">
          <div className="relative z-20 w-full max-w-2xl">
             {/* Logo / Brand Name */}
            <motion.div 
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="flex items-center gap-3 mb-12"
            >
              <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <Film className="text-white" size={28} />
              </div>
              <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 tracking-tight">
                AI ScriptFlow
              </h1>
            </motion.div>

            {/* Typewriter Slogan */}
            <div className="h-32 mb-8"> {/* Fixed height to prevent layout shift */}
              <AnimatePresence mode="wait">
                <motion.div 
                  key={currentTextIndex}
                  variants={typewriterVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                >
                  <h2 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white leading-tight tracking-tight">
                    {sentence.map((char, index) => (
                      <motion.span key={index} variants={letterVariants}>
                        {char}
                      </motion.span>
                    ))}
                    <motion.span
                      animate={{ opacity: [0, 1, 0] }}
                      transition={{ repeat: Infinity, duration: 0.8 }}
                      className="inline-block ml-1 text-cyan-400"
                    >
                      |
                    </motion.span>
                  </h2>
                </motion.div>
              </AnimatePresence>
            </div>
            
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5, duration: 1 }}
              className="text-slate-400 text-lg md:text-xl max-w-md font-light"
            >
              Unleash infinite possibilities from text to video.
            </motion.p>

            {/* Feature Pills */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 0.6 }}
              className="mt-12 flex gap-4 flex-wrap"
            >
                <div className="px-4 py-2 rounded-full bg-slate-800/40 backdrop-blur-md border border-slate-700/50 flex items-center gap-2 text-sm text-slate-300">
                   <Sparkles size={16} className="text-amber-400" /> 智能生成
                </div>
                <div className="px-4 py-2 rounded-full bg-slate-800/40 backdrop-blur-md border border-slate-700/50 flex items-center gap-2 text-sm text-slate-300">
                   <Wand2 size={16} className="text-purple-400" /> 一键渲染
                </div>
            </motion.div>
          </div>
        </div>

        {/* Right Side: Login Form */}
        <div className="w-full md:w-1/2 lg:w-2/5 flex flex-col justify-center items-center p-6 relative">
          
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="w-full max-w-md"
          >
             {/* Glass Card */}
            <div className="backdrop-blur-xl bg-slate-900/60 border border-slate-800/60 shadow-2xl rounded-3xl p-8 md:p-10 relative overflow-hidden group">
              
              {/* Top gradient line */}
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />
              
              <div className="mb-8">
                <h3 className="text-2xl font-semibold text-white mb-2">欢迎回来</h3>
                <p className="text-slate-400 text-sm">请登录以继续您的创作之旅</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-6">
                <InputGroup
                  id="username"
                  type="text"
                  label="用户名 / 邮箱"
                  placeholder="name@example.com"
                  icon={User}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />

                <div className="space-y-2">
                   <InputGroup
                    id="password"
                    type="password"
                    label="密码"
                    placeholder="••••••••"
                    icon={Lock}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <div className="flex justify-end">
                    <a href="#" className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">
                      忘记密码?
                    </a>
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={isLoading}
                  className="w-full relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 p-[1px] group focus:outline-none focus:ring-2 focus:ring-cyan-500/40 cursor-pointer"
                >
                  <div className="relative bg-gradient-to-r from-blue-600 to-cyan-600 h-full w-full rounded-xl px-4 py-3.5 flex items-center justify-center gap-2 transition-all group-hover:bg-opacity-90">
                    {isLoading ? (
                      <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : (
                      <>
                        <span className="font-semibold text-white tracking-wide">登 录</span>
                        <ArrowRight size={18} className="text-white/80 group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </div>
                </motion.button>
              </form>

              <div className="mt-8 pt-6 border-t border-slate-800 text-center">
                <p className="text-sm text-slate-500">
                  还没有账号?{' '}
                  <a onClick={() => navigate('/register')} className="cursor-pointer font-medium text-cyan-400 hover:text-cyan-300 transition-colors ml-1 hover:underline decoration-cyan-500/30">
                    立即注册
                  </a>
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Login;
