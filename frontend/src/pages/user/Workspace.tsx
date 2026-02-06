import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Settings, FileEdit, Play, Download, RefreshCw,
  BrainCircuit, Layers, Activity, Lightbulb, Swords, Users, Cpu,
  Plus, Terminal, CheckCircle2, Eye, LayoutTemplate,
  BookText, Save, Sparkles, Loader2, ThumbsUp, FileCheck, Search, X, Trash2, BookOpen,
  Hash, Type, Sliders, Upload, Database, SplitSquareVertical,
  CircleDashed, RotateCcw
} from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import ConsoleLogger, { LogEntry } from '../../components/ConsoleLogger';
import AICopilot from '../../components/AICopilot';
import AgentConfigModal from '../../components/modals/AgentConfigModal';
import { UserTier } from '../../types';
import { projectApi } from '../../services/api';
import { message, Modal } from 'antd';

interface ProjectWorkspaceProps {
  userTier: UserTier;
}

type Tab = 'CONFIG' | 'SOURCE' | 'AGENTS' | 'SKILLS' | 'PLOT' | 'SCRIPT';

// --- Mock Data Generators ---
const mockLogs: LogEntry[] = [
    { id: '1', timestamp: '10:00:01', type: 'info', message: 'Initializing breakdown agent...' },
    { id: '2', timestamp: '10:00:02', type: 'thinking', message: 'Reading context: Chapter 1-5...' },
    { id: '3', timestamp: '10:00:05', type: 'thinking', message: 'Identifying conflict nodes in scene 3...' },
    { id: '4', timestamp: '10:00:08', type: 'success', message: 'Extracted 3 core conflicts.' },
    { id: '5', timestamp: '10:00:09', type: 'info', message: 'Formatting output...' }
];

const mockChapters = Array.from({ length: 45 }, (_, i) => ({
    id: i + 1,
    title: `第 ${i + 1} 章：${['风起云涌', '暗夜潜行', '迷雾追踪', '生死时速', '真相大白'][i % 5]}`,
    content: `这是第 ${i + 1} 章的原文内容...\n\n在一个风雨交加的夜晚，街道上空无一人。只有路灯发出昏黄的光芒，映照着湿漉漉的地面。\n\n张伟紧了紧身上的大衣，加快了脚步。他感觉身后似乎有一双眼睛地盯着他，那种如芒在背的感觉让他不寒而栗。\n\n"谁在那里？" 他猛地回头，却只看到一只黑猫从巷口窜过。\n\n他深吸了一口气，继续向前走去。手中的公文包里装着一份绝密文件，这份文件关系到整个组织的生死存亡。\n\n突然，一辆黑色轿车从街角冲了出来，刺眼的远光灯让他睁不开眼...\n\n(此处为小说原始文本示例，支持长文本滚动阅读，模拟真实的阅读体验。)` ,
    status: i < 15 ? 'processed' : 'unprocessed' 
}));

const mockPlots = [
    { id: 1, batch: 1, title: '第一集：暗流涌动', summary: '主人公发现档案室的异常，初步接触核心谜题。', conflicts: ['档案缺失', '上级施压'], hooks: '发现神秘纸条', tension: 75 },
    { id: 2, batch: 1, title: '第二集：初次交锋', summary: '反派登场，主人公在调查过程中遭遇第一次阻拦。', conflicts: ['车辆跟踪', '证人失踪'], hooks: '目击者死亡', tension: 85 },
    { id: 3, batch: 1, title: '第三集：迷雾重重', summary: '线索指向了十年前的旧案，所有人都开始变得可疑。', conflicts: ['信任危机', '虚假线索'], hooks: '老照片', tension: 65 },
    { id: 4, batch: 2, title: '第四集：绝地反击', summary: '主角团队陷入陷阱，必须在有限时间内找到出路。', conflicts: ['时间紧迫', '内部叛徒'], hooks: '定时炸弹', tension: 90 },
    { id: 5, batch: 2, title: '第五集：黎明之前', summary: '最终决战前的宁静，真相即将大白。', conflicts: ['黎明前的黑暗', '最后的抉择'], hooks: '录音笔', tension: 80 },
];

const mockEpisodes = [
    {
        id: 1,
        title: "第1集",
        subtitle: "治愈系游戏？",
        status: "APPROVED",
        wordCount: 831,
        content: `# 第1集：治愈系游戏？\n\n※ “来生”旧货商店，昏暗，堆满杂物\n\n△ 柜台后，店老板（满脸褶子）搬出一个沉重的黑色手提箱，重重砸在柜台上。\n【音效】嘭！灰尘飞扬。\n\n△ 店老板神秘兮兮：“年轻人，生活压力大？这款《治愈系人生》绝对适合你。画面温馨，治愈心灵，是深夜独处的最佳伴侣。”\n\n△ 韩非（25岁，颓废，黑眼圈）半信半疑地盯着手提箱。\n△ 他掏出一叠皱皱巴巴的钞票，拍在桌上。\n\n韩非：“只要能让我笑出来，什么都行。”\n\n---\n\n※ 出租屋，深夜，暴雨\n\n△ 窗外雷雨交加，闪电惨白。\n△ 韩非坐在电脑前，从箱子里取出一个仿佛由人骨打磨的游戏头盔。\n△ 头盔表面没有任何LOGO，只有一股透骨的冰凉。\n△ 指尖触碰头盔，一股寒意顺着手指钻入骨髓。\n\n【独白】被辞退，被封杀，连笑都不会了... 也许，这游戏真的能救我？\n\n△ 韩非深吸一口气，戴上头盔。\n△ “咔哒”一声，卡扣锁死。`,
        qcReport: {
            score: 98,
            status: "PASS",
            checks: [
                { title: "剧情还原度", items: ["剧本严格按照 <PlotPoints> 进行编写，无遗漏。", "关键细节（如“治愈系游戏”、“死鱼”）均准确还原。"] },
                { title: "节奏与结构", items: ["每集字数控制在500-800字范围内，符合要求。", "结构符合“起承转合”四段式，悬念设置得当。"] },
                { title: "视觉化风格", items: ["严格使用了符号（※、△、【音效】）。", "动作描写具体，画面感强。"] },
                { title: "格式规范", items: ["符合标准剧本格式要求。"] }
            ]
        }
    },
    {
        id: 2,
        title: "第2集",
        subtitle: "血色开端",
        status: "APPROVED",
        wordCount: 756,
        content: `# 第2集：血色开端\n\n※ 游戏大厅，阴冷，雾气弥漫...\n\n△ 韩非睁开眼，发现自己站在一个巨大的轮盘前。\n△ 轮盘上布满了狰狞的笑脸。`,
        qcReport: {
            score: 95,
            status: "PASS",
            checks: [
                { title: "剧情还原度", items: ["基本还原核心冲突。"] },
                { title: "节奏与结构", items: ["结尾钩子力度稍弱，建议加强。"] }
            ]
        }
    },
    { id: 3, title: "第3集", subtitle: "午夜凶铃", status: "APPROVED", wordCount: 810, content: "", qcReport: null },
    { id: 4, title: "第4集", subtitle: "看不见的客人", status: "GENERATING", wordCount: 0, content: "", qcReport: null },
    { id: 5, title: "第5集", subtitle: "生死抉择", status: "PENDING", wordCount: 0, content: "", qcReport: null },
    { id: 6, title: "第6集", subtitle: "黎明杀机", status: "PENDING", wordCount: 0, content: "", qcReport: null },
];

const initialAgents = [
    { id: 'a1', name: 'Narrative Architect', role: '剧情架构师', status: 'active', model: 'DeepNarrative-Pro', desc: '负责宏观剧情结构的规划与节奏控制。', temperature: 0.7, tools: ['knowledge_base'] },
    { id: 'a2', name: 'Character Psychologist', role: '角色心理师', status: 'active', model: 'Claude 3.5 Sonnet', desc: '分析角色动机，确保行为逻辑符合人设。', temperature: 0.8, tools: ['web_search'] },
    { id: 'a3', name: 'Dialogue Polisher', role: '对白润色师', status: 'inactive', model: 'GPT-4o', desc: '优化人物对白，增加潜台词和方言特色。', temperature: 0.9, tools: [] },
    { id: 'a4', name: 'Continuity Guard', role: '连贯性守卫', status: 'active', model: 'Gemini-1.5-Pro', desc: '检查前后文的时间线、道具和逻辑漏洞。', temperature: 0.2, tools: ['knowledge_base', 'code_interpreter'] },
];

const initialSkills = [
    { id: 's1', name: 'Conflict Radar', trigger: 'Scene Analysis', desc: '自动识别并强化场景中的戏剧冲突点。', prompt: 'Analyze the current scene for lack of conflict. If tension is below threshold, suggest an external obstacle...' },
    { id: 's2', name: 'Emotion Sync', trigger: 'Character Action', desc: '确保角色在不同场景间的情感逻辑连贯。', prompt: 'Trace the character\'s emotional state from the previous scene. Ensure their reaction to [Event] aligns with...' },
    { id: 's3', name: 'Visual Boost', trigger: 'Description Gen', desc: '将心理描写自动转化为镜头语言和动作。', prompt: 'Convert internal monologues into visual metaphors. Instead of "he felt sad", describe "he stared at the rain..."' },
];

// --- Subcomponents ---

const SidebarItem = ({ icon: Icon, label, active, onClick }: { icon: any, label: string, active: boolean, onClick: () => void }) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 border ${
      active 
        ? 'bg-gradient-to-r from-blue-600/20 to-cyan-600/20 text-cyan-400 border-cyan-500/20' 
        : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800'
    }`}
  >
    <Icon size={18} className={active ? 'text-cyan-400' : 'text-slate-500'} />
    <span className="truncate">{label}</span>
  </button>
);

const SectionTitle = ({ title, description }: { title: string, description: string }) => (
    <div className="mb-6">
        <h2 className="text-xl font-bold text-white mb-1">{title}</h2>
        <p className="text-sm text-slate-400">{description}</p>
    </div>
);

const StatCard = ({ icon: Icon, label, value, colorClass }: { icon: any, label: string, value: string | number, colorClass: string }) => (
    <div className="bg-slate-900/40 border border-slate-800 p-4 rounded-2xl flex items-center gap-4 group hover:border-slate-700 transition-all shadow-lg">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorClass} shadow-inner`}>
            <Icon size={20} />
        </div>
        <div>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</p>
            <p className="text-lg font-bold text-white font-mono">{value}</p>
        </div>
    </div>
);

const Workspace: React.FC<ProjectWorkspaceProps> = () => {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const [project, setProject] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [splitting, setSplitting] = useState(false);
    const [starting, setStarting] = useState(false);
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    const [activeTab, setActiveTab] = useState<Tab>('CONFIG');
    const [showConsole, setShowConsole] = useState(false);
    const [showCopilot, setShowCopilot] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>(mockLogs);
    const [isProcessing, setIsProcessing] = useState(false);

    // Form Data
    const [formData, setFormData] = useState({
        name: '',
        novel_type: '悬疑/惊悚',
        description: '',
        batch_size: 5,
        chapter_split_rule: 'auto',
        breakdown_model: 'DeepNarrative-Pro',
        script_model: 'Gemini-1.5-Pro'
    });

    // Config State
    const [agents, setAgents] = useState(initialAgents);
    const [selectedAgent, setSelectedAgent] = useState<any>(null);

    // Script Tab State
    const [selectedEpisodeId, setSelectedEpisodeId] = useState<number>(1);
    const selectedEpisode = mockEpisodes.find(ep => ep.id === selectedEpisodeId) || mockEpisodes[0];

    // Source Tab State
    const [selectedChapterId, setSelectedChapterId] = useState<number>(1);
    const selectedChapter = mockChapters.find(ch => ch.id === selectedChapterId) || mockChapters[0];

    const getStatusText = (status: string) => {
        const statusMap: Record<string, string> = {
            'draft': '草稿',
            'uploaded': '已上传',
            'ready': '就绪',
            'parsing': '解析中',
            'scripting': '生成中',
            'completed': '已完成',
            'failed': '失败'
        };
        return statusMap[status] || status;
    };

    // 获取项目数据
    useEffect(() => {
        const fetchProject = async () => {
            if (!projectId) {
                navigate('/dashboard');
                return;
            }
            try {
                setLoading(true);
                const res = await projectApi.getProject(projectId);
                if (res.data) {
                    setProject(res.data);
                    // 初始化表单数据
                    setFormData({
                        name: res.data.name || '',
                        novel_type: res.data.novel_type || '悬疑/惊悚',
                        description: res.data.description || '',
                        batch_size: res.data.batch_size || 5,
                        chapter_split_rule: res.data.chapter_split_rule || 'auto'
                    });
                } else {
                    message.error('项目不存在');
                    navigate('/dashboard');
                }
            } catch (err) {
                console.error('获取项目失败:', err);
                message.error('获取项目失败');
                navigate('/dashboard');
            } finally {
                setLoading(false);
            }
        };
        fetchProject();
    }, [projectId, navigate]);

    // 保存配置
    const handleSaveConfig = async () => {
        if (!projectId) return;
        setSaving(true);
        try {
            const res = await projectApi.updateProject(projectId, formData);
            if (res.data) {
                setProject(res.data);
                message.success('配置已保存');
            }
        } catch (err) {
            console.error('保存失败:', err);
            message.error('保存失败，请重试');
        } finally {
            setSaving(false);
        }
    };

    // 处理文件上传
    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file || !projectId) return;

        // 自动提取文件名（去掉扩展名）
        const fileNameWithoutExt = file.name.replace(/\.[^/.]+$/, "");

        Modal.confirm({
            title: '上传确认',
            content: `是否将项目名称更新为 "${fileNameWithoutExt}" 并上传文件？`,
            okText: '确定',
            cancelText: '仅上传',
            onOk: async () => {
                await performUpload(file, fileNameWithoutExt);
            },
            onCancel: async () => {
                await performUpload(file);
            }
        });
    };

    const performUpload = async (file: File, newName?: string) => {
        setUploading(true);
        try {
            if (newName) {
                await projectApi.updateProject(projectId!, { name: newName });
                setFormData(prev => ({ ...prev, name: newName }));
            }

            await projectApi.uploadFile(projectId!, file);
            message.success('文件上传成功');

            const res = await projectApi.getProject(projectId!);
            if (res.data) {
                setProject(res.data);
            }
        } catch (error) {
            console.error('上传文件失败:', error);
            message.error('上传文件失败，请重试');
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    // 触发文件选择
    const triggerFileUpload = () => {
        fileInputRef.current?.click();
    };

    // 智能拆分章节
    const handleSplit = async () => {
        if (!projectId) return;
        setSplitting(true);
        setIsProcessing(true);
        setShowConsole(true); // 开启控制台查看日志
        try {
            const res = await projectApi.splitChapters(projectId);
            if (res.data) {
                message.success(`拆分成功！共识别 ${res.data.total_chapters} 章`);
                // 刷新项目数据
                const p = await projectApi.getProject(projectId);
                if (p.data) setProject(p.data);
            }
        } catch (error) {
            console.error('拆分失败:', error);
            message.error('拆分失败，请检查文件格式或拆分规则');
        } finally {
            setSplitting(false);
            setIsProcessing(false);
        }
    };

    // 启动项目
    const handleStart = async () => {
        if (!projectId) return;
        setStarting(true);
        setIsProcessing(true);
        try {
            await projectApi.startProject(projectId);
            message.success('项目已启动，开始剧情分析...');
            // 刷新项目数据
            const p = await projectApi.getProject(projectId);
            if (p.data) {
                setProject(p.data);
                // 自动跳转到 PLOT 标签页
                setActiveTab('PLOT');
            }
        } catch (error) {
            console.error('启动失败:', error);
            message.error('启动失败，请重试');
        } finally {
            setStarting(false);
            setIsProcessing(false);
        }
    };

    // 显示加载状态
    if (loading) {
        return (
            <div className="h-full flex items-center justify-center bg-slate-950">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 size={40} className="animate-spin text-cyan-500" />
                    <p className="text-slate-500 font-mono text-xs tracking-widest">LOADING PROJECT...</p>
                </div>
            </div>
        );
    }

    if (!project) {
        return (
            <div className="h-full flex items-center justify-center bg-slate-950">
                <div className="flex flex-col items-center gap-4">
                    <p className="text-slate-500 font-mono text-xs">项目加载失败</p>
                </div>
            </div>
        );
    }

    // Status Tag Component for consistency
    const StatusTag = ({ status }: { status: 'processed' | 'unprocessed' }) => (
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold border transition-colors ${
            status === 'processed' 
            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' 
            : 'bg-slate-800 text-slate-500 border-slate-700'
        }`}>
            {status === 'processed' ? <CheckCircle2 size={10} /> : <CircleDashed size={10} />}
            {status === 'processed' ? '已拆解' : '未拆解'}
        </div>
    );

    // Render logic for different tabs
    const renderContent = () => {
        switch(activeTab) {
            case 'CONFIG':
                return (
                    <div className="flex flex-col lg:flex-row gap-6 h-full animate-in fade-in slide-in-from-bottom-4 duration-300">
                        {/* 左侧内容 - 68% */}
                        <div className="flex-1 lg:flex-[0.68] space-y-6 overflow-y-auto pr-2 custom-scrollbar">
                            {/* 统计卡片 */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                <StatCard
                                    icon={Hash}
                                    label="总章节数"
                                    value={`${project.total_chapters || 0} 章`}
                                    colorClass="bg-blue-500/10 text-blue-400"
                                />
                                <StatCard
                                    icon={Type}
                                    label="预估字数"
                                    value={`${project.total_words ? (project.total_words / 10000).toFixed(1) : '0'} 万字`}
                                    colorClass="bg-purple-500/10 text-purple-400"
                                />
                                <StatCard
                                    icon={CheckCircle2}
                                    label="已拆解章节"
                                    value={`${project.processed_chapters || 0} / ${project.total_chapters || 0}`}
                                    colorClass="bg-emerald-500/10 text-emerald-400"
                                />
                                <StatCard
                                    icon={Activity}
                                    label="当前状态"
                                    value={getStatusText(project.status)}
                                    colorClass="bg-cyan-500/10 text-cyan-400"
                                />
                            </div>

                            {/* 基础信息 */}
                            <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-slate-400 flex items-center gap-2"><BookOpen size={14}/> 小说名称</label>
                                        <input
                                            type="text"
                                            value={formData.name}
                                            onChange={(e) => setFormData({...formData, name: e.target.value})}
                                            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none transition-all"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-slate-400 flex items-center gap-2"><LayoutTemplate size={14}/> 小说类型</label>
                                        <select
                                            value={formData.novel_type}
                                            onChange={(e) => setFormData({...formData, novel_type: e.target.value})}
                                            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                                        >
                                            <option value="悬疑惊悚">悬疑惊悚</option>
                                            <option value="都市言情">都市言情</option>
                                            <option value="玄幻奇幻">玄幻奇幻</option>
                                            <option value="武侠仙侠">武侠仙侠</option>
                                            <option value="科幻末世">科幻末世</option>
                                            <option value="历史军事">历史军事</option>
                                            <option value="游戏竞技">游戏竞技</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-slate-400 flex items-center gap-2"><FileEdit size={14}/> 小说简介</label>
                                    <textarea
                                        rows={5}
                                        className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 text-sm text-slate-300 focus:ring-1 focus:ring-cyan-500 outline-none resize-none leading-relaxed"
                                        value={formData.description}
                                        onChange={(e) => setFormData({...formData, description: e.target.value})}
                                        placeholder="请输入小说简介..."
                                    />
                                </div>
                            </div>

                            {/* 配置卡片 (移除源文件卡片，改为3列) */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
                                    <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider"><Sliders size={14} className="text-cyan-400"/> 核心逻辑</h3>
                                    <div className="space-y-2">
                                        <label className="text-[10px] text-slate-400 uppercase font-bold">拆剧批次</label>
                                        <input
                                            type="number"
                                            value={formData.batch_size}
                                            onChange={(e) => setFormData({...formData, batch_size: parseInt(e.target.value) || 5})}
                                            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:ring-1 focus:ring-cyan-500 outline-none"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] text-slate-400 uppercase font-bold">章节拆分规则</label>
                                        <select
                                            value={typeof formData.chapter_split_rule === 'string' ? formData.chapter_split_rule : 'custom'}
                                            onChange={(e) => setFormData({...formData, chapter_split_rule: e.target.value})}
                                            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                                        >
                                            <option value="auto">智能识别 (第X章)</option>
                                            <option value="blank_line">空行拆分</option>
                                            <option value="custom">自定义正则</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
                                    <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider"><BrainCircuit size={14} className="text-purple-400"/> 剧情拆解模型</h3>
                                    <div className="space-y-2">
                                        <label className="text-[10px] text-slate-400 uppercase font-bold">Breakdown Model</label>
                                        <select className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-cyan-500 outline-none"><option>DeepNarrative-Pro</option><option>GPT-4o</option></select>
                                    </div>
                                </div>
                                <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
                                    <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider"><Cpu size={14} className="text-indigo-400"/> 剧集生成模型</h3>
                                    <div className="space-y-2">
                                        <label className="text-[10px] text-slate-400 uppercase font-bold">Script Model</label>
                                        <select className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-cyan-500 outline-none"><option>Gemini-1.5-Pro</option><option>GPT-4o</option></select>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 右侧内容 - 32% - 小说源文件管理 */}
                        <div className="flex-1 lg:flex-[0.32] bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col gap-6 h-fit lg:h-auto relative overflow-hidden">
                            {/* 隐藏的文件输入框 */}
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileUpload}
                                className="hidden"
                                accept=".txt,.docx,.pdf,.md"
                            />

                            {/* 标题 */}
                            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3 uppercase tracking-wider mb-2">
                                <Database size={16} className="text-emerald-400"/> 小说源文件
                            </h3>

                            {/* 内容区域：根据是否有文件显示不同状态 */}
                            {!project.original_file_name ? (
                                /* 未上传状态 */
                                <div
                                    onClick={triggerFileUpload}
                                    className="flex-1 min-h-[300px] border-2 border-dashed border-slate-700 hover:border-emerald-500/50 rounded-xl flex flex-col items-center justify-center gap-4 cursor-pointer group transition-all bg-slate-950/30 hover:bg-slate-900/50"
                                >
                                    {uploading ? (
                                        <div className="flex flex-col items-center gap-3">
                                            <Loader2 size={32} className="animate-spin text-emerald-500" />
                                            <p className="text-xs text-emerald-500 font-bold animate-pulse">正在上传文件...</p>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="w-16 h-16 rounded-full bg-slate-800 group-hover:bg-emerald-500/10 flex items-center justify-center transition-colors">
                                                <Upload size={24} className="text-slate-400 group-hover:text-emerald-400 transition-colors" />
                                            </div>
                                            <div className="text-center">
                                                <p className="text-sm font-bold text-slate-300 group-hover:text-white transition-colors">点击上传小说文件</p>
                                                <p className="text-xs text-slate-500 mt-1">支持 .txt, .docx, .pdf 格式</p>
                                            </div>
                                        </>
                                    )}
                                </div>
                            ) : (
                                /* 已上传状态 */
                                <>
                                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 flex flex-col items-center gap-4 group hover:border-emerald-500/30 transition-all">
                                        <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 shadow-lg group-hover:scale-110 transition-transform">
                                            <BookText size={32} className="text-emerald-400" />
                                        </div>
                                        <div className="text-center w-full">
                                            <p className="text-sm font-bold text-white truncate px-2" title={project.original_file_name}>{project.original_file_name}</p>
                                            <p className="text-xs text-slate-500 mt-1 font-mono">
                                                {project.original_file_size ? (project.original_file_size / 1024 / 1024).toFixed(2) : '0.00'} MB
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-2 text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded-full border border-emerald-500/20">
                                            <CheckCircle2 size={12} /> 文件校验通过
                                        </div>
                                    </div>

                                    <div className="flex flex-col gap-3 mt-auto">
                                        {/* 根据状态显示主操作按钮 */}
                                        {project.status === 'uploaded' && (
                                            <button
                                                onClick={handleSplit}
                                                disabled={splitting}
                                                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-bold shadow-lg shadow-emerald-900/20 flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {splitting ? <Loader2 size={18} className="animate-spin" /> : <SplitSquareVertical size={18} />}
                                                {splitting ? '正在拆分...' : '开始智能拆分'}
                                            </button>
                                        )}

                                        {project.status === 'ready' && (
                                            <div className="w-full py-3 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-xl font-bold flex flex-col items-center justify-center gap-1 text-xs">
                                                <span className="flex items-center gap-2"><CheckCircle2 size={14}/> 章节拆分完成</span>
                                                <span className="opacity-70">请点击顶部 "项目启动" 进入下一步</span>
                                            </div>
                                        )}

                                        {(project.status === 'parsing' || project.status === 'scripting' || project.status === 'completed') && (
                                            <div className="w-full py-3 bg-slate-800 text-slate-500 rounded-xl font-bold flex items-center justify-center gap-2 text-xs cursor-not-allowed">
                                                <CheckCircle2 size={14}/> 源文件已锁定
                                            </div>
                                        )}

                                        {/* 辅助操作按钮 (仅在 uploaded 或 ready 状态下允许修改) */}
                                        {(project.status === 'uploaded' || project.status === 'ready') && (
                                            <div className="grid grid-cols-2 gap-3">
                                                <button
                                                    onClick={triggerFileUpload}
                                                    disabled={uploading || splitting}
                                                    className="py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                                                >
                                                    {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                                                    重新上传
                                                </button>
                                                {project.status === 'ready' ? (
                                                    <button
                                                        onClick={handleSplit}
                                                        disabled={splitting}
                                                        className="py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                                                    >
                                                        <RefreshCw size={14} /> 重新拆分
                                                    </button>
                                                ) : (
                                                    <button className="py-2.5 bg-slate-800 hover:bg-red-900/20 text-slate-300 hover:text-red-400 border border-slate-700 hover:border-red-500/30 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2">
                                                        <Trash2 size={14} /> 删除文件
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </div>

                                    <div className="bg-slate-800/30 rounded-xl p-4 text-[10px] text-slate-500 leading-relaxed border border-slate-800/50">
                                        <p className="flex gap-2"><Lightbulb size={12} className="text-amber-400 shrink-0"/> <span>重新上传将覆盖现有文件，并建议重新执行拆分流程。</span></p>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                );
            case 'SOURCE':
                 return (
                    <div className="h-full flex gap-0 animate-in fade-in slide-in-from-bottom-4 duration-300 overflow-hidden bg-slate-950">
                        {/* LEFT COLUMN: Chapter List */}
                        <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl">
                            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/50 backdrop-blur">
                                <h3 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
                                    章节目录
                                    <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700 font-mono">共 {mockChapters.length} 章</span>
                                </h3>
                                <div className="flex gap-2">
                                    <Search size={16} className="text-slate-500 hover:text-white cursor-pointer transition-colors" />
                                </div>
                            </div>
                            
                            <div className="flex-1 overflow-y-auto divide-y divide-slate-800/30 no-scrollbar pb-16">
                                {mockChapters.map(ch => (
                                    <div 
                                        key={ch.id} 
                                        onClick={() => setSelectedChapterId(ch.id)}
                                        className={`px-5 py-4 cursor-pointer transition-all flex flex-col gap-2 group ${
                                            selectedChapterId === ch.id 
                                            ? 'bg-cyan-500/10 border-l-4 border-l-cyan-500 shadow-inner' 
                                            : 'hover:bg-slate-800/50 border-l-4 border-l-transparent'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className={`text-[10px] font-black uppercase tracking-widest transition-colors ${selectedChapterId === ch.id ? 'text-cyan-400' : 'text-slate-500'}`}>
                                                Chapter {String(ch.id).padStart(2, '0')}
                                            </div>
                                            <StatusTag status={ch.status as any === 'processed' ? 'processed' : 'unprocessed'} />
                                        </div>
                                        <div className={`text-sm truncate ${selectedChapterId === ch.id ? 'text-white font-bold' : 'text-slate-400'}`}>
                                            {ch.title}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* FIXED FOOTER: Import Button (Reduced height) */}
                            <div className="absolute bottom-0 left-0 w-80 p-2.5 bg-slate-900/80 border-t border-slate-800 backdrop-blur-md flex justify-center">
                                <button className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/40 hover:bg-slate-800 text-slate-500 hover:text-slate-300 rounded-lg text-[10px] transition-all border border-slate-800 hover:border-slate-700 active:scale-95 group shadow-sm">
                                    <Upload size={12} className="group-hover:-translate-y-0.5 transition-transform" />
                                    导入章节 (TXT)
                                </button>
                            </div>
                        </div>

                        {/* RIGHT COLUMN: Content Viewer */}
                        <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
                            {/* Inner Header */}
                            <div className="h-16 border-b border-slate-800 bg-slate-900 flex items-center justify-between px-8 shrink-0 z-10 shadow-sm">
                                <div className="flex items-center gap-4 h-full">
                                    <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 shadow-inner shrink-0">
                                        <BookOpen size={20} className="text-cyan-400" />
                                    </div>
                                    <div className="flex items-center gap-3 min-w-0">
                                        <h2 className="text-sm font-bold text-white tracking-widest uppercase truncate max-w-[400px]">{selectedChapter.title}</h2>
                                        <span className="text-[10px] text-slate-600 font-mono shrink-0 pt-0.5">STAT: 2,450 WORDS</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <div className="flex items-center gap-2">
                                        <StatusTag status={selectedChapter.status as any === 'processed' ? 'processed' : 'unprocessed'} />
                                        
                                        {selectedChapter.status === 'processed' && (
                                            <>
                                                <button className="flex items-center gap-1.5 px-3 py-2 text-slate-400 hover:text-indigo-400 text-xs font-bold transition-colors">
                                                    <Eye size={14} /> 查看拆解结果
                                                </button>
                                                <button className="flex items-center gap-1.5 px-3 py-2 text-slate-400 hover:text-white text-xs font-bold transition-colors">
                                                    <RotateCcw size={14} /> 重新拆解
                                                </button>
                                            </>
                                        )}
                                        
                                        {!selectedChapter.status || selectedChapter.status === 'unprocessed' && (
                                            <button className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-cyan-900/20 transition-all active:scale-95">
                                                <SplitSquareVertical size={14} /> 立即拆解章节
                                            </button>
                                        )}
                                    </div>
                                    
                                    <div className="w-px h-4 bg-slate-800"></div>
                                    <button className="p-2 text-slate-500 hover:text-white transition-all" title="下载原文"><Download size={16}/></button>
                                </div>
                            </div>
                            
                            {/* Content Display */}
                            <div className="flex-1 overflow-y-auto p-0 md:p-10 bg-slate-950/40 font-sans custom-scrollbar">
                                <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-800 shadow-2xl min-h-full p-10 md:p-20 rounded-xl md:rounded-3xl relative">
                                    <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent opacity-50" />
                                    
                                    <article className="prose prose-invert prose-slate max-w-none prose-p:text-slate-300 prose-p:leading-loose prose-p:text-lg prose-headings:text-white">
                                        <h1 className="text-4xl font-black mb-16 text-center border-b border-slate-800/50 pb-10 tracking-tight">{selectedChapter.title}</h1>
                                        <div className="whitespace-pre-line text-slate-300 drop-shadow-sm">
                                            {selectedChapter.content}
                                        </div>
                                    </article>
                                    
                                    <div className="mt-24 flex justify-center opacity-10">
                                        <div className="flex gap-4">
                                            {[1,2,3,4,5].map(i => <div key={i} className="w-2 h-2 rounded-full bg-slate-400" />)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                 );
            case 'AGENTS':
                return (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
                         <div className="flex justify-between items-start">
                            <SectionTitle title="智能体编排 (Agent Orchestration)" description="配置负责不同任务的 AI 智能体。" />
                            <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs transition-colors border border-slate-700">
                                <Plus size={14} /> Add Agent
                            </button>
                         </div>
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {agents.map(agent => (
                                <div key={agent.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-cyan-500/30 transition-all group shadow-lg">
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                                                agent.status === 'active' ? 'bg-cyan-900/20 text-cyan-400' : 'bg-slate-800 text-slate-500'
                                            }`}>
                                                <BrainCircuit size={20} />
                                            </div>
                                            <div>
                                                <h4 className="font-semibold text-white">{agent.name}</h4>
                                                <span className="text-xs text-slate-500">{agent.role}</span>
                                            </div>
                                        </div>
                                        <button 
                                            onClick={() => setSelectedAgent(agent)}
                                            className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded transition-colors"
                                        >
                                            <Settings size={16} />
                                        </button>
                                    </div>
                                    <p className="text-xs text-slate-400 mb-4 h-8 line-clamp-2">{agent.desc}</p>
                                    <div className="flex items-center gap-2 text-[10px] text-slate-500 bg-slate-950/50 p-2 rounded-lg">
                                        <Cpu size={12} /> Model: <span className="text-slate-300">{agent.model}</span>
                                    </div>
                                </div>
                            ))}
                         </div>
                    </div>
                );
            case 'SKILLS':
                 return (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
                        <SectionTitle title="技能库 (Skill Library)" description="为 Agent 挂载专业的编剧理论与技巧。" />
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {initialSkills.map(skill => (
                                <div key={skill.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-purple-500/30 transition-all shadow-lg">
                                    <div className="flex items-center gap-2 mb-2 text-purple-400">
                                        <Sparkles size={16} />
                                        <h4 className="font-semibold text-white">{skill.name}</h4>
                                    </div>
                                    <p className="text-xs text-slate-400 mb-3">{skill.desc}</p>
                                    <div className="text-[10px] text-slate-500 border-t border-slate-800 pt-2 flex justify-between">
                                        <span>Trigger: {skill.trigger}</span>
                                        <span className="text-green-400">Enabled</span>
                                    </div>
                                </div>
                            ))}
                             <button className="border border-dashed border-slate-700 rounded-xl p-5 flex flex-col items-center justify-center text-slate-500 hover:text-white hover:border-slate-500 transition-colors gap-2 shadow-inner">
                                <Plus size={24} />
                                <span className="text-xs">Add Custom Skill</span>
                             </button>
                        </div>
                    </div>
                );
            case 'PLOT':
                return (
                    <div className="h-full flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-300">
                        <div className="flex justify-between items-start mb-4">
                            <SectionTitle title="分集大纲 (Episode Outline)" description="AI 生成的分集剧情结构。" />
                            <button className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium shadow-lg shadow-cyan-500/20 transition-all hover:scale-[1.02]">
                                <RefreshCw size={14} /> 重新生成大纲
                            </button>
                        </div>
                        
                        <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                            {mockPlots.map((plot) => (
                                <div key={plot.id} className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 hover:border-cyan-500/30 transition-all relative group shadow-xl">
                                     <div className="absolute top-4 right-4 text-slate-600 font-mono text-xs">ep.{String(plot.id).padStart(2,'0')}</div>
                                     <h3 className="text-lg font-bold text-white mb-2">{plot.title}</h3>
                                     <p className="text-sm text-slate-300 leading-relaxed mb-4">{plot.summary}</p>
                                     
                                     <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                         <div className="bg-slate-900 p-3 rounded-lg border border-slate-800/50 shadow-inner">
                                             <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Swords size={12}/> 核心冲突</div>
                                             <div className="flex flex-wrap gap-1">
                                                 {plot.conflicts.map((c, idx) => (
                                                     <span key={idx} className="px-1.5 py-0.5 bg-red-500/10 text-red-400 text-[10px] rounded border border-red-500/20">{c}</span>
                                                 ))}
                                             </div>
                                         </div>
                                         <div className="bg-slate-900 p-3 rounded-lg border border-slate-800/50 shadow-inner">
                                             <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Lightbulb size={12}/> 钩子 (Hook)</div>
                                             <div className="text-xs text-amber-400 font-medium">{plot.hooks}</div>
                                         </div>
                                         <div className="bg-slate-900 p-3 rounded-lg border border-slate-800/50 shadow-inner">
                                             <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Activity size={12}/> 紧张度</div>
                                             <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1.5">
                                                 <div className="h-full bg-gradient-to-r from-green-500 to-red-500" style={{width: `${plot.tension}%`}} />
                                             </div>
                                         </div>
                                     </div>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            case 'SCRIPT':
                 return (
                    <div className="h-full flex gap-0 animate-in fade-in slide-in-from-bottom-4 duration-300 overflow-hidden bg-slate-950">
                        {/* LEFT COLUMN: Controls & List */}
                        <div className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-2xl">
                            {/* Generator Controls */}
                            <div className="p-4 border-b border-slate-800 space-y-3 bg-slate-900/50">
                                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">剧集生成控制</h3>
                                
                                <button className="w-full py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white rounded-lg font-bold shadow-lg shadow-green-900/20 text-sm flex items-center justify-center gap-2 transition-all hover:scale-[1.02]">
                                    <Plus size={16} /> 生成下一批 (1/1)
                                </button>
                                
                                <button className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2">
                                    <Layers size={14} /> ∞ 全部生成
                                </button>

                                <div className="flex items-center gap-2">
                                    <div className="flex-1 relative">
                                        <input 
                                            type="number" 
                                            defaultValue={3} 
                                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-center text-white focus:border-cyan-500 outline-none font-mono shadow-inner" 
                                        />
                                    </div>
                                    <button className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs text-slate-400 border border-slate-700 rounded-lg flex items-center justify-center gap-1 transition-all">
                                        <RefreshCw size={12} /> 循环生成
                                    </button>
                                </div>
                            </div>

                            {/* Batch List */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar">
                                <div className="px-4 py-3 flex items-center justify-between text-xs text-slate-500 bg-slate-900/50 sticky top-0 z-10 backdrop-blur border-b border-slate-800">
                                    <span>批次管理</span>
                                    <div className="flex gap-2">
                                        <Trash2 size={12} className="hover:text-red-400 cursor-pointer transition-colors"/>
                                        <X size={12} className="hover:text-white cursor-pointer transition-colors"/>
                                    </div>
                                </div>

                                {/* Batch Header */}
                                <div className="px-4 py-2 bg-slate-800/30 border-b border-slate-800 flex items-center justify-between shadow-inner">
                                    <div className="flex items-center gap-2">
                                        <ChevronDownIcon size={12} className="text-slate-400" />
                                        <span className="text-xs font-bold text-slate-200">第1批次 (1-6章)</span>
                                    </div>
                                    <div className="flex items-center gap-1 text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                                        <CheckCircle2 size={10} /> 全部通过
                                    </div>
                                </div>

                                {/* Episodes List */}
                                <div className="divide-y divide-slate-800/30">
                                    {mockEpisodes.map(ep => (
                                        <div 
                                            key={ep.id}
                                            onClick={() => setSelectedEpisodeId(ep.id)}
                                            className={`px-4 py-4 cursor-pointer transition-all flex items-center justify-between group ${
                                                selectedEpisodeId === ep.id 
                                                ? 'bg-cyan-500/10 border-l-2 border-l-cyan-500 shadow-inner' 
                                                : 'hover:bg-slate-800 border-l-2 border-l-transparent'
                                            }`}
                                        >
                                            <div className="min-w-0 pr-2">
                                                <div className={`text-[10px] font-bold uppercase transition-colors ${selectedEpisodeId === ep.id ? 'text-cyan-400' : 'text-slate-500'}`}>
                                                    {ep.title}
                                                </div>
                                                <div className={`text-xs truncate mt-1 ${selectedEpisodeId === ep.id ? 'text-white font-medium' : 'text-slate-400'}`}>{ep.subtitle}</div>
                                            </div>
                                            
                                            <div className="shrink-0 flex items-center gap-2">
                                                {ep.status === 'APPROVED' && (
                                                    <span className="px-1.5 py-0.5 bg-green-500/10 text-green-500 text-[9px] font-black rounded border border-green-500/20 tracking-tighter">
                                                        OK
                                                    </span>
                                                )}
                                                {ep.status === 'GENERATING' && (
                                                    <Loader2 size={12} className="animate-spin text-blue-400"/>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* MIDDLE COLUMN: Script Editor */}
                        <div className="flex-1 flex flex-col bg-slate-900/50 relative overflow-hidden">
                            {/* Toolbar */}
                            <div className="h-14 border-b border-slate-800 bg-slate-900 flex items-center justify-between px-6 shrink-0 z-10 shadow-sm">
                                <div className="flex items-center gap-3">
                                    <h2 className="text-sm font-bold text-white tracking-widest uppercase truncate max-w-[300px]">
                                        {selectedEpisode.title} <span className="text-slate-500 mx-2">/</span> <span className="text-slate-400">{selectedEpisode.subtitle}</span>
                                    </h2>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button className="p-2 text-slate-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-all" title="Like"><ThumbsUp size={16} /></button>
                                    <div className="w-px h-4 bg-slate-800 mx-1"></div>
                                    <button className="flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all"><Download size={14} /> 导出</button>
                                    <button className="flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold text-green-400 bg-green-500/10 border border-green-500/30 rounded-lg hover:bg-green-500/20 transition-all ml-2 shadow-sm"><CheckCircle2 size={14} /> 审核通过</button>
                                </div>
                            </div>
                            
                            {/* Editor Area (饱满样式) */}
                            <div className="flex-1 overflow-y-auto p-0 md:p-8 font-mono text-sm leading-relaxed text-slate-300 bg-slate-950/40">
                                <div className="max-w-3xl mx-auto bg-slate-900 border border-slate-800 shadow-2xl min-h-full p-8 md:p-12 rounded-xl md:rounded-2xl relative">
                                    {selectedEpisode.content ? (
                                        <textarea 
                                            className="w-full h-full min-h-[800px] bg-transparent resize-none outline-none border-none focus:ring-0 text-slate-300 whitespace-pre-wrap selection:bg-cyan-500/30 scrollbar-hide"
                                            value={selectedEpisode.content}
                                            readOnly
                                        />
                                    ) : (
                                        <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4 mt-40 opacity-30">
                                            <FileEdit size={64} />
                                            <p className="text-sm tracking-widest uppercase">Initializing Content...</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Editor Footer */}
                            <div className="h-8 bg-slate-900 border-t border-slate-800 flex items-center justify-between px-4 text-[10px] text-slate-500 shrink-0 font-mono">
                                <div className="flex items-center gap-4">
                                    <span>STAT: {selectedEpisode.wordCount} WORDS</span>
                                    <span>ENCODING: UTF-8</span>
                                </div>
                                <span className="flex items-center gap-1.5 text-green-500 animate-pulse"><Save size={10} /> AUTO-SYNCED</span>
                            </div>
                        </div>

                        {/* RIGHT COLUMN: QC Report */}
                        <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col z-10 shadow-2xl">
                            <div className="p-4 border-b border-slate-800 flex items-center gap-2 bg-slate-900/50 backdrop-blur">
                                <FileCheck size={16} className="text-green-400" />
                                <h3 className="font-bold text-white text-xs uppercase tracking-wider">质量检查报告</h3>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
                                {selectedEpisode.qcReport ? (
                                    <>
                                        <div className="bg-slate-800/30 rounded-lg p-3 text-[11px] text-slate-500 border border-slate-800/50 italic">
                                            根据深度创作标准，对第{selectedEpisodeId}集剧本进行全量扫描...
                                        </div>
                                        {selectedEpisode.qcReport.checks.map((check: any, idx: number) => (
                                            <div key={idx} className="space-y-2">
                                                <h4 className="text-[11px] font-black text-slate-200 uppercase flex items-center gap-2 tracking-tighter">
                                                    <span className="w-4 h-4 rounded bg-slate-800 flex items-center justify-center text-[9px] text-cyan-500 border border-cyan-500/20">{idx + 1}</span>
                                                    {check.title}
                                                </h4>
                                                <ul className="space-y-2 pl-3 border-l border-slate-800 ml-2">
                                                    {check.items.map((item: string, i: number) => (
                                                        <li key={i} className="text-[11px] text-slate-400 leading-relaxed flex items-start gap-2">
                                                            <div className="mt-1 w-1 h-1 rounded-full bg-cyan-500 opacity-40 shrink-0" />
                                                            {item}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        ))}
                                        <div className="mt-6 pt-4 border-t border-slate-800">
                                            <div className="bg-green-500/5 border border-green-500/10 rounded-xl p-4 flex items-center gap-4">
                                                <div className="w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center font-black text-lg shadow-lg shadow-green-500/20">{selectedEpisode.qcReport.score}</div>
                                                <div>
                                                    <div className="text-[10px] text-green-400 font-black tracking-widest uppercase">Verified Pass</div>
                                                    <div className="text-[9px] text-slate-500 leading-tight">此批次创作质量卓越，符合归档标准。</div>
                                                </div>
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <div className="text-center text-slate-600 mt-20 opacity-20"><Search size={48} className="mx-auto mb-4" /><p className="text-xs uppercase font-bold">Scanning...</p></div>
                                )}
                            </div>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="flex h-full bg-slate-950 overflow-hidden">
            {/* Sidebar */}
            <div className="w-16 md:w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between py-4 z-20">
                <div className="space-y-6">
                    <div className="px-4 md:px-6">
                         <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 hidden md:block">Workflow</div>
                         <div className="space-y-1">
                             <SidebarItem icon={Settings} label="项目配置 (Config)" active={activeTab === 'CONFIG'} onClick={() => setActiveTab('CONFIG')} />
                             <SidebarItem icon={BookText} label="小说原文 (Source)" active={activeTab === 'SOURCE'} onClick={() => setActiveTab('SOURCE')} />
                             <div className="my-2 border-t border-slate-800 mx-2 hidden md:block" />
                             <SidebarItem icon={Users} label="智能体编排 (Agent)" active={activeTab === 'AGENTS'} onClick={() => setActiveTab('AGENTS')} />
                             <SidebarItem icon={Layers} label="技能库 (Skill)" active={activeTab === 'SKILLS'} onClick={() => setActiveTab('SKILLS')} />
                             <div className="my-2 border-t border-slate-800 mx-2 hidden md:block" />
                             <SidebarItem icon={LayoutTemplate} label="剧集拆解 (Plot)" active={activeTab === 'PLOT'} onClick={() => setActiveTab('PLOT')} />
                             <SidebarItem icon={FileEdit} label="剧本生成 (Script)" active={activeTab === 'SCRIPT'} onClick={() => setActiveTab('SCRIPT')} />
                         </div>
                    </div>
                </div>

                <div className="px-4 md:px-6 space-y-2">
                     <button 
                        onClick={() => setShowCopilot(!showCopilot)}
                        className={`w-full flex items-center justify-center md:justify-start gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                            showCopilot ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                     >
                        <BrainCircuit size={18} />
                        <span className="hidden md:inline">AI Copilot</span>
                     </button>
                     <button 
                         onClick={() => setShowConsole(!showConsole)}
                         className={`w-full flex items-center justify-center md:justify-start gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                            showConsole ? 'bg-slate-800 text-cyan-400 border border-slate-700' : 'text-slate-500 hover:text-slate-300'
                         }`}
                     >
                        <Terminal size={18} />
                        <span className="hidden md:inline">Console</span>
                     </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden relative">
                {/* Header */}
                {(activeTab !== 'SCRIPT' && activeTab !== 'SOURCE') && (
                    <header className="h-14 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-900/50 backdrop-blur z-10 shrink-0">
                        <div className="flex items-center gap-3">
                            <h1 className="font-semibold text-white truncate max-w-[200px]">{project.name}</h1>
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-xs border border-slate-700 hidden sm:inline-block">{project.novel_type}</span>
                        </div>
                        <div className="flex items-center gap-3">
                            {activeTab === 'CONFIG' ? (
                                <>
                                    <button
                                        onClick={handleSaveConfig}
                                        disabled={saving}
                                        className="flex items-center gap-2 px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-lg border border-slate-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                        {saving ? '保存中...' : '保存设置'}
                                    </button>
                                    <button
                                        onClick={handleStart}
                                        disabled={project.status !== 'ready' || starting}
                                        className={`flex items-center gap-2 px-6 py-1.5 text-xs font-bold rounded-lg shadow-lg transition-all ${
                                            project.status === 'ready'
                                            ? 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white shadow-cyan-500/20 hover:scale-105 cursor-pointer'
                                            : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
                                        }`}
                                    >
                                        {starting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
                                        {starting ? '启动中...' : (project.status === 'parsing' ? '正在运行' : '项目启动')}
                                    </button>
                                </>
                            ) : (
                                <>
                                    <button className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white transition-colors">
                                        <Save size={14} /> Auto-saved
                                    </button>
                                    <div className="h-4 w-px bg-slate-700"></div>
                                    <button className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-cyan-500/20 transition-all hover:scale-105">
                                        <Play size={12} fill="currentColor" /> Run Agents
                                    </button>
                                </>
                            )}
                        </div>
                    </header>
                )}

                {/* Content Body */}
                <div className={`flex-1 overflow-hidden relative ${(activeTab === 'SCRIPT' || activeTab === 'SOURCE') ? 'p-0' : 'p-6 md:p-8'}`}>
                     {renderContent()}
                </div>

                {/* Overlays */}
                <ConsoleLogger 
                    logs={logs} 
                    visible={showConsole} 
                    isProcessing={isProcessing} 
                    onClose={() => setShowConsole(false)}
                />

                <AICopilot 
                    visible={showCopilot} 
                    onClose={() => setShowCopilot(false)} 
                    context={activeTab}
                />
            </div>

            {/* Modal */}
            <AnimatePresence>
                {selectedAgent && (
                    <AgentConfigModal 
                        agent={selectedAgent} 
                        onClose={() => setSelectedAgent(null)}
                        onSave={(updated) => {
                            setAgents(agents.map(a => a.id === updated.id ? updated : a));
                            setSelectedAgent(null);
                        }}
                    />
                )}
            </AnimatePresence>
        </div>
    );
};

const ChevronDownIcon = ({size, className}:{size:number, className?:string}) => (
    <svg width={size} height={size} className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
);

export default Workspace;
