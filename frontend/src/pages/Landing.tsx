import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen, Zap, Users, Brain, Layers,
  ArrowRight, Play, CheckCircle, ChevronDown,
  FileText, Wand2, Film, Target, Shield, Sparkles
} from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';

// 打字机文案
const heroTexts = [
  "小说一键转专业剧本",
  "AI 赋能，重塑创作灵感",
  "文字到影像的无限可能"
];

const Landing: React.FC = () => {
  const navigate = useNavigate();
  const [activeFeature, setActiveFeature] = useState(0);
  const [currentTextIndex, setCurrentTextIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTextIndex((prev) => (prev + 1) % heroTexts.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      icon: BookOpen,
      title: '智能章节解析',
      desc: '上传小说文件，AI 自动识别章节结构，支持多种格式和分章规则'
    },
    {
      icon: Brain,
      title: '剧情深度拆解',
      desc: '多维度分析人物、场景、冲突，提取核心剧情点和情感脉络'
    },
    {
      icon: Film,
      title: '专业剧本生成',
      desc: '一键转换为标准剧本格式，包含场景描述、对白、动作指示'
    },
    {
      icon: Users,
      title: '多 Agent 协作',
      desc: '剧情架构师、角色心理师、对白润色师等专业 AI 角色协同工作'
    },
    {
      icon: Wand2,
      title: '技能增强系统',
      desc: '冲突雷达、情感同步、视觉增强等可配置技能，精准优化输出'
    },
    {
      icon: Target,
      title: '质量检测报告',
      desc: '自动生成质检报告，标注潜在问题，确保剧本质量达标'
    }
  ];

  const workflow = [
    { step: '01', title: '上传小说', desc: '支持 TXT、DOCX 等格式', icon: FileText },
    { step: '02', title: '智能拆解', desc: 'AI 分析剧情结构', icon: Brain },
    { step: '03', title: '生成剧本', desc: '一键批量转换', icon: Sparkles },
    { step: '04', title: '导出交付', desc: '多格式专业输出', icon: Film }
  ];

  const stats = [
    { value: '10x', label: '效率提升' },
    { value: '95%', label: '用户满意度' },
    { value: '50+', label: '支持小说类型' },
    { value: '24/7', label: '全天候服务' }
  ];

  const sentence = heroTexts[currentTextIndex].split("");
  const typewriterVariants = {
    hidden: { opacity: 1 },
    visible: { opacity: 1, transition: { staggerChildren: 0.06 } },
    exit: { opacity: 0, transition: { duration: 0.4 } }
  };
  const letterVariants = {
    hidden: { opacity: 0, display: 'none' },
    visible: { opacity: 1, display: 'inline' }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 overflow-x-hidden relative">
      {/* 复用系统动态背景 */}
      <AnimatedBackground />

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/20">
              <Film size={20} className="text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">
              AI <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">ScriptFlow</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/login')}
              className="px-5 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              登录
            </button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/register')}
              className="px-5 py-2 text-sm font-bold bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-lg hover:shadow-lg hover:shadow-cyan-500/20 transition-all"
            >
              免费试用
            </motion.button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900/40 backdrop-blur-md border border-slate-700/50 rounded-full text-sm text-slate-400 mb-8 shadow-lg">
              <Zap size={14} className="text-cyan-400" />
              <span>AI 驱动的下一代剧本创作工具</span>
            </div>

            {/* 打字机效果标题 */}
            <div className="h-24 md:h-32 mb-6 flex items-center justify-center">
              <AnimatePresence mode="wait">
                <motion.h1
                  key={currentTextIndex}
                  variants={typewriterVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  className="text-4xl md:text-6xl lg:text-7xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500"
                >
                  {sentence.map((char, index) => (
                    <motion.span key={index} variants={letterVariants}>
                      {char}
                    </motion.span>
                  ))}
                  <motion.span
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ repeat: Infinity, duration: 0.8 }}
                    className="inline-block ml-1 text-cyan-400 font-normal"
                  >
                    |
                  </motion.span>
                </motion.h1>
              </AnimatePresence>
            </div>

            <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              上传您的小说，AI 智能拆解剧情结构，多 Agent 协作生成高质量剧本。
              <br className="hidden md:block" />
              让创作效率提升 10 倍，专注于故事本身。
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate('/register')}
                className="group relative overflow-hidden px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-all flex items-center gap-3"
              >
                <div className="absolute inset-0 w-1/2 h-full bg-white/10 -skew-x-12 -translate-x-full group-hover:translate-x-[200%] transition-transform duration-700 ease-in-out" />
                <Play size={20} />
                <span className="relative z-10">立即开始创作</span>
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform relative z-10" />
              </motion.button>
              <button
                onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-8 py-4 border border-slate-700 text-slate-300 font-medium rounded-xl hover:bg-slate-800/50 hover:border-slate-600 transition-all flex items-center gap-2"
              >
                了解更多
                <ChevronDown size={18} />
              </button>
            </div>
          </motion.div>

          {/* Hero Visual - 工作流演示 */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="mt-16 relative"
          >
            <div className="relative backdrop-blur-xl bg-slate-900/70 border border-slate-800 rounded-2xl p-8 shadow-2xl overflow-hidden group hover:border-cyan-500/30 transition-all duration-500">
              {/* 边角装饰 - 与登录页一致 */}
              <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-cyan-500/30 rounded-tl-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />
              <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-cyan-500/30 rounded-tr-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />
              <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-cyan-500/30 rounded-bl-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-cyan-500/30 rounded-br-lg pointer-events-none group-hover:border-cyan-400 group-hover:w-10 group-hover:h-10 transition-all" />

              <div className="absolute -top-px left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-cyan-500 to-transparent" />

              {/* Mock Interface */}
              <div className="flex gap-6">
                {/* Left Panel - Novel */}
                <div className="flex-1 bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                  <div className="flex items-center gap-2 mb-3">
                    <BookOpen size={16} className="text-blue-400" />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">小说原文</span>
                  </div>
                  <div className="space-y-2">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="h-3 bg-slate-700/50 rounded" style={{ width: `${100 - i * 15}%` }} />
                    ))}
                  </div>
                </div>

                {/* Center - AI Processing */}
                <div className="flex flex-col items-center justify-center px-4">
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-2 shadow-lg shadow-cyan-500/30"
                  >
                    <Brain size={24} className="text-white" />
                  </motion.div>
                  <div className="flex gap-1">
                    {[0, 1, 2].map(i => (
                      <motion.div
                        key={i}
                        className="w-1.5 h-1.5 bg-cyan-400 rounded-full"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1, delay: i * 0.2, repeat: Infinity }}
                      />
                    ))}
                  </div>
                </div>

                {/* Right Panel - Script */}
                <div className="flex-1 bg-slate-800/50 rounded-xl p-4 border border-cyan-500/20">
                  <div className="flex items-center gap-2 mb-3">
                    <Film size={16} className="text-cyan-400" />
                    <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">剧本输出</span>
                  </div>
                  <div className="space-y-2">
                    <div className="text-xs text-slate-500 font-mono">场景 1 - 内景/咖啡馆/日</div>
                    {[1, 2].map(i => (
                      <div key={i} className="h-3 bg-cyan-500/20 rounded" style={{ width: `${90 - i * 20}%` }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-6 border-y border-slate-800/50 bg-slate-900/30 relative z-10">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="text-center"
              >
                <div className="text-4xl font-black bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 bg-clip-text text-transparent mb-2">
                  {stat.value}
                </div>
                <div className="text-sm text-slate-500 font-medium">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow Section */}
      <section className="py-24 px-6 relative z-10">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              四步完成
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500"> 专业剧本</span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              简洁高效的工作流程，让您专注于创意本身
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {workflow.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="relative group"
              >
                <div className="backdrop-blur-xl bg-slate-900/70 border border-slate-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all h-full">
                  <div className="text-5xl font-black text-slate-800 mb-4">{item.step}</div>
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform border border-slate-700/50">
                    <item.icon size={24} className="text-cyan-400" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">{item.title}</h3>
                  <p className="text-sm text-slate-500">{item.desc}</p>
                </div>
                {i < 3 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 w-6 h-px bg-gradient-to-r from-slate-700 to-transparent" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-6 bg-slate-900/30 relative z-10">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              强大的
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500"> 核心功能</span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              专为编剧和内容创作者打造的 AI 工具集
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                onMouseEnter={() => setActiveFeature(i)}
                className={`group backdrop-blur-xl bg-slate-900/70 border rounded-2xl p-6 transition-all cursor-pointer ${
                  activeFeature === i ? 'border-cyan-500/50 shadow-lg shadow-cyan-500/10' : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-all border ${
                  activeFeature === i
                    ? 'bg-gradient-to-br from-blue-500 to-cyan-500 border-transparent'
                    : 'bg-slate-800 border-slate-700/50'
                }`}>
                  <feature.icon size={24} className={activeFeature === i ? 'text-white' : 'text-slate-400'} />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">{feature.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Agent System Section */}
      <section className="py-24 px-6 relative z-10">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-black mb-6">
                多 Agent
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500"> 智能协作</span>
              </h2>
              <p className="text-slate-400 mb-8 leading-relaxed">
                不同于传统单一 AI，我们采用多 Agent 协作架构。
                每个 Agent 专注于特定领域，协同工作产出更专业的剧本。
              </p>
              <div className="space-y-4">
                {[
                  { name: '剧情架构师', desc: '宏观剧情结构规划与节奏控制' },
                  { name: '角色心理师', desc: '分析角色动机，确保行为逻辑' },
                  { name: '对白润色师', desc: '优化人物对白，增加潜台词' },
                  { name: '连贯性守卫', desc: '检查时间线、道具和逻辑漏洞' }
                ].map((agent, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-start gap-3"
                  >
                    <CheckCircle size={20} className="text-cyan-400 mt-0.5 shrink-0" />
                    <div>
                      <div className="font-bold text-white">{agent.name}</div>
                      <div className="text-sm text-slate-500">{agent.desc}</div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="relative"
            >
              <div className="backdrop-blur-xl bg-slate-900/70 border border-slate-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all">
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { icon: Brain, label: '架构师', color: 'blue' },
                    { icon: Users, label: '心理师', color: 'purple' },
                    { icon: FileText, label: '润色师', color: 'pink' },
                    { icon: Shield, label: '守卫', color: 'green' }
                  ].map((item, i) => (
                    <motion.div
                      key={i}
                      animate={{ y: [0, -5, 0] }}
                      transition={{ duration: 2, delay: i * 0.3, repeat: Infinity }}
                      className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center"
                    >
                      <div className={`w-10 h-10 rounded-lg bg-${item.color}-500/20 flex items-center justify-center mx-auto mb-2`}>
                        <item.icon size={20} className={`text-${item.color}-400`} />
                      </div>
                      <div className="text-xs font-bold text-slate-400">{item.label}</div>
                    </motion.div>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-center gap-2 text-xs text-slate-500">
                  <Layers size={14} />
                  <span>协同工作中...</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 bg-gradient-to-b from-slate-900/50 to-slate-950 relative z-10">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-black mb-6">
              准备好开始您的
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500"> 创作之旅</span>
              了吗？
            </h2>
            <p className="text-slate-400 mb-10 max-w-xl mx-auto">
              立即注册，免费体验 AI 剧本创作的全新方式。
              让技术为创意赋能，让故事更精彩。
            </p>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/register')}
              className="group relative overflow-hidden px-10 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-all text-lg"
            >
              <div className="absolute inset-0 w-1/2 h-full bg-white/10 -skew-x-12 -translate-x-full group-hover:translate-x-[200%] transition-transform duration-700 ease-in-out" />
              <span className="relative z-10">免费开始使用</span>
            </motion.button>
            <p className="mt-4 text-sm text-slate-600">
              无需信用卡 · 即刻开始
            </p>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-slate-800/50 relative z-10">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <Film size={16} className="text-white" />
              </div>
              <span className="font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">AI ScriptFlow</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-slate-500">
              <button className="hover:text-cyan-400 transition-colors">用户协议</button>
              <span className="w-1 h-1 rounded-full bg-slate-700" />
              <button className="hover:text-cyan-400 transition-colors">隐私政策</button>
              <span className="w-1 h-1 rounded-full bg-slate-700" />
              <button className="hover:text-cyan-400 transition-colors">帮助中心</button>
            </div>
            <div className="text-sm text-slate-600 font-mono">
              © 2026 AI ScriptFlow · v1.0.0
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
