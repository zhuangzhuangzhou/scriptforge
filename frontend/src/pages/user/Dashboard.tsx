import React, { useState, useEffect } from 'react';
import { Plus, Search, MoreVertical, FileText, Clock, PlayCircle, CheckCircle2, Trash2, Sparkles, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import CreateProjectModal from '../../components/modals/CreateProjectModal';
import { UserTier } from '../../types';
import { projectApi, USE_MOCK } from '../../services/api';
import { message } from 'antd';

interface DashboardProps {
  onOpenProject: (project: any) => void;
  userTier: UserTier;
}

const Dashboard: React.FC<DashboardProps> = ({ onOpenProject, userTier }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
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
    onOpenProject(project);
    navigate('/workspace');
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
                {projects.map((project, index) => (
                <motion.div
                    key={project.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => handleOpen(project)}
                    className="group bg-slate-900/40 border border-slate-800 hover:border-cyan-500/40 rounded-2xl p-6 cursor-pointer hover:bg-slate-800/40 transition-all duration-300 relative overflow-hidden shadow-xl"
                >
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    
                    <div className="flex justify-between items-start mb-6">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-cyan-500 group-hover:scale-110 transition-all">
                            <FileText size={24} />
                        </div>
                        <div>
                            <h3 className="font-bold text-white group-hover:text-cyan-400 transition-colors tracking-tight text-lg truncate max-w-[150px]">{project.name}</h3>
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
                                <span>Progress</span>
                                <span className="text-cyan-500 font-mono">{project.processed_chapters}/{project.total_chapters} CH</span>
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
                                <span>{new Date(project.updated_at).toLocaleDateString()}</span>
                            </div>
                            <div className={`flex items-center gap-1.5 text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-tighter border ${
                                project.status === 'completed' ? 'bg-green-500/5 text-green-500 border-green-500/20' :
                                project.status === 'processing' ? 'bg-blue-500/5 text-blue-400 border-blue-500/20' :
                                'bg-slate-800 text-slate-500 border-slate-700'
                            }`}>
                                {project.status}
                            </div>
                        </div>
                    </div>
                </motion.div>
                ))}
            </div>
        )}
      </div>

      <footer className="mt-auto pt-6 border-t border-slate-900 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] text-slate-500 uppercase font-bold tracking-widest shrink-0">
        <div className="flex items-center gap-6">
            <button className="hover:text-cyan-400 transition-colors">User Agreement</button>
            <button className="hover:text-cyan-400 transition-colors">Privacy Policy</button>
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
    </div>
  );
};

export default Dashboard;
