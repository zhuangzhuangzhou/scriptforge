import React, { useState, useEffect } from 'react';
import { Plus, MoreVertical, FileText, Clock, CheckCircle2, Trash2, Sparkles, Loader2, CheckCheck, Upload, Book, Coffee, Feather, Music, Camera, Gamepad2, Ghost, Rocket, Zap, Crown, Gem, Palette, Sword, Flame, Skull, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import CreateProjectModal from '../../components/modals/CreateProjectModal';
import { UserTier } from '../../types';
import { projectApi, USE_MOCK } from '../../services/api';
import { message } from 'antd';

interface DashboardProps {
  userTier: UserTier;
}

interface ProtocolModalProps {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

const ProtocolModal: React.FC<ProtocolModalProps> = ({ title, isOpen, onClose, children }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-950/80 backdrop-blur-md"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative bg-slate-900/90 border border-slate-800 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl"
          >
            <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/50">
              <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <div className="w-1.5 h-6 bg-cyan-500 rounded-full" />
                {title}
              </h2>
              <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors p-2 hover:bg-slate-800 rounded-xl">
                <X size={20} />
              </button>
            </div>

            <div className="p-8 max-h-[65vh] overflow-y-auto custom-scrollbar text-slate-300 text-sm leading-relaxed font-light">
              {children}
            </div>

            <div className="p-4 border-t border-slate-800/50 bg-slate-900/30 flex justify-end">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold rounded-lg transition-all uppercase tracking-widest border border-slate-700/50"
              >
                Close / 关闭
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

const PROJECT_STYLES = [
  { icon: Book, color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  { icon: Coffee, color: 'text-amber-400', bgColor: 'bg-amber-500/10' },
  { icon: Feather, color: 'text-emerald-400', bgColor: 'bg-emerald-500/10' },
  { icon: Music, color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  { icon: Camera, color: 'text-pink-400', bgColor: 'bg-pink-500/10' },
  { icon: Gamepad2, color: 'text-indigo-400', bgColor: 'bg-indigo-500/10' },
  { icon: Ghost, color: 'text-slate-400', bgColor: 'bg-slate-500/10' },
  { icon: Rocket, color: 'text-orange-400', bgColor: 'bg-orange-500/10' },
  { icon: Zap, color: 'text-yellow-400', bgColor: 'bg-yellow-500/10' },
  { icon: Crown, color: 'text-yellow-500', bgColor: 'bg-yellow-600/10' },
  { icon: Gem, color: 'text-cyan-400', bgColor: 'bg-cyan-500/10' },
  { icon: Palette, color: 'text-rose-400', bgColor: 'bg-rose-500/10' },
  { icon: Sword, color: 'text-red-400', bgColor: 'bg-red-500/10' },
  { icon: Flame, color: 'text-orange-600', bgColor: 'bg-orange-700/10' },
  { icon: Skull, color: 'text-gray-400', bgColor: 'bg-gray-500/10' },
];

const getProjectStyle = (id: string) => {
  const sum = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return PROJECT_STYLES[sum % PROJECT_STYLES.length];
};

const Dashboard: React.FC<DashboardProps> = ({ userTier }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showUserAgreement, setShowUserAgreement] = useState(false);
  const [showPrivacyPolicy, setShowPrivacyPolicy] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const navigate = useNavigate();

  // 获取真实项目列表
  const fetchProjects = async () => {
    try {
      setLoading(true);
      const res = await projectApi.getProjects();
      setProjects(res.data);
    } catch (err) {
      message.error('获取项目列表失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = () => {
    fetchProjects(); // 刷新列表
    setIsModalOpen(false);
  };

  const handleOpen = (project: any) => {
    navigate(`/workspace/${project.id}`);
  };

  const getStatusConfig = (status: string) => {
    const configs: Record<string, any> = {
      draft: { label: '草稿', color: 'text-slate-400', icon: FileText, bgColor: 'bg-slate-500/10', borderColor: 'border-slate-500/20' },
      uploaded: { label: '已上传', color: 'text-blue-400', icon: Upload, bgColor: 'bg-blue-500/10', borderColor: 'border-blue-500/20' },
      ready: { label: '已拆分', color: 'text-indigo-400', icon: CheckCircle2, bgColor: 'bg-indigo-500/10', borderColor: 'border-indigo-500/20' },
      parsing: { label: '剧情分析中', color: 'text-purple-400', icon: Sparkles, bgColor: 'bg-purple-500/10', borderColor: 'border-purple-500/20' },
      scripting: { label: '剧本生成中', color: 'text-pink-400', icon: Sparkles, bgColor: 'bg-pink-500/10', borderColor: 'border-pink-500/20', animate: true },
      completed: { label: '已完成', color: 'text-green-400', icon: CheckCheck, bgColor: 'bg-green-500/10', borderColor: 'border-green-500/20' },
    };
    return configs[status] || { label: status, color: 'text-slate-500', icon: FileText, bgColor: 'bg-slate-800', borderColor: 'border-slate-700' };
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (window.confirm('确定要永久删除该项目吗？此操作不可撤销。')) {
      try {
        await projectApi.deleteProject(id);
        message.success('项目已删除');
        setProjects(projects.filter(p => p.id !== id));
      } catch (err) {
        message.error('删除项目失败');
      }
    }
    setActiveMenuId(null);
  };

  if (loading && !USE_MOCK) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
            <Loader2 size={40} className="animate-spin text-cyan-500" />
            <p className="text-slate-500 font-mono text-xs tracking-widest">LOADING CORE DATA...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-10 max-w-7xl mx-auto h-full flex flex-col" onClick={() => setActiveMenuId(null)}>
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-white mb-2 tracking-tight">项目管理 <span className="text-slate-600 font-mono text-sm ml-2 font-normal">/ Projects</span></h1>
          <p className="text-slate-400 text-sm">管理您的小说改编项目，查看进度与历史版本。</p>
        </div>
        
        <motion.button 
          whileHover={{ scale: 1.02, translateY: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setIsModalOpen(true)}
          className="relative group overflow-hidden px-8 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold shadow-[0_0_20px_rgba(37,99,235,0.3)] transition-all"
        >
          <div className="absolute inset-0 w-1/2 h-full bg-white/10 -skew-x-12 -translate-x-full group-hover:translate-x-[200%] transition-transform duration-700 ease-in-out" />
          <div className="flex items-center gap-2 relative z-10">
            <Plus size={20} strokeWidth={3} />
            <span className="tracking-wide">新建改编项目</span>
            <Sparkles size={16} className="text-cyan-200 animate-pulse" />
          </div>
        </motion.button>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto min-h-0 pr-2 custom-scrollbar">
        {projects.length === 0 ? (
            <div className="h-64 border-2 border-dashed border-slate-800 rounded-3xl flex flex-col items-center justify-center text-slate-600 gap-4">
                <FileText size={48} opacity={0.2} />
                <p className="text-sm">暂无项目，点击右上角开始创作</p>
            </div>
        ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-10">
                {projects.map((project, index) => {
                  const style = getProjectStyle(project.id);
                  const ProjectIcon = style.icon;
                  return (
                    <motion.div
                        key={project.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        onClick={() => handleOpen(project)}
                        className="group bg-slate-900/40 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-6 cursor-pointer hover:bg-slate-800/60 transition-all duration-300 ease-out relative overflow-hidden shadow-xl hover:shadow-[0_20px_40px_-15px_rgba(99,102,241,0.2)] hover:-translate-y-1"
                    >
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                        <div className="flex justify-between items-start mb-6">
                        <div className="flex items-center gap-4">
                            <div className={`w-12 h-12 rounded-xl ${style.bgColor} flex items-center justify-center ${style.color} group-hover:scale-110 transition-all`}>
                                <ProjectIcon size={24} />
                            </div>
                            <div>
                                <h3 className="font-bold text-white group-hover:text-indigo-400 transition-colors tracking-tight text-lg truncate max-w-[150px]">{project.name}</h3>
                                <span className="text-[10px] uppercase font-black text-slate-500 border border-slate-800 rounded px-2 py-0.5 mt-1 inline-block">{project.novel_type || '未分类'}</span>
                            </div>
                        </div>

                        <div className="relative">
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenuId(activeMenuId === project.id ? null : project.id);
                                }}
                                className="text-slate-600 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition-all"
                            >
                                <MoreVertical size={18} />
                            </button>

                            <AnimatePresence>
                                {activeMenuId === project.id && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.95, y: -10 }}
                                        animate={{ opacity: 1, scale: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.95, y: -10 }}
                                        className="absolute right-0 mt-2 w-32 bg-slate-900 border border-slate-700 shadow-2xl rounded-xl z-50 overflow-hidden backdrop-blur-xl"
                                    >
                                        <button
                                            onClick={(e) => handleDelete(e, project.id)}
                                            className="w-full px-4 py-3 text-xs font-bold text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors"
                                        >
                                            <Trash2 size={14} /> 删除项目
                                        </button>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                        </div>

                        <div className="space-y-5">
                            <div>
                                <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">
                                    <span>处理进度</span>
                                    <span className="bg-gradient-to-r from-pink-500 to-violet-500 bg-clip-text text-transparent font-black font-mono">{project.processed_chapters}/{project.total_chapters} 章</span>
                                </div>
                                <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden shadow-inner border border-slate-800/50">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${(project.processed_chapters / (project.total_chapters || 1)) * 100}%` }}
                                        className="h-full bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-400 rounded-full"
                                    />
                                </div>
                            </div>

                            <div className="flex items-center justify-between pt-5 border-t border-slate-800/50">
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase">
                                    <Clock size={12} />
                                    <span>{new Date(project.updated_at).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })}</span>
                                </div>
                                {(() => {
                                    const config = getStatusConfig(project.status);
                                    const StatusIcon = config.icon;
                                    return (
                                        <div className={`flex items-center gap-1.5 text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-tighter border ${config.bgColor} ${config.color} ${config.borderColor}`}>
                                            <StatusIcon size={12} />
                                            {config.label}
                                        </div>
                                    );
                                })()}
                            </div>
                        </div>
                    </motion.div>
                  );
                })}
            </div>
        )}
      </div>

      <footer className="mt-auto pt-6 border-t border-slate-900 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] text-slate-500 uppercase font-bold tracking-widest shrink-0">
        <div className="flex items-center gap-6">
            <button onClick={() => setShowUserAgreement(true)} className="hover:text-cyan-400 transition-colors">用户协议</button>
            <button onClick={() => setShowPrivacyPolicy(true)} className="hover:text-cyan-400 transition-colors">隐私政策</button>
        </div>
        <div className="flex items-center gap-4">
            <span>© 2026 AI ScriptFlow Core</span>
            <div className="w-1 h-1 rounded-full bg-slate-800" />
            <span className="text-slate-400">Release v2.4.0-Final</span>
        </div>
      </footer>

      {isModalOpen && (
        <CreateProjectModal 
            onClose={() => setIsModalOpen(false)} 
            onSubmit={handleCreateProject}
            userTier={userTier}
        />
      )}

      <ProtocolModal
        title="用户协议"
        isOpen={showUserAgreement}
        onClose={() => setShowUserAgreement(false)}
      >
        <div className="space-y-6">
          <p>欢迎使用 AI ScriptFlow。在使用我们的服务之前，请仔细阅读以下条款：</p>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">01.</span> 服务说明
            </h4>
            <p className="text-slate-400">本平台提供基于 AI 的剧本改编与处理服务，旨在辅助创作者提高效率。生成内容仅供参考。</p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">02.</span> 账号责任
            </h4>
            <p className="text-slate-400">用户应妥善保管账号密码，并对该账号下的所有行为承担法律责任。</p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">03.</span> 内容所有权
            </h4>
            <p className="text-slate-400">用户通过本平台生成的内容，其版权归属于生成该内容的用户所有，但用户需确保原始素材（如小说原文）的合法授权。</p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">04.</span> 免责声明
            </h4>
            <p className="text-slate-400">由于 AI 技术的局限性，我们不对生成内容的准确性、完整性或适用性做任何明示或暗示的保证。</p>
          </div>
        </div>
      </ProtocolModal>

      <ProtocolModal
        title="隐私政策"
        isOpen={showPrivacyPolicy}
        onClose={() => setShowPrivacyPolicy(false)}
      >
        <div className="space-y-6">
          <p>我们非常重视您的隐私保护，以下是我们的隐私处理原则：</p>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">01.</span> 数据收集
            </h4>
            <p className="text-slate-400">我们仅收集维持服务运行所必需的信息，如账号名、邮箱及为了优化处理效果而上传的文本片段。</p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">02.</span> 数据用途
            </h4>
            <p className="text-slate-400">收集的数据主要用于提供核心服务、改进 AI 模型的处理质量以及向您发送必要的系统通知。</p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">03.</span> 数据安全
            </h4>
            <p className="text-slate-400">我们采用行业标准的加密技术存储您的数据，并严格限制内部人员对生产数据的访问权限。</p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-2 flex items-center gap-2">
              <span className="text-cyan-500 text-xs font-mono">04.</span> 第三方共享
            </h4>
            <p className="text-slate-400">除非法律要求，我们不会将您的个人数据出售或共享给第三方公司进行营销活动。</p>
          </div>
        </div>
      </ProtocolModal>
    </div>
  );
};

export default Dashboard;
