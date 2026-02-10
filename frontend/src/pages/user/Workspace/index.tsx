import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Settings, FileEdit, Play,
  BrainCircuit, Layers, Users,
  Terminal, LayoutTemplate,
  BookText, Save, Sparkles, Loader2, X,
  RotateCcw, PlayCircle, FastForward, Repeat, Zap
} from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import ConsoleLogger from '../../../components/ConsoleLogger';
import AICopilot from '../../../components/AICopilot';
import SkillSelector from '../../../components/SkillSelector';
import ConfigSelector from '../../../components/ConfigSelector';
import AgentConfigModal from '../../../components/modals/AgentConfigModal';
import { UserTier, Batch, PlotBreakdown } from '../../../types';
import { projectApi, breakdownApi } from '../../../services/api';
import { message, Modal, Upload } from 'antd';
import { useConsoleLogger } from '../../../hooks/useConsoleLogger';
import { useBreakdownWebSocket } from '../../../hooks/useBreakdownWebSocket';
import { parseErrorMessage } from '../../../utils/errorParser';
import ConfigTab from './ConfigTab';
import SourceTab from './SourceTab';
import PlotTab from './PlotTab';
import ScriptTab from './ScriptTab';
import AgentsTab from './AgentsTab';
import SkillsTab from './SkillsTab';

interface ProjectWorkspaceProps {
  userTier: UserTier;
}

type Tab = 'CONFIG' | 'SOURCE' | 'AGENTS' | 'SKILLS' | 'PLOT' | 'SCRIPT';

// --- Mock Data Generators ---
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
    const importPosition = 'after' as const;

    const [activeTab, setActiveTab] = useState<Tab>('CONFIG');
    const [showConsole, setShowConsole] = useState(false);
    const [showCopilot, setShowCopilot] = useState(false);
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

    // Source Tab State
    const [chapters, setChapters] = useState<any[]>([]);
    const [selectedChapter, setSelectedChapter] = useState<any>(null);
    const [loadingChapters, setLoadingChapters] = useState(false);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const [totalChapters, setTotalChapters] = useState(0);
    const [keyword, setKeyword] = useState('');
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
    const [uploadChapterFile, setUploadChapterFile] = useState<File | null>(null);

    // PLOT Tab State
    const [batches, setBatches] = useState<Batch[]>([]);
    const [batchTotal, setBatchTotal] = useState(0);
    const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);
    const [breakdownResult, setBreakdownResult] = useState<PlotBreakdown | null>(null);
    const [breakdownLoading, setBreakdownLoading] = useState(false);
    const [breakdownTaskId, setBreakdownTaskId] = useState<string | null>(null);
    const [breakdownProgress, setBreakdownProgress] = useState(0);
    const [isCreatingBatches, setIsCreatingBatches] = useState(false);
    const [isAllBreakdownRunning, setIsAllBreakdownRunning] = useState(false);

    // 批量拆解状态
    const [batchProgress, setBatchProgress] = useState<{
        total: number;
        completed: number;
        in_progress: number;
        pending: number;
        failed: number;
        overall_progress: number;
    } | null>(null);
    const [isBatchRunning, setIsBatchRunning] = useState(false);

    // 错误提示状态
    const [showErrorModal, setShowErrorModal] = useState(false);
    const [parsedError, setParsedError] = useState<{
        code: string;
        message: string;
        canRetry: boolean;
        action?: 'upgrade' | 'retry' | 'skip' | 'configure';
    } | null>(null);

    // Breakdown Config Modal State
    const [isBreakdownModalOpen, setIsBreakdownModalOpen] = useState(false);
    const [targetBatchId, setTargetBatchId] = useState<string | null>(null);
    const [selectedBreakdownSkills, setSelectedBreakdownSkills] = useState<string[]>([]);
    const [breakdownConfig, setBreakdownConfig] = useState({
        adaptMethodKey: 'adapt_method_default',
        qualityRuleKey: 'qa_breakdown_default',
        outputStyleKey: 'output_style_default'
    });

    // PLOT Pagination State
    const [batchPage, setBatchPage] = useState(1);
    const [batchHasMore, setBatchHasMore] = useState(true);
    const [loadingBatches, setLoadingBatches] = useState(false);

    // 使用 useConsoleLogger Hook 管理日志
    const {
        logs,
        llmStats,
        addLog,
        clearLogs
    } = useConsoleLogger(breakdownTaskId);

    // 使用 WebSocket Hook 监听任务进度（优先使用 WebSocket，失败时降级到轮询）
    const lastStepRef = useRef<string>('');
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const pollIntervalTimeRef = useRef<number>(2000); // 动态轮询间隔

    const { isConnected: wsConnected, progress: wsProgress, currentStep: wsCurrentStep, usePolling } = useBreakdownWebSocket(
        breakdownTaskId,
        {
            onProgress: (data) => {
                setBreakdownProgress(data.progress || 0);

                // 去重日志：只在步骤变化时添加
                if (data.current_step && data.current_step !== lastStepRef.current) {
                    addLog('thinking', data.current_step);
                    lastStepRef.current = data.current_step;
                }
            },
            onComplete: () => {
                setBreakdownTaskId(null);
                message.success('拆解完成');
                if (selectedBatch) {
                    fetchBreakdownResults(selectedBatch.id);
                }
                fetchBatches();
            },
            onError: (error) => {
                setBreakdownTaskId(null);
                const parsedError = parseErrorMessage(error);
                showError(parsedError);
            },
            fallbackToPolling: true
        }
    );

    // 当 WebSocket 降级到轮询时，启动优化的轮询机制
    useEffect(() => {
        if (usePolling && breakdownTaskId && selectedBatch) {
            console.log('[Polling] WebSocket 不可用，启动优化轮询机制');
            startOptimizedPolling(breakdownTaskId, selectedBatch.id);
        }

        return () => {
            if (pollingIntervalRef.current) {
                clearTimeout(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };
    }, [usePolling, breakdownTaskId, selectedBatch]);

    // 优化的轮询机制（动态间隔 + 去重日志）
    const startOptimizedPolling = (taskId: string, batchId: string) => {
        const poll = async () => {
            try {
                const res = await breakdownApi.getTaskStatus(taskId);
                const { status, progress, current_step } = res.data;

                setBreakdownProgress(progress || 0);

                // 去重日志
                if (current_step && current_step !== lastStepRef.current) {
                    addLog('thinking', current_step);
                    lastStepRef.current = current_step;
                }

                // 根据状态动态调整轮询间隔
                if (status === 'queued') {
                    pollIntervalTimeRef.current = 3000; // 排队中，降低频率
                } else if (status === 'running' || status === 'processing') {
                    pollIntervalTimeRef.current = 1500; // 运行中，提高频率
                } else if (status === 'retrying') {
                    pollIntervalTimeRef.current = 5000; // 重试中，降低频率
                }

                // 任务完成
                if (status === 'completed') {
                    if (pollingIntervalRef.current) {
                        clearTimeout(pollingIntervalRef.current);
                        pollingIntervalRef.current = null;
                    }
                    setBreakdownTaskId(null);
                    message.success('拆解完成');
                    fetchBreakdownResults(batchId);
                    fetchBatches();
                    return;
                }

                // 任务失败
                if (status === 'failed') {
                    if (pollingIntervalRef.current) {
                        clearTimeout(pollingIntervalRef.current);
                        pollingIntervalRef.current = null;
                    }
                    setBreakdownTaskId(null);

                    const errorMsg = res.data.error_message || '拆解失败';
                    const parsedError = parseErrorMessage(errorMsg);
                    showError(parsedError);
                    return;
                }

                // 调度下一次轮询
                pollingIntervalRef.current = setTimeout(poll, pollIntervalTimeRef.current);

            } catch (err) {
                console.error('[Polling] 轮询失败:', err);
                if (pollingIntervalRef.current) {
                    clearTimeout(pollingIntervalRef.current);
                    pollingIntervalRef.current = null;
                }
            }
        };

        poll();
    };

    // 创建批次并获取列表
    const createBatchesAndFetch = async () => {
        if (!projectId) return;
        setIsCreatingBatches(true);
        try {
            // 调用后端创建批次接口（幂等）
            await projectApi.createBatches(projectId);
            // 创建完成后获取列表
            await fetchBatches(1, false);
        } catch (err) {
            console.error('创建批次失败:', err);
            message.error('创建批次失败');
        } finally {
            setIsCreatingBatches(false);
        }
    };

    // 获取批次列表
    const fetchBatches = async (pageNum = 1, append = false) => {
        if (!projectId) return;
        setLoadingBatches(true);
        try {
            const res = await projectApi.getBatches(projectId, pageNum, 20);
            const newItems = res.data?.items || [];
            const total = res.data?.total || 0;

            setBatchTotal(total);

            if (append) {
                setBatches(prev => [...prev, ...newItems]);
            } else {
                setBatches(newItems);
                if (newItems.length > 0 && !selectedBatch && pageNum === 1) {
                    setSelectedBatch(newItems[0]);
                }
            }

            setBatchHasMore((pageNum * 20) < total);

        } catch (err) {
            console.error('获取批次失败:', err);
            message.error('获取批次列表失败');
        } finally {
            setLoadingBatches(false);
        }
    };

    // 获取项目详情
    const fetchProject = async () => {
        if (!projectId) return;
        setLoading(true);
        try {
            const res = await projectApi.getProject(projectId);
            setProject(res.data);
            setFormData({
                name: res.data.name || '',
                novel_type: res.data.type || '悬疑/惊悚',
                description: res.data.description || '',
                batch_size: res.data.batch_size || 5,
                chapter_split_rule: 'auto',
                breakdown_model: 'DeepNarrative-Pro',
                script_model: 'Gemini-1.5-Pro'
            });
            setTotalChapters(res.data.total_chapters || 0);
        } catch (err) {
            console.error('获取项目失败:', err);
            message.error('加载项目失败');
        } finally {
            setLoading(false);
        }
    };

    // 获取章节列表
    const fetchChapters = async (pageNum = 1, append = false) => {
        if (!projectId) return;
        setLoadingChapters(true);
        try {
            const res = await projectApi.getChapters(projectId, pageNum, 20, keyword);
            const newItems = res.data.items || [];

            if (append) {
                setChapters(prev => [...prev, ...newItems]);
            } else {
                setChapters(newItems);
            }
            setHasMore((pageNum * 20) < (res.data.total || 0));
            setTotalChapters(res.data.total || 0);
        } catch (err) {
            message.error('获取章节列表失败');
        } finally {
            setLoadingChapters(false);
        }
    };

    const handleSaveConfig = async () => {
        if (!projectId) return;
        setSaving(true);
        try {
            await projectApi.updateProject(projectId, {
                name: formData.name,
                novel_type: formData.novel_type,
                description: formData.description,
                batch_size: formData.batch_size
            });
            message.success('保存成功');
            fetchProject();
        } catch (err) {
            message.error('保存失败');
        } finally {
            setSaving(false);
        }
    };

    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
        if (scrollHeight - scrollTop <= clientHeight + 50 && !loadingChapters && hasMore) {
            const nextPage = page + 1;
            setPage(nextPage);
            fetchChapters(nextPage, true);
        }
    };

    const getStatusText = (status: string) => {
         const statusMap: Record<string, string> = {
            'draft': '草稿',
            'uploaded': '已上传',
            'ready': '就绪',
            'parsing': '拆解中',
            'scripting': '生成中',
            'completed': '完成'
        };
        return statusMap[status] || status;
    };

    // 初始化加载
    useEffect(() => {
        fetchProject();
    }, [projectId]);

    // 搜索监听
    useEffect(() => {
        if (activeTab === 'SOURCE') {
            setPage(1);
            fetchChapters(1, false);
        }
    }, [keyword]);

    // 监听 Tab 切换加载数据
    useEffect(() => {
        if (activeTab === 'SOURCE') {
            fetchChapters();
        }
        if (activeTab === 'PLOT') {
            // 直接获取批次列表，分批已在启动时异步触发
            setBatchPage(1);
            setBatchHasMore(true);
            setBatches([]);
            fetchBatches(1, false);
        }
    }, [activeTab, projectId]);

    // 滚动加载
    const handleBatchScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
        if (scrollHeight - scrollTop <= clientHeight + 50 && !loadingBatches && batchHasMore) {
            const nextPage = batchPage + 1;
            setBatchPage(nextPage);
            fetchBatches(nextPage, true);
        }
    };

    const handleDeleteChapter = async (e: React.MouseEvent, chapterId: string) => {
        e.stopPropagation();
        if (!projectId) return;
        Modal.confirm({
            title: '确认删除',
            content: '确定要删除这一章吗？此操作不可撤销。',
            okText: '删除',
            okType: 'danger',
            cancelText: '取消',
            className: 'dark-modal',
            styles: {
                mask: { backgroundColor: 'rgba(0, 0, 0, 0.8)' },
                content: {
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '16px',
                    padding: '24px'
                },
                header: { backgroundColor: 'transparent', color: '#fff' },
                body: { color: '#94a3b8' },
                footer: { borderTop: '1px solid #1e293b' }
            },
            okButtonProps: {
                style: { backgroundColor: '#dc2626', borderColor: '#dc2626' }
            },
            cancelButtonProps: {
                style: { backgroundColor: '#1e293b', borderColor: '#334155', color: '#94a3b8' }
            },
            onOk: async () => {
                try {
                    await projectApi.deleteChapter(projectId, chapterId);
                    message.success('章节已删除');
                    setChapters(prev => prev.filter(c => String(c.id) !== chapterId));
                    setTotalChapters(prev => prev - 1);
                } catch (err) {
                    message.error('删除失败');
                }
            }
        });
    };

    const handleUploadChapter = async () => {
        if (!projectId || !uploadChapterFile) {
            message.warning('请选择文件');
            return;
        }
        setUploading(true);
        try {
            const prevChapterId = importPosition === 'after' && selectedChapter ? String(selectedChapter.id) : undefined;
            await projectApi.uploadChapter(projectId, uploadChapterFile, prevChapterId);
            message.success('章节上传并插入成功');
            setIsUploadModalOpen(false);
            setUploadChapterFile(null);
            setPage(1);
            fetchChapters(1, false);
        } catch (err) {
            message.error('上传失败');
        } finally {
            setUploading(false);
        }
    };

    const triggerChapterFileUpload = () => {
        setIsUploadModalOpen(true);
    };

    const handleModalFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // 验证文件大小 (1MB = 1024 * 1024 bytes)
        if (file.size > 1024 * 1024) {
            message.error('文件大小不能超过 1MB');
            return;
        }

        setUploadChapterFile(file);
    };

    const handleDownloadChapter = () => {
        if (!selectedChapter) return;
        const blob = new Blob([selectedChapter.content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${selectedChapter.title}.txt`;
        link.click();
        URL.revokeObjectURL(url);
    };

    // 监听 Tab 切换加载数据
    useEffect(() => {
        if (activeTab === 'SOURCE') {
            fetchChapters();
        }
        if (activeTab === 'PLOT') {
            // 进入 PLOT 页面时，先创建批次（幂等），再获取批次列表
            createBatchesAndFetch();
        }
    }, [activeTab, projectId]);


    // 获取拆解结果（带重试机制和指数退避）
    const fetchBreakdownResults = async (batchId: string, retryCount = 0) => {
        if (retryCount === 0) {
            setBreakdownLoading(true);
        }

        try {
            const res = await breakdownApi.getBreakdownResults(batchId);
            setBreakdownResult(res.data);
            setBreakdownLoading(false);
        } catch (err: any) {
            // 如果是 404 且批次状态为 completed，可能是时序问题，自动重试
            if (err.response?.status === 404 && retryCount < 3) {
                const retryDelay = Math.pow(2, retryCount) * 1000; // 指数退避：1s, 2s, 4s
                console.log(`拆解结果未找到，${retryDelay / 1000}秒后重试 (${retryCount + 1}/3)...`);
                setTimeout(() => {
                    fetchBreakdownResults(batchId, retryCount + 1);
                }, retryDelay);
            } else {
                console.error('获取拆解结果失败:', err);
                setBreakdownResult(null);
                setBreakdownLoading(false);
            }
        }
    };

    // 启动拆解任务 (打开配置弹窗)
    const handleStartBreakdownClick = (batchId: string) => {
        setTargetBatchId(batchId);
        // 默认全选或根据上次选择，这里暂时留空让用户选，或者 Fetch 默认 skills
        setIsBreakdownModalOpen(true);
    };

    // 确认启动拆解
    const handleConfirmBreakdown = async () => {
        if (!targetBatchId) return;
        setIsBreakdownModalOpen(false);

        try {
            // 自动弹出 Console
            setShowConsole(true);
            clearLogs();
            lastStepRef.current = ''; // 重置步骤记录
            addLog('info', `配置已应用，开始拆解批次 ${selectedBatch?.batch_number || ''}...`);

            const res = await breakdownApi.startBreakdown(targetBatchId, {
                selectedSkills: selectedBreakdownSkills,
                adaptMethodKey: breakdownConfig.adaptMethodKey,
                qualityRuleKey: breakdownConfig.qualityRuleKey,
                outputStyleKey: breakdownConfig.outputStyleKey
            });
            setBreakdownTaskId(res.data.task_id);
            message.info('拆解任务已启动');

            // WebSocket 会自动连接，如果失败会降级到轮询
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || '启动拆解失败';
            message.error(errorMsg);
            showError({ code: 'START_FAILED', message: errorMsg });
        }
    };

    // 以前的直接启动函数保留给 Loop/All 使用，但需要改造支持参数
    const internalStartBreakdown = async (batchId: string) => {
        const res = await breakdownApi.startBreakdown(batchId); // 使用默认配置
        return res;
    };

    // 循环拆解：依次拆解所有 pending 批次
    const handleLoopBreakdown = async () => {
        const pendingBatches = batches.filter(b => b.breakdown_status === 'pending');
        if (pendingBatches.length === 0) {
            message.info('没有待拆解的批次');
            return;
        }
        setShowConsole(true);
        setBreakdownQueue(pendingBatches.map(b => b.id));
        setCurrentBreakdownIndex(0);
        setIsAllBreakdownRunning(true);

        // 启动第一个批次
        await processBreakdownQueue(pendingBatches[0].id, pendingBatches.map(b => b.id), 0);
    };

    // 处理拆解队列
    const processBreakdownQueue = async (batchId: string, queue: string[], index: number) => {
        try {
            addLog('info', `开始拆解批次 ${index + 1}/${queue.length}...`);

            const res = await breakdownApi.startBreakdown(batchId);
            setBreakdownTaskId(res.data.task_id);

            // 轮询并在完成后处理下一个
            pollBreakdownStatusWithCallback(res.data.task_id, () => {
                const nextIndex = index + 1;
                if (nextIndex < queue.length) {
                    setCurrentBreakdownIndex(nextIndex);
                    processBreakdownQueue(queue[nextIndex], queue, nextIndex);
                } else {
                    setIsAllBreakdownRunning(false);
                    setBreakdownQueue([]);
                    message.success('所有批次拆解完成');
                }
            });
        } catch (err: any) {
            setIsAllBreakdownRunning(false);
            message.error(err.response?.data?.detail || '拆解失败');
        }
    };

    // 全部拆解：一次性启动所有 pending 批次（增强版）
    const handleAllBreakdown = async () => {
        if (!projectId) return;
        const pendingBatches = batches.filter(b => b.breakdown_status === 'pending');
        if (pendingBatches.length === 0) {
            message.info('没有待拆解的批次');
            return;
        }
        setShowConsole(true);
        setIsBatchRunning(true);

        // 初始化批量进度
        setBatchProgress({
            total: pendingBatches.length,
            completed: 0,
            in_progress: 0,
            pending: pendingBatches.length,
            failed: 0,
            overall_progress: 0
        });

        try {
            const res = await breakdownApi.startBatchBreakdown({
                projectId,
                adaptMethodKey: breakdownConfig.adaptMethodKey,
                qualityRuleKey: breakdownConfig.qualityRuleKey,
                outputStyleKey: breakdownConfig.outputStyleKey
            });

            if (res.data.total > 0) {
                message.info(`已启动 ${res.data.total} 个拆解任务`);
                // 开始轮询批量进度
                pollBatchProgress();
            } else {
                setIsBatchRunning(false);
                message.info('没有待拆解的批次');
            }
        } catch (err: any) {
            setIsBatchRunning(false);
            setBatchProgress(null);
            const errorMsg = err.response?.data?.detail || '批量拆解失败';
            message.error(errorMsg);
            // 显示错误模态框
            showError({
                code: 'BATCH_START_FAILED',
                message: errorMsg,
                canRetry: true
            });
        }
    };

    // 轮询批量进度
    const pollBatchProgress = () => {
        const interval = setInterval(async () => {
            try {
                const res = await breakdownApi.getBatchProgress(projectId);
                const progress = res.data;

                setBatchProgress({
                    total: progress.total_batches,
                    completed: progress.completed,
                    in_progress: progress.in_progress,
                    pending: progress.pending,
                    failed: progress.failed,
                    overall_progress: progress.overall_progress
                });

                // 检查是否全部完成
                const allDone = progress.completed + progress.failed === progress.total_batches;
                if (allDone) {
                    clearInterval(interval);
                    setIsBatchRunning(false);

                    if (progress.failed > 0) {
                        message.warning(`批量拆解完成，${progress.failed} 个任务失败`);
                    } else {
                        message.success(`全部 ${progress.completed} 个批次拆解完成`);
                    }
                    fetchBatches();
                }
            } catch (err) {
                console.error('获取批量进度失败:', err);
            }
        }, 3000);
    };

    // 取消批量拆解
    const handleCancelBatch = () => {
        setIsBatchRunning(false);
        setBatchProgress(null);
        message.info('已取消批量拆解');
    };

    // 解析错误信息
    const showError = (error: { code: string; message: string; canRetry?: boolean }) => {
        let action: 'upgrade' | 'retry' | 'skip' | 'configure' | undefined;
        let canRetry = error.canRetry ?? true;

        if (error.code === 'QUOTA_EXCEEDED') {
            action = 'upgrade';
            canRetry = false;
        } else if (error.code === 'VALIDATION_ERROR') {
            action = 'configure';
        } else if (error.code === 'RETRYABLE_ERROR') {
            canRetry = false; // 后端会自动重试
        }

        setParsedError({
            code: error.code,
            message: error.message,
            canRetry,
            action
        });
        setShowErrorModal(true);
    };

    // 继续拆解：从第一个 pending 批次开始
    const handleContinueBreakdown = async () => {
        if (!projectId) return;
        const firstPending = batches.find(b => b.breakdown_status === 'pending');
        if (!firstPending) {
            message.info('没有待拆解的批次');
            return;
        }
        setSelectedBatch(firstPending);
        try {
             setShowConsole(true);
             clearLogs();
             lastStepRef.current = '';
             const res = await internalStartBreakdown(firstPending.id);
             setBreakdownTaskId(res.data.task_id);
             // WebSocket 会自动连接
        } catch (err: any) {
             const errorMsg = err.response?.data?.detail || '启动失败';
             message.error(errorMsg);
             showError({ code: 'START_FAILED', message: errorMsg });
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

    // Render logic for different tabs
    const renderContent = () => {
        switch(activeTab) {
            case 'CONFIG':
                return (
                    <ConfigTab
                        project={project}
                        formData={formData}
                        onFormChange={(field, value) => setFormData(prev => ({ ...prev, [field]: value }))}
                        onSaveConfig={handleSaveConfig}
                        saving={saving}
                        uploading={uploading}
                        splitting={splitting}
                        onFileUpload={triggerFileUpload}
                        onSplit={handleSplit}
                        getStatusText={getStatusText}
                    />
                );
            case 'SOURCE':
                return (
                    <SourceTab
                        project={project}
                        chapters={chapters}
                        selectedChapter={selectedChapter}
                        onSelectChapter={setSelectedChapter}
                        loadingChapters={loadingChapters}
                        totalChapters={totalChapters}
                        keyword={keyword}
                        onKeywordChange={setKeyword}
                        onScroll={handleScroll}
                        onDeleteChapter={handleDeleteChapter}
                        onDownloadChapter={handleDownloadChapter}
                        onUploadChapter={triggerChapterFileUpload}
                    />
                );
            case 'PLOT':
                return (
                    <PlotTab
                        projectId={projectId!}
                        batches={batches}
                        selectedBatch={selectedBatch}
                        onSelectBatch={setSelectedBatch}
                        onStartBreakdown={handleStartBreakdownClick}
                        isCreatingBatches={isCreatingBatches}
                        loadingBatches={loadingBatches}
                        breakdownTaskId={breakdownTaskId}
                        breakdownProgress={breakdownProgress}
                        breakdownResult={breakdownResult}
                        breakdownLoading={breakdownLoading}
                        onBatchScroll={handleBatchScroll}
                    />
                );
            case 'SCRIPT':
                return (
                    <ScriptTab
                        episodes={mockEpisodes}
                        selectedEpisodeId={selectedEpisodeId}
                        onSelectEpisode={setSelectedEpisodeId}
                    />
                );
            case 'AGENTS':
                return (
                    <AgentsTab
                        agents={agents}
                        onSelectAgent={setSelectedAgent}
                    />
                );
            case 'SKILLS':
                return (
                    <SkillsTab
                        skills={initialSkills}
                    />
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

                            {/* PLOT Tab: 进度条展示在 Header 左侧 */}
                            {activeTab === 'PLOT' && batches.length > 0 && (
                                <div className="ml-6 hidden md:flex items-center gap-3 animate-in fade-in slide-in-from-left-4 duration-500">
                                    {/* 简约图标替代胶囊 */}
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-500 ${
                                        isAllBreakdownRunning
                                        ? 'bg-cyan-500/10 text-cyan-400 shadow-[0_0_15px_-3px_rgba(6,182,212,0.4)]'
                                        : 'bg-slate-800/80 text-slate-500 border border-slate-700/50'
                                    }`}>
                                        {isAllBreakdownRunning ? (
                                            <Loader2 size={16} className="animate-spin" />
                                        ) : (
                                            <Zap size={16} className={batches.some(b => b.breakdown_status === 'completed') ? 'text-amber-400 fill-amber-400/20' : ''} />
                                        )}
                                    </div>

                                    {/* 能量条进度 */}
                                    <div className="flex flex-col gap-1.5 w-40 group">
                                        <div className="flex justify-between items-end px-0.5">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest group-hover:text-slate-400 transition-colors">
                                                {isAllBreakdownRunning ? 'Processing' : 'Breakdown Status'}
                                            </span>
                                            <span className={`text-[10px] font-mono font-bold ${isAllBreakdownRunning ? 'text-cyan-400' : 'text-emerald-500'}`}>
                                                {Math.round((batches.filter(b => b.breakdown_status === 'completed').length / batches.length) * 100)}%
                                            </span>
                                        </div>
                                        <div className="h-1.5 w-full bg-slate-800/80 rounded-full overflow-hidden border border-slate-700/30 p-[1px]">
                                            <div
                                                className={`h-full rounded-full transition-all duration-700 ease-out relative overflow-hidden ${
                                                    isAllBreakdownRunning
                                                    ? 'bg-gradient-to-r from-cyan-500 to-blue-500'
                                                    : 'bg-gradient-to-r from-emerald-600 to-teal-400'
                                                }`}
                                                style={{width: `${(batches.filter(b => b.breakdown_status === 'completed').length / batches.length) * 100}%`}}
                                            >
                                                {/* 流光特效 */}
                                                {isAllBreakdownRunning && (
                                                    <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/50 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
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
                            ) : activeTab === 'PLOT' ? (
                                <div className="flex items-center gap-3">
                                    {/* 批量进度显示 */}
                                    {isBatchRunning && batchProgress && (
                                        <div className="flex items-center gap-3 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                                            <div className="relative w-8 h-8">
                                                <svg className="w-8 h-8 transform -rotate-90">
                                                    <circle
                                                        cx="16" cy="16" r="12"
                                                        stroke="#1e293b" strokeWidth="3" fill="none"
                                                    />
                                                    <circle
                                                        cx="16" cy="16" r="12"
                                                        stroke="#06b6d4" strokeWidth="3" fill="none"
                                                        strokeDasharray={`${batchProgress.overall_progress * 0.75} 75`}
                                                        className="transition-all duration-500"
                                                    />
                                                </svg>
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-xs text-blue-300 font-medium">
                                                    批量拆解中 {batchProgress.completed}/{batchProgress.total}
                                                </span>
                                                <div className="flex gap-2 text-[10px]">
                                                    <span className="text-green-400">{batchProgress.completed} 成功</span>
                                                    <span className="text-yellow-400">{batchProgress.in_progress} 进行</span>
                                                    <span className="text-red-400">{batchProgress.failed} 失败</span>
                                                </div>
                                            </div>
                                            <button
                                                onClick={handleCancelBatch}
                                                className="ml-2 px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 rounded border border-slate-700 transition-colors"
                                            >
                                                取消
                                            </button>
                                        </div>
                                    )}

                                    <button
                                        onClick={handleLoopBreakdown}
                                        disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning || batches.filter(b => b.breakdown_status === 'pending').length === 0}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                        title="依次拆解所有待处理批次"
                                    >
                                        <Repeat size={14} />
                                        循环
                                    </button>
                                    <button
                                        onClick={handleAllBreakdown}
                                        disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning || batches.filter(b => b.breakdown_status === 'pending').length === 0}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                        title="一次性启动所有待处理批次"
                                    >
                                        <FastForward size={14} />
                                        全部
                                    </button>
                                    <button
                                        onClick={handleContinueBreakdown}
                                        disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning || batches.filter(b => b.breakdown_status === 'pending').length === 0}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                        title="从第一个待处理批次开始"
                                    >
                                        <PlayCircle size={14} />
                                        继续
                                    </button>

                                    <div className="w-px h-4 bg-slate-700 mx-1"></div>

                                    {selectedBatch && selectedBatch.breakdown_status === 'pending' ? (
                                        <button
                                            onClick={() => handleStartBreakdownClick(selectedBatch.id)}
                                            disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning}
                                            className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-bold shadow-lg shadow-emerald-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <Play size={14} />
                                            开始拆解
                                        </button>
                                    ) : selectedBatch && selectedBatch.breakdown_status === 'failed' ? (
                                        <button
                                            onClick={() => handleStartBreakdownClick(selectedBatch.id)}
                                            disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning}
                                            className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white rounded-lg text-xs font-bold shadow-lg transition-all hover:scale-[1.02] disabled:opacity-50"
                                        >
                                            <RotateCcw size={14} />
                                            重试拆解
                                        </button>
                                    ) : selectedBatch && selectedBatch.breakdown_status === 'completed' ? (
                                        <button
                                            onClick={() => handleStartBreakdownClick(selectedBatch.id)}
                                            disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning}
                                            className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-lg text-xs font-bold shadow-lg transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <RotateCcw size={14} />
                                            重新拆解
                                        </button>
                                    ) : (
                                        <button disabled className="flex items-center gap-2 px-4 py-1.5 bg-slate-800 text-slate-500 rounded-lg text-xs font-bold border border-slate-700 opacity-50 cursor-not-allowed">
                                            <Play size={14} />
                                            开始拆解
                                        </button>
                                    )}
                                </div>
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
                <div className={`flex-1 overflow-hidden relative ${(activeTab === 'SCRIPT' || activeTab === 'SOURCE' || activeTab === 'PLOT') ? 'p-0' : 'p-6 md:p-8'}`}>
                     {renderContent()}
                </div>

                {/* Overlays */}
                <ConsoleLogger
                    logs={logs}
                    llmStats={llmStats}
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

            {/* Chapter Import Modal */}
            <Modal
                open={isUploadModalOpen}
                onCancel={() => {
                    setIsUploadModalOpen(false);
                    setUploadChapterFile(null);
                }}
                onOk={handleUploadChapter}
                title={
                    <div className="flex items-center gap-2 text-white">
                        <Upload size={18} className="text-cyan-400" />
                        <span>导入章节</span>
                    </div>
                }
                okText={uploading ? '上传中...' : '确认导入'}
                cancelText="取消"
                confirmLoading={uploading}
                centered
                width={420}
                closeIcon={<X size={18} className="text-slate-500 hover:text-white transition-colors" />}
                className="dark-modal"
                styles={{
                    mask: { backgroundColor: 'rgba(0, 0, 0, 0.85)', backdropFilter: 'blur(4px)' },
                    content: {
                        backgroundColor: '#0f172a',
                        border: '1px solid #334155',
                        borderRadius: '16px',
                        padding: '0',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px rgba(6, 182, 212, 0.1)'
                    },
                    header: {
                        backgroundColor: '#0f172a',
                        borderBottom: '1px solid #1e293b',
                        padding: '16px 24px',
                        borderRadius: '16px 16px 0 0'
                    },
                    body: {
                        backgroundColor: '#0f172a',
                        padding: '20px 24px'
                    },
                    footer: {
                        backgroundColor: '#0f172a',
                        borderTop: '1px solid #1e293b',
                        padding: '16px 24px',
                        borderRadius: '0 0 16px 16px'
                    }
                }}
                okButtonProps={{
                    style: {
                        backgroundColor: '#0891b2',
                        borderColor: '#0891b2',
                        fontWeight: 600,
                        boxShadow: '0 0 20px rgba(8, 145, 178, 0.3)'
                    },
                    disabled: !uploadChapterFile
                }}
                cancelButtonProps={{
                    style: {
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        color: '#94a3b8',
                        fontWeight: 500
                    }
                }}
            >
                <div className="space-y-5">
                    {/* 提示信息 */}
                    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                        <p className="text-sm text-slate-300 leading-relaxed">
                            导入的章节将自动追加到当前选择的章节
                            {selectedChapter ? (
                                <span className="inline-flex items-center mx-1.5 px-2.5 py-1 bg-cyan-500/10 text-cyan-400 rounded-lg border border-cyan-500/20 font-mono text-xs">
                                    Chapter {String(selectedChapter.chapter_number).padStart(2, '0')} · {selectedChapter.title}
                                </span>
                            ) : (
                                <span className="mx-1 text-amber-400">（请先选择章节）</span>
                            )}
                            后
                        </p>
                    </div>

                    {/* 文件选择区域 */}
                    <label className="block cursor-pointer">
                        <div className={`flex flex-col items-center justify-center w-full h-36 border-2 border-dashed rounded-xl transition-all group ${
                            uploadChapterFile
                            ? 'border-cyan-500/50 bg-cyan-500/5'
                            : 'border-slate-700 hover:border-cyan-500/50 bg-slate-800/30 hover:bg-slate-800/50'
                        }`}>
                            <input
                                type="file"
                                accept=".txt"
                                onChange={handleModalFileSelect}
                                className="hidden"
                            />
                            {uploadChapterFile ? (
                                <div className="flex items-center gap-4 px-4">
                                    <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20">
                                        <BookText size={24} className="text-cyan-400" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-white font-medium truncate">{uploadChapterFile.name}</p>
                                        <p className="text-xs text-slate-500 mt-0.5">{(uploadChapterFile.size / 1024).toFixed(2)} KB</p>
                                    </div>
                                    <div className="text-[10px] text-cyan-400 bg-cyan-500/10 px-2 py-1 rounded-full border border-cyan-500/20">
                                        已选择
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div className="w-14 h-14 rounded-full bg-slate-800 group-hover:bg-cyan-500/10 flex items-center justify-center transition-colors mb-3 border border-slate-700 group-hover:border-cyan-500/30">
                                        <Upload size={24} className="text-slate-500 group-hover:text-cyan-400 transition-colors" />
                                    </div>
                                    <p className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors font-medium">点击选择文件</p>
                                    <p className="text-xs text-slate-600 mt-1.5">仅限 .txt 文件，最大 1MB</p>
                                </>
                            )}
                        </div>
                    </label>
                </div>
            </Modal>

            {/* Breakdown Config Modal */}
            <Modal
                open={isBreakdownModalOpen}
                onCancel={() => setIsBreakdownModalOpen(false)}
                onOk={handleConfirmBreakdown}
                title={
                    <div className="flex items-center gap-2 text-white">
                        <BrainCircuit size={18} className="text-cyan-400" />
                        <span>剧情拆解配置</span>
                    </div>
                }
                okText="开始拆解"
                cancelText="取消"
                centered
                width={500}
                closeIcon={<X size={18} className="text-slate-500 hover:text-white transition-colors" />}
                className="dark-modal"
                styles={{
                    mask: { backgroundColor: 'rgba(0, 0, 0, 0.85)', backdropFilter: 'blur(4px)' },
                    content: {
                        backgroundColor: '#0f172a',
                        border: '1px solid #334155',
                        borderRadius: '16px',
                        padding: '0',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px rgba(6, 182, 212, 0.1)'
                    },
                    header: {
                        backgroundColor: '#0f172a',
                        borderBottom: '1px solid #1e293b',
                        padding: '16px 24px',
                        borderRadius: '16px 16px 0 0'
                    },
                    body: {
                        backgroundColor: '#0f172a',
                        padding: '20px 24px'
                    },
                    footer: {
                        backgroundColor: '#0f172a',
                        borderTop: '1px solid #1e293b',
                        padding: '16px 24px',
                        borderRadius: '0 0 16px 16px'
                    }
                }}
                okButtonProps={{
                    style: {
                        backgroundColor: '#0891b2',
                        borderColor: '#0891b2',
                        fontWeight: 600,
                        boxShadow: '0 0 20px rgba(8, 145, 178, 0.3)'
                    }
                }}
                cancelButtonProps={{
                    style: {
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        color: '#94a3b8',
                        fontWeight: 500
                    }
                }}
            >
                <div className="space-y-4">
                    {/* 积分说明提示 */}
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 flex gap-3 items-start">
                        <div className="mt-0.5">
                            <Zap size={16} className="text-amber-400" />
                        </div>
                        <div className="text-xs text-amber-300 leading-relaxed">
                            <span className="font-bold block mb-1 text-amber-200">积分扣除说明</span>
                            任务启动时会预扣剧集配额，<span className="font-bold text-amber-100">积分将在任务成功完成后扣除</span>（基础消耗 10 积分）。如果任务失败，配额和积分都会自动回滚。
                        </div>
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 flex gap-3 items-start">
                        <div className="mt-0.5">
                            <Sparkles size={16} className="text-blue-400" />
                        </div>
                        <div className="text-xs text-blue-300 leading-relaxed">
                            <span className="font-bold block mb-1 text-blue-200">选择挂载的 AI 技能</span>
                            不同的技能组合会影响拆解的维度和消耗的 Token。建议根据小说类型选择合适的技能。
                        </div>
                    </div>

                    <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                        <SkillSelector
                            category="breakdown"
                            selectedSkillIds={selectedBreakdownSkills}
                            onChange={setSelectedBreakdownSkills}
                        />
                    </div>

                    {/* 配置选择器 */}
                    <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-3 flex gap-3 items-start">
                        <div className="mt-0.5">
                            <Settings size={16} className="text-purple-400" />
                        </div>
                        <div className="text-xs text-purple-300 leading-relaxed">
                            <span className="font-bold block mb-1 text-purple-200">改编方法与质检规则</span>
                            选择适配方法（冲突提取标准）、质检规则（8维度评分）和输出风格（起承转钩）。可使用系统默认配置或自定义配置。
                        </div>
                    </div>

                    <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                        <ConfigSelector
                            value={breakdownConfig}
                            onChange={setBreakdownConfig}
                        />
                    </div>
                </div>
            </Modal>

            {/* 错误提示模态框 */}
            <Modal
                open={showErrorModal}
                onCancel={() => {
                    setShowErrorModal(false);
                    setParsedError(null);
                }}
                footer={null}
                centered
                width={400}
                closeIcon={<X size={18} className="text-slate-500 hover:text-white transition-colors" />}
                className="error-modal"
                styles={{
                    mask: { backgroundColor: 'rgba(0, 0, 0, 0.85)', backdropFilter: 'blur(4px)' },
                    content: {
                        backgroundColor: '#0f172a',
                        border: '1px solid #334155',
                        borderRadius: '16px',
                        padding: '0',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
                    },
                    header: {
                        backgroundColor: '#0f172a',
                        borderBottom: 'none',
                        padding: '24px 24px 0',
                        borderRadius: '16px 16px 0 0'
                    },
                    body: {
                        backgroundColor: '#0f172a',
                        padding: '16px 24px 24px'
                    },
                    footer: {
                        borderTop: 'none',
                        padding: '0 24px 24px'
                    }
                }}
            >
                <div className="text-center">
                    {/* 错误图标 */}
                    <div className="mx-auto w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mb-4">
                        <X size={32} className="text-red-400" />
                    </div>

                    {/* 标题 */}
                    <h3 className="text-lg font-medium text-white mb-2">拆解任务失败</h3>

                    {/* 错误信息 */}
                    <div className="bg-slate-800/50 rounded-lg p-3 mb-6">
                        <p className="text-sm text-slate-300 leading-relaxed">
                            {parsedError?.message || '未知错误'}
                        </p>
                        {parsedError?.code && (
                            <p className="text-xs text-slate-500 mt-2 font-mono">
                                错误码: {parsedError.code}
                            </p>
                        )}
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex justify-center gap-3">
                        {parsedError?.action === 'upgrade' && (
                            <button
                                onClick={() => navigate('/pricing')}
                                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-sm font-medium transition-all hover:scale-[1.02]"
                            >
                                升级套餐
                            </button>
                        )}
                        {parsedError?.action === 'configure' && (
                            <button
                                onClick={() => {
                                    setShowErrorModal(false);
                                    navigate('/admin/ai-config');
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium border border-slate-700 transition-colors"
                            >
                                修改配置
                            </button>
                        )}
                        {parsedError?.canRetry && (
                            <button
                                onClick={() => {
                                    setShowErrorModal(false);
                                    setParsedError(null);
                                    // 重试当前选中的批次
                                    if (selectedBatch) {
                                        handleStartBreakdownClick(selectedBatch.id);
                                    }
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white rounded-lg text-sm font-medium transition-all hover:scale-[1.02]"
                            >
                                <RotateCcw size={14} />
                                重新尝试
                            </button>
                        )}
                        <button
                            onClick={() => {
                                setShowErrorModal(false);
                                setParsedError(null);
                            }}
                            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium border border-slate-700 transition-colors"
                        >
                            关闭
                        </button>
                    </div>
                </div>
            </Modal>
        </div>

    );
};

export default Workspace;
