import React, { useState } from 'react';
import { User, Lock, Mail, ArrowRight, UserPlus, Film, Sparkles, Wand2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import AnimatedBackground from '../../components/AnimatedBackground';
import InputGroup from '../../components/ui/InputGroup';
import './auth.css';

interface RegisterForm {
  email: string
  username: string
  password: string
  confirmPassword: string
  fullName?: string
}

const Register: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<RegisterForm>({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    fullName: ''
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData(prev => ({ ...prev, [id]: value }));
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      message.error('两次密码输入不一致');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          username: formData.username,
          password: formData.password,
          full_name: formData.fullName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '注册失败');
      }

      message.success('注册成功，请登录');
      navigate('/login');
    } catch (error: any) {
      message.error(error.message || '注册失败，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative w-full h-screen flex overflow-hidden bg-slate-950 text-white">
      <AnimatedBackground />

      <div className="relative z-10 w-full h-full flex flex-col md:flex-row">
        
        {/* Left Side: Brand & Vision */}
        <div className="w-full md:w-1/2 lg:w-3/5 flex flex-col justify-center items-start p-8 md:p-16 lg:p-24 relative overflow-hidden">
          <div className="relative z-20 w-full max-w-2xl">
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

            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white leading-tight mb-6 tracking-tight">
                加入我们，
                <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 animate-gradient">
                  开启创作之旅
                </span>
              </h2>
              <p className="text-slate-400 text-lg md:text-xl max-w-md font-light">
                Join us and start your creative journey.
              </p>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 0.6 }}
              className="mt-12 flex gap-4 flex-wrap"
            >
                <div className="px-4 py-2 rounded-full bg-slate-800/40 backdrop-blur-md border border-slate-700/50 flex items-center gap-2 text-sm text-slate-300">
                   <UserPlus size={16} className="text-emerald-400" /> 免费注册
                </div>
                <div className="px-4 py-2 rounded-full bg-slate-800/40 backdrop-blur-md border border-slate-700/50 flex items-center gap-2 text-sm text-slate-300">
                   <Sparkles size={16} className="text-amber-400" /> 立即体验
                </div>
            </motion.div>
          </div>
        </div>

        {/* Right Side: Register Form */}
        <div className="w-full md:w-1/2 lg:w-2/5 flex flex-col justify-center items-center p-6 relative">
          
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="w-full max-w-md"
          >
            <div className="backdrop-blur-xl bg-slate-900/60 border border-slate-800/60 shadow-2xl rounded-3xl p-8 relative overflow-hidden group">
              
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />
              
              <div className="mb-6">
                <h3 className="text-2xl font-semibold text-white mb-2">创建新账号</h3>
                <p className="text-slate-400 text-sm">填写以下信息完成注册</p>
              </div>

              <form onSubmit={handleRegister} className="space-y-4">
                <InputGroup
                  id="email"
                  type="email"
                  label="电子邮箱"
                  placeholder="name@example.com"
                  icon={Mail}
                  value={formData.email}
                  onChange={handleChange}
                />

                <InputGroup
                  id="username"
                  type="text"
                  label="用户名"
                  placeholder="请输入用户名"
                  icon={User}
                  value={formData.username}
                  onChange={handleChange}
                />

                <InputGroup
                  id="fullName"
                  type="text"
                  label="姓名 (可选)"
                  placeholder="请输入姓名"
                  icon={User}
                  value={formData.fullName || ''}
                  onChange={handleChange}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <InputGroup
                    id="password"
                    type="password"
                    label="密码"
                    placeholder="至少6位"
                    icon={Lock}
                    value={formData.password}
                    onChange={handleChange}
                  />
                  <InputGroup
                    id="confirmPassword"
                    type="password"
                    label="确认密码"
                    placeholder="重复密码"
                    icon={Lock}
                    value={formData.confirmPassword}
                    onChange={handleChange}
                  />
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={isLoading}
                  className="w-full mt-4 relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 p-[1px] group focus:outline-none focus:ring-2 focus:ring-cyan-500/40 cursor-pointer"
                >
                  <div className="relative bg-gradient-to-r from-blue-600 to-cyan-600 h-full w-full rounded-xl px-4 py-3.5 flex items-center justify-center gap-2 transition-all group-hover:bg-opacity-90">
                    {isLoading ? (
                      <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : (
                      <>
                        <span className="font-semibold text-white tracking-wide">立即注册</span>
                        <ArrowRight size={18} className="text-white/80 group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </div>
                </motion.button>
              </form>

              <div className="mt-6 pt-6 border-t border-slate-800 text-center">
                <p className="text-sm text-slate-500">
                  已有账号?{' '}
                  <a onClick={() => navigate('/login')} className="cursor-pointer font-medium text-cyan-400 hover:text-cyan-300 transition-colors ml-1 hover:underline decoration-cyan-500/30">
                    直接登录
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

export default Register;
