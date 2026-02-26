import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Settings, FileEdit, Play,
  BrainCircuit, Layers, Users,
  Terminal, LayoutTemplate,
  BookText, Save, Loader2, X, XCircle,
  RotateCcw, PlayCircle, FastForward, Zap,
  Upload, AlertTriangle
} from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import ConsoleLogger from '../../../components/ConsoleLogger';
import AICopilot from '../../../components/AICopilot';
import AgentConfigModal from '../../../components/modals/AgentConfigModal';
import ConfirmModal from '../../../components/modals/ConfirmModal';
import { UserTier, Batch, PlotBreakdown } from '../../../types';
import { projectApi, breakdownApi } from '../../../services/api';
import { message, Modal } from 'antd';
import { useConsoleLogger } from '../../../hooks/useConsoleLogger';
import { useBreakdownWebSocket } from '../../../hooks/useBreakdownWebSocket';
import { parseErrorMessage } from '../../../utils/errorParser';
import ConfigTab from './ConfigTab';
import SourceTab from './SourceTab';
import PlotTab from './PlotTab';
import ScriptTab from './ScriptTab';
import AgentsTab from './AgentsTab';
import SkillsTab from './SkillsTab';
import MethodViewModal from './PlotTab/MethodViewModal';
import { BATCH_STATUS, TASK_STATUS } from '../../../constants/status';

interface ProjectWorkspaceProps {
  userTier: UserTier;
}

type Tab = 'CONFIG' | 'SOURCE' | 'AGENTS' | 'SKILLS' | 'PLOT' | 'SCRIPT';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: string;
  model: string;
  desc: string;
  temperature?: number;
  systemPrompt?: string;
  tools?: string[];
}

const initialAgents: Agent[] = [
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

const SidebarItem = ({ icon: Icon, label, active, onClick, disabled, title }: { icon: any, label: string, active: boolean, onClick: () => void, disabled?: boolean, title?: string }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    title={title}
    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 border ${
      active
        ? 'bg-gradient-to-r from-blue-600/20 to-cyan-600/20 text-cyan-400 border-cyan-500/20'
        : disabled
          ? 'border-transparent text-slate-600 cursor-not-allowed'
          : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800'
    }`}
  >
    <Icon size={18} className={active ? 'text-cyan-400' : disabled ? 'text-slate-600' : 'text-slate-500'} />
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

    // 🔧 优化：根据项目状态设置初始 Tab，避免短暂渲染 CONFIG Tab 导致额外 API 调用
    const getInitialTab = (projectStatus?: string): Tab => {
        const statusTabMap: Record<string, Tab> = {
            'draft': 'CONFIG',
            'uploaded': 'CONFIG',
            'ready': 'CONFIG',
            'parsing': 'PLOT',
            'scripting': 'SCRIPT',
            'completed': 'SCRIPT'
        };
        return statusTabMap[projectStatus || ''] || 'CONFIG';
    };

    const [activeTab, setActiveTab] = useState<Tab>(() => getInitialTab(project?.status));
    const [hasAutoNavigated, setHasAutoNavigated] = useState(false); // 标记是否已自动跳转
    const [showConsole, setShowConsole] = useState(false);
    const [showCopilot, setShowCopilot] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);

    // Form Data
    const [formData, setFormData] = useState({
        name: '',
        novel_type: '悬疑/惊悚',
        description: '',
        batch_size: 6,
        chapter_split_rule: 'auto',
        breakdown_model: 'DeepNarrative-Pro',
        script_model: 'Gemini-1.5-Pro'
    });

    // Config State
    const [agents, setAgents] = useState(initialAgents);
    const [selectedAgent, setSelectedAgent] = useState<any>(null);

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
    const [executingBatchId, setExecutingBatchId] = useState<string | null>(null);  // 当前正在执行的批次 ID
    const [breakdownProgress, setBreakdownProgress] = useState(0);
    const [breakdownCurrentStep, setBreakdownCurrentStep] = useState('');
    const [breakdownCompleted, setBreakdownCompleted] = useState(false);
    const [isCreatingBatches, setIsCreatingBatches] = useState(false);
    const [isAllBreakdownRunning, setIsAllBreakdownRunning] = useState(false);

    // 批量拆解状态（全局进度，从 API 获取）
    const [batchProgress, setBatchProgress] = useState<{
        total_batches: number;
        completed: number;
        in_progress: number;
        pending: number;
        failed: number;
        overall_progress: number;
    } | null>(null);
    const [isBatchRunning, setIsBatchRunning] = useState(false);
    const [taskCompleted, setTaskCompleted] = useState(false);

    // Script Tab 剧集生成进度状态
    const [scriptProgress, setScriptProgress] = useState<{
        total: number;
        completed: number;
        in_progress: number;
        pending: number;
        failed: number;
    }>({
        total: 0,
        completed: 0,
        in_progress: 0,
        pending: 0,
        failed: 0
    });

    // Script Tab 操作函数
    const [scriptActions, setScriptActions] = useState<{
        handleGenerateAll: () => void;
        handleContinueGenerate: () => void;
        handleRegenerateCurrent: () => void;
        handleRegenerateAll: () => void;
        handleStopBatchGenerate: () => void;
        handleStopGenerate: () => void;  // 停止单集生成
        isBatchProcessing: boolean;
        isGenerating: boolean;  // 单集生成状态
    } | null>(null);


    useEffect(() => {
        // 只有在控制台打开且没有正在执行的任务时才重置进度
        // 但如果任务已完成，则保持显示完成状态
        if (showConsole && !breakdownTaskId && !taskCompleted) {
            setBreakdownProgress(0);
            setBreakdownCurrentStep('');
        }
    }, [showConsole, breakdownTaskId, taskCompleted]);

    // 停止任务状态
    const [isStopping, setIsStopping] = useState(false);
    const [showStopConfirmModal, setShowStopConfirmModal] = useState(false);

    // 执行模式选择弹窗状态（测试用）
    const [showExecutionModeModal, setShowExecutionModeModal] = useState(false);
    const [pendingBreakdownBatchId, setPendingBreakdownBatchId] = useState<string | null>(null);

    // 自动保存状态（用于显示光效）
    const [isAutoSaving, setIsAutoSaving] = useState(false);
    const [showSaveGlow, setShowSaveGlow] = useState(false);

    // 错误提示状态
    const [showErrorModal, setShowErrorModal] = useState(false);
    const [parsedError, setParsedError] = useState<{
        code: string;
        message: string;
        canRetry: boolean;
        action?: 'upgrade' | 'retry' | 'skip' | 'configure';
    } | null>(null);

    // 存储键
    const STORAGE_KEY = 'breakdown_config';

    // 从 localStorage 读取拆解配置
    const loadBreakdownConfig = () => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const config = JSON.parse(saved);
                // 兼容新旧格式：新格式使用 selectedResourceIds，旧格式使用 breakdownConfig
                const resourceIds = config.selectedResourceIds || config.breakdownConfig || [];
                return {
                    selectedBreakdownSkills: config.selectedBreakdownSkills || [],
                    breakdownConfig: resourceIds
                };
            }
        } catch (err) {
            console.error('加载拆解配置失败:', err);
        }
        return { selectedBreakdownSkills: [], breakdownConfig: [] };
    };

    // 获取拆解结果（带重试机制和指数退避）
    const fetchBreakdownResults = async (batchId: string, retryCount = 0) => {
        if (retryCount === 0) {
            setBreakdownLoading(true);
        }

        console.log(`[fetchBreakdownResults] 开始获取拆解结果, batchId: ${batchId}, 重试次数: ${retryCount}`);

        try {
            const res = await breakdownApi.getBreakdownResults(batchId);
            console.log('[fetchBreakdownResults] 获取成功:', res.data);
            setBreakdownResult(res.data);
            setBreakdownLoading(false);
        } catch (err: any) {
            console.error('[fetchBreakdownResults] 获取失败:', err);
            console.error('[fetchBreakdownResults] 错误详情:', {
                status: err.response?.status,
                statusText: err.response?.statusText,
                data: err.response?.data,
                message: err.message
            });

            // 如果是 404 或 500，且重试次数未达上限，自动重试
            if ((err.response?.status === 404 || err.response?.status === 500) && retryCount < 5) {
                const retryDelay = Math.pow(2, retryCount) * 1000; // 指数退避：1s, 2s, 4s, 8s, 16s
                console.log(`[fetchBreakdownResults] ${retryDelay / 1000}秒后重试 (${retryCount + 1}/5)...`);
                setTimeout(() => {
                    fetchBreakdownResults(batchId, retryCount + 1);
                }, retryDelay);
            } else if (err.response?.status === 401) {
                // 认证失败
                console.error('[fetchBreakdownResults] 认证失败，请重新登录');
                message.error('认证失败，请重新登录');
                setBreakdownResult(null);
                setBreakdownLoading(false);
            } else {
                console.error('[fetchBreakdownResults] 获取拆解结果失败，已达最大重试次数');
                message.error('获取拆解结果失败，请刷新页面重试');
                setBreakdownResult(null);
                setBreakdownLoading(false);
            }
        }
    };

    // Method View Modal State
    const [methodViewModalOpen, setMethodViewModalOpen] = useState(false);
    const [viewingMethodId, setViewingMethodId] = useState<string | null>(null);

    // PLOT Pagination State
    const [batchPage, setBatchPage] = useState(1);
    const [batchHasMore, setBatchHasMore] = useState(true);
    const [loadingBatches, setLoadingBatches] = useState(false);

    // 使用 useConsoleLogger Hook 管理日志（禁用内置 WebSocket，避免重复连接）
    const {
        logs,
        llmStats,
        addLog,
        appendStreamLog,
        clearLogs,
        finalizeStreamLog
    } = useConsoleLogger(null, { enableWebSocket: false });

    // 使用 WebSocket Hook 监听任务进度（优先使用 WebSocket，失败时降级到轮询）
    const lastStepRef = useRef<string>('');
    const pollingIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollIntervalTimeRef = useRef<number>(2000); // 动态轮询间隔

    const { isConnected: wsConnected, progress: wsProgress, currentStep: wsCurrentStep, usePolling, currentRound, totalRounds } = useBreakdownWebSocket(
        breakdownTaskId,
        {
            onProgress: (data) => {
                console.log('[Workspace] 收到进度更新:', data);
                setBreakdownProgress(data.progress || 0);

                // 去重日志：只在步骤变化时添加
                if (data.current_step && data.current_step !== lastStepRef.current) {
                    addLog('thinking', data.current_step);
                    lastStepRef.current = data.current_step;
                }
            },
            onComplete: async () => {
                setBreakdownTaskId(null);
                setExecutingBatchId(null);  // 清空当前执行批次
                message.success('拆解完成');
                // 由 useEffect 统一触发 fetchBreakdownResults
                await fetchBatches();
                // 🔧 新增：批次完成后更新全局进度
                await fetchGlobalProgress();
                // ✅ 新增：检测是否有下一个任务（全部拆解模式）
                console.log('[Workspace] 批次完成，检测是否有下一个任务...');
                setTimeout(async () => {
                    await autoDetectProcessingTask();
                }, 1000);
            },
            onError: (error) => {
                setBreakdownTaskId(null);
                setExecutingBatchId(null);  // 清空当前执行批次
                const parsedError = parseErrorMessage(error);
                showError(parsedError);
                // 🔧 新增：批次失败后更新全局进度
                fetchGlobalProgress();
            },
            fallbackToPolling: false,  // 🔧 调试模式：禁用降级轮询

            // 来自 useBreakdownLogs 的回调
            onStepStart: (stepName, metadata) => {
                console.log('[StreamLogs] 步骤开始:', stepName, metadata);
                setShowConsole(true);  // 🔧 关键修复：收到第一条日志时自动打开 Console
                addLog('thinking', `🚀 ${stepName}`);
                setBreakdownCurrentStep(stepName);
                const header = buildFormattedSectionHeader(stepName);
                if (header) {
                    addLog('formatted', header);
                }
            },
            onStreamChunk: (stepName, chunk) => {
                // RAW 模式：直接追加内容，确保 JSON 连续显示
                appendStreamLog(chunk);
            },
            onFormattedChunk: (stepName, chunk) => {
                // 实时显示格式化内容（Formatted 模式）
                console.log('[StreamLogs] 格式化内容:', chunk);
                addLog('formatted', chunk);
            },
            onStepEnd: (stepName, result) => {
                console.log('[StreamLogs] 步骤完成:', stepName, result);
                // 结束当前流式日志，确保下一步骤的内容不会追加到当前日志
                finalizeStreamLog();
                addLog('success', `✅ ${stepName} 完成`);
            },
            onWarning: (warning) => {
                console.warn('[StreamLogs] 警告:', warning);
                addLog('warning', `⚠️ ${warning}`);
            },
            onInfo: (info) => {
                console.log('[StreamLogs] 信息:', info);
                addLog('info', info);
            },
            onSuccess: (msg) => {
                console.log('[StreamLogs] 成功:', msg);
                addLog('success', `✅ ${msg}`);
                if (msg.includes('Agent 完成')) {
                    handleBreakdownCompleted(msg);
                }
            },
            onBatchSwitch: async (switchInfo) => {
                console.log('[Workspace] 收到批次切换消息:', switchInfo);

                try {
                    // ✅ 修复：刷新当前选中的批次数据（完成后会变为 COMPLETED）
                    if (selectedBatch) {
                        await refreshBatch(selectedBatch.id);
                    }
                    // ✅ 修复：刷新新批次数据（状态变为 IN_PROGRESS）
                    await refreshBatch(switchInfo.newBatchId);

                    // ✅ 修复：使用 switchToTaskBatch 统一处理批次切换
                    await switchToTaskBatch({
                        task_id: switchInfo.newTaskId,
                        batch_id: switchInfo.newBatchId,
                        batch_number: switchInfo.newBatchNumber
                    }, { silent: false });

                    // 更新全局进度
                    await fetchGlobalProgress();
                } catch (err) {
                    console.error('[Workspace] 批次切换失败:', err);
                    message.error('批次切换失败');
                }
            },
            // ✅ 新增：WebSocket 关闭时检测是否有正在处理的任务
            onClose: async () => {
                console.log('[Workspace] WebSocket 关闭，检测是否有正在处理的任务...');
                // 先清空当前任务ID，否则 autoDetectProcessingTask 会跳过检测
                setBreakdownTaskId(null);
                setExecutingBatchId(null);
                // 等待一下，确保后端已经创建下一个任务
                setTimeout(async () => {
                    await autoDetectProcessingTask();
                }, 2000);
            }
        }
    );

    const normalizeStepTitle = (stepName: string) => {
        if (stepName.includes('剧情拆解质量校验') || stepName.includes('质量校验') || stepName.includes('质量检查') || stepName.includes('质检')) {
            return '质量检查';
        }
        if (stepName.includes('网文改编剧情拆解') || stepName.includes('剧情拆解') || stepName.includes('剧集拆解')) {
            return '剧集拆解';
        }
        return '';
    };

    const buildFormattedSectionHeader = (stepName: string) => {
        const title = normalizeStepTitle(stepName);
        if (!title) return '';
        return `------\n${title} Agent 正在运行中...\n------\n\n`;
    };

    const handleBreakdownCompleted = (messageText?: string) => {
        if (breakdownCompleted) return;
        setBreakdownCompleted(true);
        setTaskCompleted(true);  // 标记任务已完成
        setBreakdownTaskId(null);
        setExecutingBatchId(null);  // 清空当前执行批次
        setBreakdownProgress(100);
        setBreakdownCurrentStep('已完成');
        if (messageText) {
            addLog('formatted', messageText);
        }
        message.success('拆解完成');
        // ✅ 修复：使用 refreshBatch 精准刷新当前批次
        if (selectedBatch) {
            refreshBatch(selectedBatch.id);
        }
        // 🔧 新增：批次完成后更新全局进度
        fetchGlobalProgress();
    };

    // 监听 selectedBatch 变化，只处理状态同步和清理
    // 不触发 fetchBreakdownResults（避免重复调用）
    // 🔧 优化：合并批次选择和状态变化的逻辑，避免重复调用
    const prevBatchIdRef = React.useRef<string | null>(null);
    const prevBatchStatusRef = React.useRef<string | null>(null);

    useEffect(() => {
        if (!selectedBatch) return;

        const currentId = selectedBatch.id;
        const currentStatus = selectedBatch.breakdown_status;
        const prevId = prevBatchIdRef.current;
        const prevStatus = prevBatchStatusRef.current;

        // 切换批次时先清空旧结果
        if (currentId !== prevId) {
            setBreakdownResult(null);
        }

        const isRunning = currentStatus === BATCH_STATUS.IN_PROGRESS || currentStatus === BATCH_STATUS.QUEUED;

        if (!isRunning) {
            setBreakdownTaskId(null);
            setExecutingBatchId(null);
        }

        // 🔧 关键优化：只在以下情况加载拆解结果，避免重复
        // 1. 切换到一个已完成的批次（id 变化 && 状态是 completed）
        // 2. 当前批次状态变为完成（id 不变 && 状态从非 completed 变为 completed）
        const shouldLoadResults =
            currentStatus === BATCH_STATUS.COMPLETED && (
                currentId !== prevId ||  // 切换批次
                prevStatus !== BATCH_STATUS.COMPLETED  // 状态变化
            );

        if (shouldLoadResults) {
            console.log('[Workspace] 加载拆解结果:', {
                batchId: selectedBatch.id,
                reason: currentId !== prevId ? '切换批次' : '状态变为完成'
            });
            setBreakdownLoading(true);
            fetchBreakdownResults(selectedBatch.id);
        }

        // 更新上一个状态
        prevBatchIdRef.current = currentId;
        prevBatchStatusRef.current = currentStatus;
    }, [selectedBatch?.id, selectedBatch?.breakdown_status]);

    // 批次列表更新时，同步选中批次状态（避免完成后仍显示停止按钮）
    useEffect(() => {
        if (!selectedBatch) return;
        const latest = batches.find(b => b.id === selectedBatch.id);
        if (!latest) return;
        if (latest.breakdown_status !== selectedBatch.breakdown_status) {
            console.log('[Workspace] 批次状态变化，同步选中批次状态:', latest.breakdown_status);
            setSelectedBatch(latest);
        }
    }, [batches, selectedBatch?.id]);

    // 处理 processing/queued 状态但缺少 taskId 的情况
    useEffect(() => {
        if (!selectedBatch) return;
        if (breakdownTaskId) return;
        if (selectedBatch.breakdown_status !== BATCH_STATUS.IN_PROGRESS && selectedBatch.breakdown_status !== BATCH_STATUS.QUEUED) return;

        (async () => {
            try {
                const taskRes = await breakdownApi.getBatchCurrentTask(selectedBatch.id);
                const taskId = taskRes.data?.task_id;
                if (taskId) {
                    setBreakdownTaskId(taskId);
                    addLog('info', `已关联批次 ${selectedBatch.batch_number} 的任务: ${taskId}`);
                }
            } catch (err) {
                console.warn('[Workspace] 获取当前批次任务失败:', err);
            }
        })();
    }, [selectedBatch?.id, selectedBatch?.breakdown_status, breakdownTaskId]);

    // 当 WebSocket 降级到轮询时，启动优化的轮询机制
    // 🔧 调试模式：暂时禁用降级轮询，以便调试 WebSocket
    /*
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
    */

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
                if (status === TASK_STATUS.QUEUED) {
                    pollIntervalTimeRef.current = 3000; // 排队中，降低频率
                } else if (status === TASK_STATUS.RUNNING) {
                    pollIntervalTimeRef.current = 1500; // 运行中，提高频率

                    // 任务开始执行时，刷新批次列表（更新状态从 QUEUED 到 PROCESSING）
                    fetchBatches();
                } else if (status === TASK_STATUS.RETRYING) {
                    pollIntervalTimeRef.current = 5000; // 重试中，降低频率
                }

                // 任务完成
                if (status === TASK_STATUS.COMPLETED) {
                    if (pollingIntervalRef.current) {
                        clearTimeout(pollingIntervalRef.current);
                        pollingIntervalRef.current = null;
                    }
                    setBreakdownTaskId(null);
                    setExecutingBatchId(null);  // 清空当前执行批次
                    message.success('拆解完成');
                    // 由 useEffect 统一触发 fetchBreakdownResults
                    fetchBatches();
                    // 🔧 新增：任务完成后更新全局进度
                    fetchGlobalProgress();
                    return;
                }

                // 任务失败
                if (status === TASK_STATUS.FAILED) {
                    if (pollingIntervalRef.current) {
                        clearTimeout(pollingIntervalRef.current);
                        pollingIntervalRef.current = null;
                    }
                    setBreakdownTaskId(null);
                    setExecutingBatchId(null);  // 清空当前执行批次

                    const errorMsg = res.data.error_message || '拆解失败';
                    const parsedError = parseErrorMessage(errorMsg);
                    showError(parsedError);
                    // 🔧 新增：任务失败后更新全局进度
                    fetchGlobalProgress();
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
        // 显示全局 loading 提示
        const hideLoading = message.loading('正在创建批次，请稍候...', 0);
        try {
            // 调用后端创建批次接口（幂等）
            await projectApi.createBatches(projectId);
            // 创建完成后获取列表
            await fetchBatches(1, false);
        } catch (err) {
            console.error('创建批次失败:', err);
            message.error('创建批次失败');
        } finally {
            hideLoading();
            setIsCreatingBatches(false);
        }
    };

    // 🔧 新增：刷新单个批次数据（精准刷新，不影响分页）
    const refreshBatch = useCallback(async (batchId: string) => {
        if (!projectId) return;

        try {
            // 使用 getBatches 获取当前页数据，然后找到目标批次
            const res = await projectApi.getBatches(projectId, batchPage, 20);
            const freshBatches = res.data?.items || [];

            // 找到目标批次
            const updatedBatch = freshBatches.find((b: any) => b.id === batchId);

            if (updatedBatch) {
                // 更新批次列表中的该批次数据
                setBatches(prev => prev.map(b =>
                    b.id === batchId ? updatedBatch : b
                ));
                console.log(`[Workspace] 已刷新批次 ${batchId} 的数据`);
            } else {
                console.warn(`[Workspace] 批次 ${batchId} 不在当前页面`);
            }
        } catch (err) {
            console.error(`[Workspace] 刷新批次 ${batchId} 失败:`, err);
        }
    }, [projectId, batchPage]);

    // 🔧 提取：根据 current_task 切换到目标批次（统一逻辑，解决分页问题）
    const switchToTaskBatch = async (currentTask: any, options: { silent?: boolean } = {}) => {
        if (!currentTask || !currentTask.task_id) return;

        // 防重复：如果已经连接到该任务，跳过
        if (breakdownTaskId === currentTask.task_id) {
            if (!options.silent) {
                console.log('[Workspace] 已连接到任务:', currentTask.task_id);
            }
            return;
        }

        console.log('[Workspace] 切换到任务批次:', currentTask);

        // 检查批次是否在当前列表中
        let targetBatch = batches.find((b: Batch) => b.id === currentTask.batch_id);

        if (!targetBatch && currentTask.batch_number) {
            // 批次不在当前列表，加载包含该批次的页面
            const pageNum = Math.ceil(currentTask.batch_number / 20);
            console.log(`[Workspace] 批次 ${currentTask.batch_number} 不在当前列表，加载第 ${pageNum} 页`);

            try {
                const batchRes = await projectApi.getBatches(projectId!, pageNum, 20);
                const pageItems = batchRes.data?.items || [];

                // 🔧 关键修复：更新批次列表和分页状态
                setBatches(pageItems);
                setBatchTotal(batchRes.data?.total || 0);
                setBatchHasMore((pageNum * 20) < (batchRes.data?.total || 0));
                setBatchPage(pageNum);  // ✅ 修复：同步更新当前页码

                targetBatch = pageItems.find((b: Batch) => b.id === currentTask.batch_id);
            } catch (err) {
                console.error('[Workspace] 加载批次页面失败:', err);
                return;
            }
        } else if (targetBatch) {
            // ✅ 修复：批次在当前列表中，刷新该批次数据获取最新状态
            await refreshBatch(currentTask.batch_id);
            // 重新获取 targetBatch（已更新）
            targetBatch = batches.find((b: Batch) => b.id === currentTask.batch_id);
        }

        if (targetBatch) {
            // 提示用户（只在批次切换时，且非静默模式）
            if (!options.silent && (!selectedBatch || selectedBatch.id !== targetBatch.id)) {
                message.info(`已自动跳转到正在拆解的批次：第 ${currentTask.batch_number} 批次`);
            }

            setSelectedBatch(targetBatch);
            setBreakdownTaskId(currentTask.task_id);
            setShowConsole(true);

            if (!options.silent) {
                addLog('info', `检测到批次 ${currentTask.batch_number} 正在拆解中，已自动连接...`);
            }
        } else {
            console.warn('[Workspace] 未找到目标批次:', currentTask.batch_id);
        }
    };

    // 🔧 优化：使用全局进度 API 检测正在处理的任务（解决分页问题）
    const autoDetectProcessingTask = async (progressData?: any) => {
        if (breakdownTaskId) return; // 已有任务连接，跳过检测

        try {
            // 🔧 优化：如果已有进度数据，直接使用，避免重复调用 API
            const progress = progressData || (await breakdownApi.getBatchProgress(projectId!)).data;
            await switchToTaskBatch(progress?.current_task);
        } catch (err) {
            console.warn('[Workspace] 检测正在处理的任务失败:', err);
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
                } else if (selectedBatch) {
                    const latest = newItems.find((b: any) => b.id === selectedBatch.id);
                    if (latest && latest.breakdown_status !== selectedBatch.breakdown_status) {
                        setSelectedBatch(latest);
                    }
                }

                // 🔧 优化：先获取全局进度，再复用数据检测任务（避免重复调用 API）
                if (pageNum === 1) {
                    const progress = await fetchGlobalProgress();
                    await autoDetectProcessingTask(progress);
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

    // 获取全局进度（从 API 获取准确的统计数据）
    const fetchGlobalProgress = async () => {
        if (!projectId) return null;
        try {
            const res = await breakdownApi.getBatchProgress(projectId);
            console.log('[Workspace] 获取全局进度:', res.data);
            setBatchProgress(res.data);
            return res.data;  // 🔧 返回数据，供其他函数复用
        } catch (err) {
            console.error('[Workspace] 获取全局进度失败:', err);
            // 失败时使用降级显示，不影响用户体验
            setBatchProgress(null);
            return null;
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
                novel_type: res.data.novel_type || '悬疑/惊悚',
                description: res.data.description || '',
                batch_size: res.data.batch_size || 6,
                chapter_split_rule: 'auto',
                breakdown_model: res.data.breakdown_model_id || '',  // 使用后端返回的模型 ID
                script_model: res.data.script_model_id || ''  // 使用后端返回的模型 ID
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
                // 如果是第一页且没有选中章节，自动选择第一章
                if (pageNum === 1 && !selectedChapter && newItems.length > 0) {
                    setSelectedChapter(newItems[0]);
                }
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

        // 校验必填项
        if (!formData.breakdown_model) {
            message.error('请选择拆解模型');
            return;
        }
        if (!formData.script_model) {
            message.error('请选择剧本模型');
            return;
        }

        setSaving(true);
        try {
            await projectApi.updateProject(projectId, {
                name: formData.name,
                novel_type: formData.novel_type,
                description: formData.description,
                batch_size: formData.batch_size,
                breakdown_model_id: formData.breakdown_model,  // 传递模型 ID
                script_model_id: formData.script_model  // 传递模型 ID
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
        let isMounted = true;

        const loadProject = async () => {
            if (isMounted && projectId) {
                await fetchProject();
            }
        };

        loadProject();

        return () => {
            isMounted = false;
        };
    }, [projectId]);

    // 监听 SkillsTab 自动保存状态
    useEffect(() => {
        const handleSaveStatus = (e: CustomEvent<{ saving: boolean; savedAt?: Date }>) => {
            if (e.detail.saving) {
                setIsAutoSaving(true);
            } else {
                setIsAutoSaving(false);
                // 保存完成后显示光效
                setShowSaveGlow(true);
                setTimeout(() => setShowSaveGlow(false), 1500);
            }
        };

        window.addEventListener('skillsTabSaveStatus', handleSaveStatus as EventListener);
        return () => {
            window.removeEventListener('skillsTabSaveStatus', handleSaveStatus as EventListener);
        };
    }, []);

    // 根据项目状态自动跳转到对应标签页（仅首次加载时）
    useEffect(() => {
        if (!project || hasAutoNavigated) return;

        // 根据项目状态决定默认标签页
        const statusTabMap: Record<string, Tab> = {
            'draft': 'CONFIG',
            'uploaded': 'CONFIG',
            'ready': 'CONFIG',
            'parsing': 'PLOT',
            'scripting': 'SCRIPT',
            'completed': 'SCRIPT'
        };

        const defaultTab = statusTabMap[project.status] || 'CONFIG';
        setActiveTab(defaultTab);
        setHasAutoNavigated(true); // 标记已完成自动跳转
    }, [project?.status, hasAutoNavigated]);

    // 搜索监听
    useEffect(() => {
        if (activeTab === 'SOURCE') {
            setPage(1);
            fetchChapters(1, false);
        }
    }, [keyword]);

    // 监听 Tab 切换加载数据（合并后的唯一版本）
    useEffect(() => {
        if (activeTab === 'SOURCE') {
            fetchChapters();
        }
        if (activeTab === 'PLOT') {
            // 进入 PLOT 页面时，先检查项目状态
            if (project?.status !== 'ready' && project?.status !== 'parsing') {
                // 状态不正确，提示并跳转到 CONFIG 页面
                if (project?.status === 'uploaded') {
                    message.warning('请先完成章节拆分');
                } else if (project?.status === 'draft') {
                    message.warning('请先上传文件');
                } else {
                    message.warning('项目状态不允许进入此页面');
                }
                setActiveTab('CONFIG');
                return;
            }
            // 🔧 优化：先获取批次列表，复用结果避免重复请求
            (async () => {
                setLoadingBatches(true);
                try {
                    const res = await projectApi.getBatches(projectId!, 1, 20);
                    const total = res.data?.total || 0;

                    if (total === 0) {
                        // 批次不存在，需要创建
                        await createBatchesAndFetch();
                    } else {
                        // 🔧 关键优化：复用第一次请求的结果，避免重复调用
                        const newItems = res.data?.items || [];

                        setBatchTotal(total);
                        setBatches(newItems);
                        setBatchHasMore((1 * 20) < total);

                        if (newItems.length > 0 && !selectedBatch) {
                            setSelectedBatch(newItems[0]);
                        }

                        // 🔧 优化：获取全局进度并复用结果，避免重复调用
                        const progressData = await fetchGlobalProgress();

                        // 自动检测正在处理的任务（复用进度数据）
                        await autoDetectProcessingTask(progressData);
                    }
                } catch (err) {
                    console.error('获取批次列表失败:', err);
                    message.error('获取批次列表失败');
                } finally {
                    setLoadingBatches(false);
                }
            })();
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

    // 启动拆解任务 - 弹出模式选择弹窗
    const handleStartBreakdownClick = (batchId: string) => {
        setPendingBreakdownBatchId(batchId);
        setShowExecutionModeModal(true);
    };

    // 确认执行模式后启动拆解
    const handleConfirmExecutionMode = async (mode: string) => {
        setShowExecutionModeModal(false);
        if (!pendingBreakdownBatchId) return;

        const batchId = pendingBreakdownBatchId;
        setPendingBreakdownBatchId(null);

        // 从 SkillsTab 保存的配置中读取
        const config = loadBreakdownConfig();

        try {
            // 自动弹出 Console
            setShowConsole(true);
            clearLogs();
            lastStepRef.current = ''; // 重置步骤记录
            setTaskCompleted(false);  // 重置任务完成标志
            setBreakdownCompleted(false);  // 重置拆解完成标志
            addLog('info', `配置已加载，执行模式: ${mode}，开始拆解批次 ${selectedBatch?.batch_number || ''}...`);

            const res = await breakdownApi.startBreakdown(batchId, {
                selectedSkills: config.selectedBreakdownSkills,
                resourceIds: config.breakdownConfig,
                novelType: formData.novel_type,
                executionMode: mode  // 传递执行模式
            });
            setBreakdownTaskId(res.data.task_id);
            setExecutingBatchId(batchId);  // 记录当前正在执行的批次
            message.info('拆解任务已启动');

            // 刷新批次列表，显示当前正在拆解的批次
            fetchBatches();
            // 🔧 新增：启动拆解后更新全局进度
            fetchGlobalProgress();

            // 更新 selectedBatch 状态为 processing/queued，使按钮显示"停止拆解"
            if (selectedBatch && selectedBatch.id === batchId) {
                setSelectedBatch({
                    ...selectedBatch,
                    breakdown_status: BATCH_STATUS.IN_PROGRESS
                });
            }

            // WebSocket 会自动连接，如果失败会降级到轮询
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || '启动拆解失败';
            message.error(errorMsg);
            showError({ code: 'START_FAILED', message: errorMsg });

            if (errorMsg.includes('上一批次')) {
                const firstBlocking = batches.find(b => b.breakdown_status !== BATCH_STATUS.COMPLETED);
                if (firstBlocking) {
                    message.info(`需按顺序拆解，已跳转到第 ${firstBlocking.batch_number} 批次`);
                    setSelectedBatch(firstBlocking);
                }
            }
        }
    };

    // 全部拆解：一次性启动所有 pending 和 failed 批次（增强版）
    const handleAllBreakdown = async () => {
        if (!projectId) return;

        // 🔧 修改：使用全局进度判断是否有待拆解批次
        const hasPendingBatches = batchProgress
            ? (batchProgress.pending + batchProgress.failed) > 0
            : batches.filter(b => b.breakdown_status === BATCH_STATUS.PENDING || b.breakdown_status === BATCH_STATUS.FAILED).length > 0;

        if (!hasPendingBatches) {
            message.info('没有待拆解的批次');
            return;
        }
        setShowConsole(true);
        setIsBatchRunning(true);

        try {
            const config = loadBreakdownConfig();
            const res = await breakdownApi.startBatchBreakdown({
                projectId,
                resourceIds: config.breakdownConfig
            });

            if (res.data.total > 0) {
                message.info(`已启动 ${res.data.total} 个拆解任务`);

                // ✅ 设置 taskId 以触发 WebSocket 连接
                if (res.data.task_ids && res.data.task_ids.length > 0) {
                    setBreakdownTaskId(res.data.task_ids[0]);  // 监听第一个任务
                }

                // 刷新批次列表，显示当前正在拆解的批次（fetchBatches 内部已包含全局进度获取）
                await fetchBatches();
                // ✅ 修复：移除轮询，完全依赖 WebSocket 推送
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

    // 继续拆解：从第一个 pending 或 failed 批次开始
    const handleContinueBreakdown = async () => {
        if (!projectId) return;
        const firstNeedBreakdown = batches.find(b => b.breakdown_status === BATCH_STATUS.PENDING || b.breakdown_status === BATCH_STATUS.FAILED);
        if (!firstNeedBreakdown) {
            message.info('没有待拆解的批次');
            return;
        }
        // 先更新选中批次并设置状态为 processing
        setSelectedBatch({
            ...firstNeedBreakdown,
            breakdown_status: BATCH_STATUS.IN_PROGRESS
        });
        try {
             setShowConsole(true);
             clearLogs();
             lastStepRef.current = '';
             // 从 SkillsTab 保存的配置中读取
             const config = loadBreakdownConfig();
             const res = await breakdownApi.startBreakdown(firstNeedBreakdown.id, {
                 selectedSkills: config.selectedBreakdownSkills,
                 resourceIds: config.breakdownConfig,
                 novelType: formData.novel_type
             });
             setBreakdownCompleted(false);
             setBreakdownCurrentStep('');
             setBreakdownTaskId(res.data.task_id);
             // 刷新批次列表，显示当前正在拆解的批次
             fetchBatches();
             // 🔧 新增：启动继续拆解后更新全局进度
             fetchGlobalProgress();
             // WebSocket 会自动连接
        } catch (err: any) {
             // 失败时恢复状态
             setSelectedBatch(firstNeedBreakdown);
             const errorMsg = err.response?.data?.detail || '启动失败';
             message.error(errorMsg);
             showError({ code: 'START_FAILED', message: errorMsg });
        }
    };

    // 停止当前拆解任务
    const handleStopCurrentBreakdown = () => {
        if (!breakdownTaskId) return;
        setShowStopConfirmModal(true);
    };

    // 执行停止操作
    const handleConfirmStop = async () => {
        if (!breakdownTaskId) return;
        setIsStopping(true);
        try {
            const res = await breakdownApi.stopBreakdown(breakdownTaskId);
            const { message: resMessage, token_deducted } = res.data;

            // 构建成功消息
            let successMsg = resMessage || '已停止拆解任务';
            if (token_deducted > 0) {
                successMsg += `（扣除 ${token_deducted} 积分）`;
            }
            message.success(successMsg);

            setBreakdownTaskId(null);
            setExecutingBatchId(null);  // 清空当前执行批次
            setBreakdownProgress(0);
            setShowStopConfirmModal(false);
            // 刷新批次列表以更新状态
            fetchBatches();
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || '停止任务失败';
            message.error(errorMsg);
        } finally {
            setIsStopping(false);
        }
    };

    // 触发文件选择
    const triggerFileUpload = () => {
        fileInputRef.current?.click();
    };

    // 处理项目文件上传
    const handleProjectFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !projectId) return;

        setUploading(true);
        try {
            await projectApi.uploadFile(projectId, file);
            message.success('文件上传成功！');

            // 刷新项目数据以更新文件信息
            const p = await projectApi.getProject(projectId);
            if (p.data) setProject(p.data);
        } catch (error: any) {
            console.error('文件上传失败:', error);
            const errorMsg = error.response?.data?.detail || '文件上传失败，请重试';
            message.error(errorMsg);
        } finally {
            setUploading(false);
            // 清空 input 值，允许重复上传同一文件
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    // 智能拆分章节
    const handleSplit = async () => {
        if (!projectId) return;
        setSplitting(true);
        setIsProcessing(true);
        // 显示全局 loading 提示
        const hideLoading = message.loading('正在拆分章节，请稍候...', 0);
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
            hideLoading();
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
                        onStopBreakdown={handleStopCurrentBreakdown}
                        isCreatingBatches={isCreatingBatches}
                        loadingBatches={loadingBatches}
                        breakdownTaskId={breakdownTaskId}
                        breakdownProgress={breakdownProgress}
                        breakdownResult={breakdownResult}
                        breakdownLoading={breakdownLoading}
                        onBatchScroll={handleBatchScroll}
                        onViewMethod={(methodId) => {
                            setViewingMethodId(methodId);
                            setMethodViewModalOpen(true);
                        }}
                    />
                );
            case 'SCRIPT':
                return (
                    <ScriptTab
                        projectId={projectId!}
                        projectName={formData.name}
                        batchId={selectedBatch?.id}
                        breakdownId={selectedBatch?.id}
                        novelType={formData.novel_type}
                        onProgressUpdate={(progress) => {
                            setScriptProgress(progress);
                        }}
                        onActionsReady={(actions) => {
                            setScriptActions(actions);
                        }}
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
            {/* 隐藏的项目文件上传 input */}
            <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.docx,.pdf"
                onChange={handleProjectFileUpload}
                className="hidden"
            />

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
                             <SidebarItem icon={LayoutTemplate} label="剧集拆解 (Plot)" active={activeTab === 'PLOT'} onClick={() => setActiveTab('PLOT')} disabled={project.status !== 'ready' && project.status !== 'parsing'} title={project.status === 'uploaded' ? '请先完成章节拆分' : project.status === 'draft' ? '请先上传文件' : ''} />
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
                {activeTab !== 'SOURCE' && (
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
                                            <Zap size={16} className={batches.some(b => b.breakdown_status === BATCH_STATUS.COMPLETED) ? 'text-amber-400 fill-amber-400/20' : ''} />
                                        )}
                                    </div>

                                    {/* 能量条进度 */}
                                    <div className="flex flex-col gap-1.5 w-40 group">
                                        <div className="flex justify-between items-end px-0.5">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest group-hover:text-slate-400 transition-colors">
                                                {isAllBreakdownRunning ? '处理中' : '拆解进度'}
                                            </span>
                                            <span className={`text-[10px] font-mono font-bold ${isAllBreakdownRunning ? 'text-cyan-400' : 'text-emerald-500'}`}>
                                                {batchProgress?.completed || 0}/{batchProgress?.total_batches || batchTotal}
                                            </span>
                                        </div>
                                        <div className="h-1.5 w-full bg-slate-800/80 rounded-full overflow-hidden border border-slate-700/30 p-[1px]">
                                            <div
                                                className={`h-full rounded-full transition-all duration-700 ease-out relative overflow-hidden ${
                                                    isAllBreakdownRunning
                                                    ? 'bg-gradient-to-r from-cyan-500 to-blue-500'
                                                    : 'bg-gradient-to-r from-emerald-600 to-teal-400'
                                                }`}
                                                style={{width: `${batchProgress?.total_batches ? (batchProgress.completed / batchProgress.total_batches) * 100 : 0}%`}}
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

                            {/* SCRIPT Tab: 剧集生成进度展示在 Header 左侧 */}
                            {activeTab === 'SCRIPT' && scriptProgress.total > 0 && (
                                <div className="ml-6 hidden md:flex items-center gap-3 animate-in fade-in slide-in-from-left-4 duration-500">
                                    {/* 简约图标 */}
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-500 ${
                                        scriptProgress.in_progress > 0
                                        ? 'bg-cyan-500/10 text-cyan-400 shadow-[0_0_15px_-3px_rgba(6,182,212,0.4)]'
                                        : 'bg-slate-800/80 text-slate-500 border border-slate-700/50'
                                    }`}>
                                        {scriptProgress.in_progress > 0 ? (
                                            <Loader2 size={16} className="animate-spin" />
                                        ) : (
                                            <FileEdit size={16} className={scriptProgress.completed > 0 ? 'text-amber-400' : ''} />
                                        )}
                                    </div>

                                    {/* 能量条进度 */}
                                    <div className="flex flex-col gap-1.5 w-40 group">
                                        <div className="flex justify-between items-end px-0.5">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest group-hover:text-slate-400 transition-colors">
                                                {scriptProgress.in_progress > 0 ? '生成中' : '剧本进度'}
                                            </span>
                                            <span className={`text-[10px] font-mono font-bold ${scriptProgress.in_progress > 0 ? 'text-cyan-400' : 'text-emerald-500'}`}>
                                                {scriptProgress.completed}/{scriptProgress.total}
                                            </span>
                                        </div>
                                        <div className="h-1.5 w-full bg-slate-800/80 rounded-full overflow-hidden border border-slate-700/30 p-[1px]">
                                            <div
                                                className={`h-full rounded-full transition-all duration-700 ease-out relative overflow-hidden ${
                                                    scriptProgress.in_progress > 0
                                                    ? 'bg-gradient-to-r from-cyan-500 to-blue-500'
                                                    : 'bg-gradient-to-r from-emerald-600 to-teal-400'
                                                }`}
                                                style={{width: `${scriptProgress.total > 0 ? (scriptProgress.completed / scriptProgress.total) * 100 : 0}%`}}
                                            >
                                                {/* 流光特效 */}
                                                {scriptProgress.in_progress > 0 && (
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
                                        disabled={saving || !formData.breakdown_model || !formData.script_model}
                                        title={!formData.breakdown_model ? '请先选择拆解模型' : !formData.script_model ? '请先选择剧本模型' : ''}
                                        className="flex items-center gap-2 px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-lg border border-slate-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-slate-800 disabled:text-slate-500"
                                    >
                                        {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                        {saving ? '保存中...' : '保存设置'}
                                    </button>
                                    <button
                                        onClick={handleStart}
                                        disabled={project.status !== 'ready' || starting}
                                        title={project.status !== 'ready' ? '请先完成章节拆分' : !formData.breakdown_model || !formData.script_model ? '请先选择模型' : ''}
                                        className={`flex items-center gap-2 px-6 py-1.5 text-xs font-bold rounded-lg shadow-lg transition-all relative overflow-hidden ${
                                            project.status === 'parsing'
                                            ? 'bg-slate-800 text-slate-400 border-2 border-cyan-500/50 cursor-not-allowed animate-pulse-border'
                                            : project.status === 'ready'
                                            ? 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white shadow-cyan-500/20 hover:scale-105 cursor-pointer'
                                            : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
                                        }`}
                                    >
                                        {/* 流光效果 - 仅在 parsing 状态显示 */}
                                        {project.status === 'parsing' && (
                                            <>
                                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent animate-shimmer" />
                                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/30 to-transparent animate-shimmer-reverse" />
                                            </>
                                        )}
                                        <span className="relative z-10 flex items-center gap-2">
                                            {starting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
                                            {starting ? '启动中...' : (project.status === 'parsing' ? '正在运行' : '项目启动')}
                                        </span>
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
                                                        strokeDasharray={`${(batchProgress?.overall_progress || 0) * 0.75} 75`}
                                                        className="transition-all duration-500"
                                                    />
                                                </svg>
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-xs text-blue-300 font-medium">
                                                    批量拆解中 {batchProgress?.completed || 0}/{batchProgress?.total_batches || 0}
                                                </span>
                                                <div className="flex gap-2 text-[10px]">
                                                    <span className="text-green-400">{batchProgress?.completed || 0} 成功</span>
                                                    <span className="text-yellow-400">{batchProgress?.in_progress || 0} 进行</span>
                                                    <span className="text-red-400">{batchProgress?.failed || 0} 失败</span>
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
                                        onClick={handleAllBreakdown}
                                        disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning || (batchProgress ? (batchProgress.pending + batchProgress.failed) === 0 : batches.filter(b => b.breakdown_status === BATCH_STATUS.PENDING || b.breakdown_status === BATCH_STATUS.FAILED).length === 0)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white border border-purple-500/30 rounded-lg text-xs font-bold shadow-lg shadow-purple-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                                        title="一次性启动所有待处理批次"
                                    >
                                        <FastForward size={14} />
                                        全部拆解
                                    </button>
                                    <button
                                        onClick={handleContinueBreakdown}
                                        disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning || (batchProgress ? (batchProgress.pending + batchProgress.failed) === 0 : batches.filter(b => b.breakdown_status === BATCH_STATUS.PENDING || b.breakdown_status === BATCH_STATUS.FAILED).length === 0)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white border border-teal-500/30 rounded-lg text-xs font-bold shadow-lg shadow-teal-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                                        title="跳转到第一个待处理批次并开始拆解"
                                    >
                                        <PlayCircle size={14} />
                                        继续拆解
                                    </button>

                                    <div className="w-px h-4 bg-slate-700 mx-1"></div>

                                    {/* 当前有任务在执行时显示停止按钮 */}
                                    {breakdownTaskId ? (
                                        <button
                                            onClick={handleStopCurrentBreakdown}
                                            disabled={isStopping}
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white border border-red-500/30 rounded-lg text-xs font-bold shadow-lg shadow-red-900/20 transition-all hover:scale-[1.02] disabled:opacity-70 disabled:cursor-not-allowed"
                                        >
                                            {isStopping ? (
                                                <>
                                                    <Loader2 size={14} className="animate-spin" />
                                                    停止中...
                                                </>
                                            ) : (
                                                <>
                                                    <X size={14} />
                                                    停止拆解
                                                </>
                                            )}
                                        </button>
                                    ) : selectedBatch && selectedBatch.breakdown_status === BATCH_STATUS.PENDING ? (
                                        <button
                                            onClick={() => handleStartBreakdownClick(selectedBatch.id)}
                                            disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning}
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border border-emerald-500/30 rounded-lg text-xs font-bold shadow-lg shadow-emerald-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <Play size={14} />
                                            开始拆解
                               </button>
                                    ) : selectedBatch && selectedBatch.breakdown_status === BATCH_STATUS.FAILED ? (
                                        <button
                                            onClick={() => handleStartBreakdownClick(selectedBatch.id)}
                                            disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning}
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white border border-orange-500/30 rounded-lg text-xs font-bold shadow-lg shadow-orange-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <RotateCcw size={14} />
                                            重试拆解
                                        </button>
                                    ) : selectedBatch && selectedBatch.breakdown_status === BATCH_STATUS.COMPLETED ? (
                                        <button
                                            onClick={() => handleStartBreakdownClick(selectedBatch.id)}
                                            disabled={!!breakdownTaskId || isAllBreakdownRunning || isBatchRunning}
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white border border-blue-500/30 rounded-lg text-xs font-bold shadow-lg transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
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
                            ) : (activeTab as Tab) === 'SCRIPT' ? (
                                <div className="flex items-center gap-3">
                                    {(scriptActions?.isBatchProcessing || scriptActions?.isGenerating) ? (
                                        // 生成中 - 显示停止按钮
                                        <button
                                            onClick={() => scriptActions?.isBatchProcessing
                                                ? scriptActions?.handleStopBatchGenerate()
                                                : scriptActions?.handleStopGenerate()
                                            }
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white border border-red-500/30 rounded-lg text-xs font-bold shadow-lg shadow-red-900/20 transition-all hover:scale-[1.02]"
                                            title="停止生成"
                                        >
                                            <XCircle size={14} />
                                            停止生成
                                        </button>
                                    ) : (
                                        <>
                                            <button
                                                onClick={() => scriptActions?.handleGenerateAll()}
                                                disabled={!scriptActions || scriptProgress.pending === 0}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white border border-indigo-500/30 rounded-lg text-xs font-bold shadow-lg shadow-indigo-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                                                title="一次性生成所有待处理剧集"
                                            >
                                                <FastForward size={14} />
                                                全部生成
                                            </button>
                                            <button
                                                onClick={() => scriptActions?.handleContinueGenerate()}
                                                disabled={!scriptActions || scriptProgress.pending === 0}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white border border-emerald-500/30 rounded-lg text-xs font-bold shadow-lg shadow-emerald-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                                                title="跳转到第一个待处理剧集并开始生成"
                                            >
                                                <PlayCircle size={14} />
                                                继续生成
                                            </button>

                                            <div className="w-px h-4 bg-slate-700 mx-1"></div>

                                            <button
                                                onClick={() => scriptActions?.handleRegenerateCurrent()}
                                                disabled={!scriptActions || scriptProgress.total === 0}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white border border-sky-500/30 rounded-lg text-xs font-bold shadow-lg shadow-sky-900/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
                                                title="重新生成当前选中的剧集"
                                            >
                                                <RotateCcw size={14} />
                                                重新生成
                                            </button>
                                        </>
                                    )}
                                </div>
                            ) : (activeTab as Tab) === 'SOURCE' ? (
                                <></>
                            ) : (
                                <>
                                    <div className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium transition-all rounded-lg ${
                                        isAutoSaving
                                            ? 'text-cyan-400 bg-cyan-500/10'
                                            : 'text-slate-400'
                                    }`}>
                                        {isAutoSaving ? (
                                            <Loader2 size={14} className="animate-spin" />
                                        ) : (
                                            <Save size={14} />
                                        )}
                                        {isAutoSaving ? '保存中...' : '自动保存'}
                                    </div>
                                    <div className="h-4 w-px bg-slate-700"></div>
                                    <button
                                        onClick={() => {
                                            window.dispatchEvent(new CustomEvent('skillsTabManualSave'));
                                            setShowSaveGlow(true);
                                            setTimeout(() => setShowSaveGlow(false), 1500);
                                        }}
                                        className={`relative flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-lg transition-all ${
                                            showSaveGlow ? 'shadow-cyan-500/50 shadow-xl ring-2 ring-cyan-400/30' : 'shadow-cyan-500/20'
                                        }`}
                                    >
                                        {/* 保存完成提示 */}
                                        {showSaveGlow && (
                                            <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                                        )}
                                        <Save size={12} className="relative z-10" />
                                        <span className="relative z-10">保存配置</span>
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
                    isProcessing={!!breakdownTaskId}
                    progress={breakdownProgress}
                    currentStep={breakdownCurrentStep}
                    currentRound={currentRound}
                    totalRounds={totalRounds}
                    batchNumber={selectedBatch?.batch_number || 0}
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
                    mask: { backgroundColor: 'rgba(0, 0, 0, 0.4)', backdropFilter: 'blur(2px)' },
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

            {/* 方法论查看弹窗 */}
            <AnimatePresence>
                {methodViewModalOpen && viewingMethodId && (
                    <MethodViewModal
                        methodId={viewingMethodId}
                        onClose={() => {
                            setMethodViewModalOpen(false);
                            setViewingMethodId(null);
                        }}
                    />
                )}
            </AnimatePresence>

            {/* 确认弹窗 */}
            <ConfirmModal
                open={showStopConfirmModal}
                onCancel={() => setShowStopConfirmModal(false)}
                onConfirm={handleConfirmStop}
                title="确认停止拆解"
                content={
                    <div className="text-left">
                        <p className="text-slate-300 mb-4">
                            {selectedBatch ? (
                                <>确定要停止批次 <span className="text-blue-400 font-semibold">{selectedBatch.batch_number}</span> 的拆解任务吗？</>
                            ) : (
                                '确定要停止当前拆解任务吗？'
                            )}
                        </p>
                        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                            <div className="flex gap-3 items-start">
                                <div className="mt-0.5">
                                    <AlertTriangle size={16} className="text-amber-400" />
                                </div>
                                <div className="text-xs text-amber-300 leading-relaxed">
                                    <span className="font-semibold block mb-1 text-amber-200">停止后将取消排队中的后续任务</span>
                                    已排队的批次将自动取消，您可以稍后重新启动拆解流程。
                                </div>
                            </div>
                        </div>
                    </div>
                }
                confirmText="确认停止"
                confirmType="danger"
                iconType="danger"
                loading={isStopping}
            />

            {/* 执行模式选择弹窗（测试用） */}
            {showExecutionModeModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-slate-900 rounded-xl p-6 w-96 border border-slate-700 shadow-2xl">
                        <h3 className="text-white font-bold mb-2 text-lg">选择执行模式</h3>
                        <p className="text-slate-500 text-xs mb-5">测试功能：对比不同执行模式的效果</p>
                        <div className="space-y-3">
                            <button
                                onClick={() => handleConfirmExecutionMode('agent_loop')}
                                className="w-full p-4 bg-slate-800 hover:bg-slate-700 rounded-xl text-left transition-all border border-slate-700 hover:border-slate-600"
                            >
                                <div className="text-cyan-400 font-semibold mb-1">Agent 全量循环</div>
                                <div className="text-xs text-slate-500 leading-relaxed">
                                    内部最多3轮循环，每轮全量重生成<br/>
                                    <span className="text-amber-400/80">Token 消耗高，修正效果一般</span>
                                </div>
                            </button>
                            <button
                                onClick={() => handleConfirmExecutionMode('agent_single')}
                                className="w-full p-4 bg-cyan-500/10 hover:bg-cyan-500/20 rounded-xl text-left transition-all border border-cyan-500/30 hover:border-cyan-500/50 relative"
                            >
                                <div className="absolute top-3 right-3 px-2 py-0.5 bg-cyan-500/20 text-cyan-400 text-[10px] font-bold rounded-full border border-cyan-500/30">
                                    推荐
                                </div>
                                <div className="text-cyan-400 font-semibold mb-1">Agent 单轮 + Skill 修正</div>
                                <div className="text-xs text-slate-400 leading-relaxed">
                                    Agent 跑1轮生成初版，后续局部修正<br/>
                                    <span className="text-emerald-400/80">Token 消耗适中，修正精准</span>
                                </div>
                            </button>
                            <button
                                onClick={() => handleConfirmExecutionMode('skill_only')}
                                className="w-full p-4 bg-slate-800 hover:bg-slate-700 rounded-xl text-left transition-all border border-slate-700 hover:border-slate-600"
                            >
                                <div className="text-cyan-400 font-semibold mb-1">纯 Skill 模式</div>
                                <div className="text-xs text-slate-500 leading-relaxed">
                                    不用 Agent，直接 Skill + 外部质检修正<br/>
                                    <span className="text-blue-400/80">Token 消耗最低，速度最快</span>
                                </div>
                            </button>
                        </div>
                        <button
                            onClick={() => {
                                setShowExecutionModeModal(false);
                                setPendingBreakdownBatchId(null);
                            }}
                            className="mt-5 w-full p-2.5 text-slate-500 hover:text-slate-300 text-sm rounded-lg hover:bg-slate-800 transition-colors"
                        >
                            取消
                        </button>
                    </div>
                </div>
            )}
        </div>

    );
};

export default Workspace;
