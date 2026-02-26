import axios from 'axios';
import { mockProjects, mockLogs, mockUser } from './mockData';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
// 增强判断：打印日志并支持字符串或布尔值
const rawMockEnv = import.meta.env.VITE_USE_MOCK as string | boolean | undefined;
const USE_MOCK = String(rawMockEnv) === 'true';

console.log('[API Config] Base URL:', API_BASE_URL);
console.log('[API Config] Mock Mode:', USE_MOCK, `(Raw: ${rawMockEnv})`);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const projectApi = {
  getProjects: async () => {
    if (USE_MOCK) {
      await delay(500);
      return { data: mockProjects };
    }
    return api.get('/projects');
  },
  
  getProject: async (id: string) => {
    if (USE_MOCK) {
      await delay(300);
      const project = mockProjects.find(p => p.id === id);
      return { data: project || null };
    }
    const response = await api.get(`/projects/${id}`);
    console.log('[API DEBUG] getProject response:', response.data); // 打印完整响应
    return { data: response.data };
  },
  
  createProject: async (data: { name: string; novel_type?: string; description?: string; batch_size?: number }) => {
    if (USE_MOCK) {
      await delay(500);
      const newProject = {
        id: String(mockProjects.length + 1),
        name: data.name,
        novel_type: data.novel_type || '未知',
        description: data.description || '',
        batch_size: data.batch_size || 10,
        type: data.novel_type || '未知',
        updated_at: '刚刚',
        status: 'draft',
        progress: 0,
        total_chapters: data.batch_size || 10,
        processed_chapters: 0,
        scripted_chapters: 0
      };
      mockProjects.push(newProject);
      return { data: newProject };
    }
    return api.post('/projects', data);
  },
  
  updateProject: async (id: string, data: any) => {
    if (USE_MOCK) {
      await delay(300);
      const index = mockProjects.findIndex(p => p.id === id);
      if (index !== -1) {
        mockProjects[index] = { ...mockProjects[index], ...data };
        return { data: mockProjects[index] };
      }
      return { data: null };
    }
    return api.put(`/projects/${id}`, data);
  },
  
  deleteProject: async (id: string) => {
    if (USE_MOCK) {
      await delay(300);
      const index = mockProjects.findIndex(p => p.id === id);
      if (index !== -1) {
        mockProjects.splice(index, 1);
      }
      return { data: { success: true } };
    }
    return api.delete(`/projects/${id}`);
  },
  
  uploadFile: async (id: string, file: File) => {
    if (USE_MOCK) {
      await delay(1000);
      return { data: { success: true, message: '文件上传成功' } };
    }
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/projects/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  splitChapters: async (id: string) => {
    if (USE_MOCK) {
      await delay(1000);
      return { data: { message: '拆分成功', total_chapters: 45 } };
    }
    return api.post(`/projects/${id}/split`);
  },

  startProject: async (id: string) => {
    if (USE_MOCK) {
      await delay(500);
      return { data: { status: 'parsing' } };
    }
    return api.post(`/projects/${id}/start`);
  },

  getBatches: async (projectId: string, page: number = 1, pageSize: number = 20) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          items: [],
          total: 0
        }
      };
    }
    const response = await api.get(`/projects/${projectId}/batches`, {
      params: { page, page_size: pageSize }
    });
    return { data: response.data };
  },

  // 创建批次（幂等，进入 PLOT 页面时调用）
  createBatches: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(500);
      return { data: { message: '批次已存在', created: false } };
    }
    return api.post(`/projects/${projectId}/create-batches`);
  },

  getChapters: async (projectId: string, page = 1, pageSize = 20, keyword?: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { items: [], total: 0 } };
    }
    const response = await api.get(`/projects/${projectId}/chapters`, {
      params: { page, page_size: pageSize, keyword }
    });
    return { data: response.data };
  },

  deleteChapter: async (projectId: string, chapterId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { success: true } };
    }
    return api.delete(`/projects/${projectId}/chapters/${chapterId}`);
  },

  uploadChapter: async (projectId: string, file: File, prevChapterId?: string) => {
    if (USE_MOCK) {
      await delay(1000);
      return { data: { success: true } };
    }
    const formData = new FormData();
    formData.append('file', file);
    if (prevChapterId) {
      formData.append('prev_chapter_id', prevChapterId);
    }
    return api.post(`/projects/${projectId}/chapters/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};

// 模型管理 API
export const modelsApi = {
  getModels: async () => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: [
          { id: 'm1', model_key: 'gpt-4o', display_name: 'GPT-4o (推荐)', pricing: { input_credits_per_1k: 5, output_credits_per_1k: 15 } },
          { id: 'm2', model_key: 'gpt-4-turbo', display_name: 'GPT-4 Turbo', pricing: { input_credits_per_1k: 10, output_credits_per_1k: 30 } },
          { id: 'm3', model_key: 'claude-3-5-sonnet', display_name: 'Claude 3.5 Sonnet', pricing: { input_credits_per_1k: 3, output_credits_per_1k: 15 } },
        ]
      };
    }
    return api.get('/models');
  }
};

export const logsApi = {
  getLogs: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(200);
      return { data: mockLogs };
    }
    return api.get(`/projects/${projectId}/logs`);
  }
};

export const userApi = {
  getProfile: async () => {
    if (USE_MOCK) {
      await delay(200);
      return { data: mockUser };
    }
    return api.get('/user/profile');
  }
};

// 剧情拆解 API
export const breakdownApi = {
  // 启动单个批次拆解
  startBreakdown: async (batchId: string, options?: {
    modelConfigId?: string;
    selectedSkills?: string[];
    pipelineId?: string;
    // 新版：资源 ID 列表（支持多选）
    resourceIds?: string[];
    // 旧版：单个资源 ID（保留兼容）
    adaptMethodId?: string;
    outputStyleId?: string;
    templateId?: string;
    adaptMethodKey?: string;
    qualityRuleKey?: string;
    outputStyleKey?: string;
    novelType?: string;
    // 执行模式：agent_loop / agent_single / skill_only
    executionMode?: string;
  }) => {
    if (USE_MOCK) {
      await delay(500);
      return { data: { task_id: 'mock-task-1', status: 'queued' } };
    }
    // 构建请求参数，只传有值的字段
    const params: Record<string, any> = {
      batch_id: batchId,
    };
    if (options?.modelConfigId) params.model_config_id = options.modelConfigId;
    if (options?.selectedSkills?.length) params.selected_skills = options.selectedSkills;
    if (options?.pipelineId) params.pipeline_id = options.pipelineId;
    if (options?.resourceIds?.length) params.resource_ids = options.resourceIds;
    if (options?.adaptMethodId) params.adapt_method_id = options.adaptMethodId;
    if (options?.outputStyleId) params.output_style_id = options.outputStyleId;
    if (options?.templateId) params.template_id = options.templateId;
    if (options?.adaptMethodKey) params.adapt_method_key = options.adaptMethodKey;
    if (options?.qualityRuleKey) params.quality_rule_key = options.qualityRuleKey;
    if (options?.outputStyleKey) params.output_style_key = options.outputStyleKey;
    if (options?.novelType) params.novel_type = options.novelType;
    if (options?.executionMode) params.execution_mode = options.executionMode;

    return api.post('/breakdown/start', params);
  },

  // 批量启动所有 pending 批次拆解
  startAllBreakdowns: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(500);
      return { data: { task_ids: [], total: 0 } };
    }
    return api.post('/breakdown/start-all', null, { params: { project_id: projectId } });
  },

  // 继续拆解：从第一个 pending 批次开始
  startContinue: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(500);
      return { data: { task_id: 'mock-task-1', batch_id: 'mock-batch-1', status: 'queued' } };
    }
    return api.post(`/breakdown/continue/${projectId}`);
  },

  // 获取任务状态
  getTaskStatus: async (taskId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { task_id: taskId, status: 'completed', progress: 100 } };
    }
    return api.get(`/breakdown/tasks/${taskId}`);
  },

  // 停止正在执行的任务
  stopBreakdown: async (taskId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { task_id: taskId, status: 'cancelled', message: '任务已停止' } };
    }
    return api.post(`/breakdown/tasks/${taskId}/stop`);
  },

  // 获取批次当前正在执行的任务
  getBatchCurrentTask: async (batchId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { task_id: null, status: 'pending' } };
    }
    return api.get(`/breakdown/batch/${batchId}/current-task`);
  },

  // 获取任务执行日志（包括 LLM 调用详情）
  getTaskLogs: async (taskId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          task_id: taskId,
          execution_id: 'mock-exec-1',
          execution_logs: [
            {
              timestamp: new Date().toISOString(),
              stage: 'breakdown',
              event: 'stage_start',
              message: '开始剧情拆解',
              detail: null
            },
            {
              timestamp: new Date().toISOString(),
              stage: 'breakdown',
              event: 'validator_result',
              message: 'LLM 调用: 一致性检查',
              detail: {
                validator_name: 'consistency_checker',
                status: 'passed',
                score: 85
              }
            },
            {
              timestamp: new Date().toISOString(),
              stage: 'breakdown',
              event: 'stage_completed',
              message: '剧情拆解完成',
              detail: null
            }
          ],
          llm_calls: {
            total: 1,
            stages: [
              {
                stage: 'breakdown',
                validator: 'consistency_checker',
                status: 'passed',
                score: 85,
                timestamp: new Date().toISOString()
              }
            ]
          },
          timeline: []
        }
      };
    }
    return api.get(`/breakdown/tasks/${taskId}/logs`);
  },

  // 获取拆解结果
  getBreakdownResults: async (batchId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          batch_id: batchId,
          format_version: 3,
          plot_points: [
            { id: 1, episode: 1, scene: '档案室', characters: ['主角'], event: '发现神秘档案', hook_type: '悬念', status: 'unused' },
            { id: 2, episode: 1, scene: '办公室', characters: ['主角', '上级'], event: '接受任务', hook_type: '挑战', status: 'used' },
            { id: 3, episode: 2, scene: '现场', characters: ['主角'], event: '调查取证', hook_type: '悬疑', status: 'unused' }
          ],
          qa_status: 'PASS',
          qa_score: 85,
          qa_report: null,
          qa_retry_count: 0,
          used_adapt_method_id: null,
          created_at: new Date().toISOString()
        }
      };
    }
    return api.get(`/breakdown/results/${batchId}`);
  },

  // 根据 breakdown_id 获取指定拆解记录的完整数据
  getBreakdownById: async (breakdownId: string) => {
    return api.get(`/breakdown/breakdown/${breakdownId}`);
  },

  // 获取可用的配置列表
  getAvailableConfigs: async () => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          adapt_methods: [
            { key: 'adapt_method_default', description: '网文改编漫剧方法论（系统默认）', is_custom: false }
          ],
          quality_rules: [
            { key: 'qa_breakdown_default', description: '剧情拆解质检标准（系统默认）', is_custom: false }
          ],
          output_styles: [
            { key: 'output_style_default', description: '漫剧输出风格（系统默认）', is_custom: false }
          ]
        }
      };
    }
    return api.get('/breakdown/available-configs');
  },

  // 批量启动拆解（增强版）
  startBatchBreakdown: async (options: {
    projectId: string;
    // 新版：资源 ID 列表（支持多选）
    resourceIds?: string[];
    // 旧版：单个资源 ID（保留兼容）
    adaptMethodId?: string;
    outputStyleId?: string;
    adaptMethodKey?: string;
    qualityRuleKey?: string;
    outputStyleKey?: string;
    concurrentLimit?: number;
  }) => {
    if (USE_MOCK) {
      await delay(500);
      const total = 5;
      return {
        data: {
          task_ids: Array.from({ length: total }, (_, i) => `mock-batch-task-${i}`),
          total,
          project_id: options.projectId,
          config: {
            resource_ids: options.resourceIds
          },
          message: `已启动 ${total} 个拆解任务`
        }
      };
    }
    // 构建请求参数，只传有值的字段
    const params: Record<string, any> = {
      project_id: options.projectId,
    };
    if (options.resourceIds?.length) params.resource_ids = options.resourceIds;
    if (options.adaptMethodId) params.adapt_method_id = options.adaptMethodId;
    if (options.outputStyleId) params.output_style_id = options.outputStyleId;
    if (options.adaptMethodKey) params.adapt_method_key = options.adaptMethodKey;
    if (options.qualityRuleKey) params.quality_rule_key = options.qualityRuleKey;
    if (options.outputStyleKey) params.output_style_key = options.outputStyleKey;
    if (options.concurrentLimit) params.concurrent_limit = options.concurrentLimit;

    return api.post('/breakdown/batch-start', params);
  },

  // 获取批量拆解进度
  getBatchProgress: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          project_id: projectId,
          total_batches: 10,
          completed: 3,
          in_progress: 2,
          pending: 4,
          failed: 1,
          overall_progress: 30,
          status_summary: {
            pending: 4,
            queued: 0,
            running: 2,
            retrying: 0,
            completed: 3,
            failed: 1
          },
          task_details: [],
          last_updated: new Date().toISOString()
        }
      };
    }
    return api.get(`/breakdown/batch-progress/${projectId}`);
  },

  // 重试失败的任务
  retryTask: async (taskId: string, newConfig?: {
    adaptMethodKey?: string;
    qualityRuleKey?: string;
    outputStyleKey?: string;
  }) => {
    if (USE_MOCK) {
      await delay(500);
      return {
        data: {
          task_id: `retry-${taskId}`,
          status: 'queued',
          retry_count: 1,
          batch_id: 'mock-batch-1',
          config: newConfig || {},
          message: '任务已重新加入队列（第 1 次尝试）'
        }
      };
    }
    return api.post(`/breakdown/tasks/${taskId}/retry`, {
      new_config: newConfig ? {
        adapt_method_key: newConfig.adaptMethodKey,
        quality_rule_key: newConfig.qualityRuleKey,
        output_style_key: newConfig.outputStyleKey
      } : undefined
    });
  },

  // 更新剧情点状态（v2 新格式）
  updatePlotPointStatus: async (batchId: string, pointId: number, status: 'used' | 'unused') => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { success: true, point_id: pointId, status } };
    }
    return api.patch(`/breakdown/results/${batchId}/plot-points/${pointId}`, { status });
  },

  // 获取拆解详情（模型、资源、质检信息等）
  getBreakdownDetail: async (batchId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          breakdown_id: 'mock-breakdown-1',
          batch_id: batchId,
          created_at: new Date().toISOString(),
          format_version: 3,
          model_info: {
            provider: 'openai',
            model_name: 'gpt-4-turbo',
            display_name: 'GPT-4 Turbo'
          },
          resource_info: {
            adapt_method: {
              id: 'mock-resource-1',
              name: 'adapt_method_default',
              display_name: '默认改编方法论'
            }
          },
          qa_status: 'PASS',
          qa_score: 85,
          qa_report: { score: 85, status: 'PASS' },
          qa_retry_count: 1,
          task_info: {
            task_id: 'mock-task-1',
            status: 'completed',
            started_at: new Date(Date.now() - 120000).toISOString(),
            completed_at: new Date().toISOString(),
            duration_seconds: 120,
            retry_count: 0
          }
        }
      };
    }
    return api.get(`/breakdown/results/${batchId}/detail`);
  },

  // 获取拆解历史列表（同一批次的多次拆解记录）
  getBreakdownHistory: async (batchId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          items: [
            {
              breakdown_id: 'mock-breakdown-2',
              batch_id: batchId,
              created_at: new Date().toISOString(),
              format_version: 3,
              model_info: { provider: 'openai', model_name: 'gpt-4-turbo', display_name: 'GPT-4 Turbo' },
              resource_info: { adapt_method: { id: 'r1', name: 'default', display_name: '默认方法论' } },
              qa_status: 'PASS',
              qa_score: 85,
              qa_report: null,
              qa_retry_count: 1,
              plot_points_count: 12,
              task_info: { task_id: 't2', status: 'completed', started_at: null, completed_at: null, duration_seconds: 95, retry_count: 0 }
            },
            {
              breakdown_id: 'mock-breakdown-1',
              batch_id: batchId,
              created_at: new Date(Date.now() - 3600000).toISOString(),
              format_version: 3,
              model_info: { provider: 'openai', model_name: 'gpt-4', display_name: 'GPT-4' },
              resource_info: {},
              qa_status: 'FAIL',
              qa_score: 58,
              qa_report: null,
              qa_retry_count: 0,
              plot_points_count: 8,
              task_info: { task_id: 't1', status: 'completed', started_at: null, completed_at: null, duration_seconds: 120, retry_count: 0 }
            }
          ]
        }
      };
    }
    return api.get(`/breakdown/results/${batchId}/history`);
  },

  // 获取项目的所有拆解结果
  getProjectBreakdowns: async (projectId: string, page: number = 1, pageSize: number = 20) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { items: [], total: 0, page: 1, page_size: 20 } };
    }
    return api.get('/breakdown/project-breakdowns', {
      params: { project_id: projectId, page, page_size: pageSize }
    });
  }
};

export const skillsApi = {
  // 获取可用技能
  getAvailableSkills: async (category?: string) => {
    if (USE_MOCK) {
      await delay(200);
      return {
        data: {
          skills: [
            { id: 's1', name: 'conflict_extraction', display_name: '冲突提取', description: '自动识别剧本中的核心冲突点', category: 'breakdown', is_active: true, is_builtin: true },
            { id: 's2', name: 'plot_hook_identification', display_name: '伏笔识别', description: '识别并标记剧情中的伏笔', category: 'breakdown', is_active: true, is_builtin: true },
            { id: 's3', name: 'character_analysis', display_name: '角色分析', description: '深度分析角色动机与心理', category: 'breakdown', is_active: true, is_builtin: true },
            { id: 's4', name: 'scene_identification', display_name: '场景切分', description: '识别场景转换与关键场景', category: 'breakdown', is_active: true, is_builtin: true },
            { id: 's5', name: 'emotion_extraction', display_name: '情感曲线', description: '分析剧情的情感起伏', category: 'breakdown', is_active: true, is_builtin: true },
          ]
        }
      };
    }
    return api.get('/skills/available', { params: { category } });
  }
};

// AI 资源文档 API
export const aiResourceApi = {
  list: (params?: any) => api.get('/ai-resources', { params }),
  get: (id: string) => api.get(`/ai-resources/${id}`),
  create: (data: any) => api.post('/ai-resources', data),
  update: (id: string, data: any) => api.put(`/ai-resources/${id}`, data),
  delete: (id: string) => api.delete(`/ai-resources/${id}`),
  clone: (id: string) => api.post(`/ai-resources/${id}/clone`),
};

// 单集剧本 API
export const scriptApi = {
  // 获取剧集摘要（Script Tab 专用聚合接口，支持分页）
  getEpisodesSummary: async (projectId: string, page: number = 1, pageSize: number = 20) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          episodes: [],
          running_task: null,
          progress: { total: 0, completed: 0, in_progress: 0, pending: 0, failed: 0 },
          pagination: { page: 1, page_size: pageSize, total_pages: 1 }
        }
      };
    }
    return api.get('/scripts/episodes/summary', { params: { project_id: projectId, page, page_size: pageSize } });
  },

  // 按项目获取所有剧本列表
  getProjectScripts: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: [] };
    }
    return api.get('/scripts', { params: { project_id: projectId } });
  },

  // 启动单集剧本生成
  startEpisodeScript: async (breakdownId: string, episodeNumber: number, options?: {
    modelConfigId?: string;
    novelType?: string;
  }) => {
    if (USE_MOCK) {
      await delay(500);
      return { data: { task_id: 'mock-script-task-1', status: 'queued' } };
    }
    return api.post('/scripts/episode/start', {
      breakdown_id: breakdownId,
      episode_number: episodeNumber,
      model_config_id: options?.modelConfigId,
      novel_type: options?.novelType
    });
  },

  // 获取剧本任务状态
  getTaskStatus: async (taskId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { task_id: taskId, status: 'completed', progress: 100 } };
    }
    return api.get(`/scripts/tasks/${taskId}`);
  },

  // 获取单集剧本结果
  getEpisodeScript: async (breakdownId: string, episodeNumber: number) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          episode_number: episodeNumber,
          title: `第 ${episodeNumber} 集`,
          word_count: 650,
          structure: {
            opening: { content: '【起】示例开场内容...', word_count: 120 },
            development: { content: '【承】示例发展内容...', word_count: 180 },
            climax: { content: '【转】示例高潮内容...', word_count: 230 },
            hook: { content: '【钩】示例悬念内容...\n【卡黑】', word_count: 120 }
          },
          full_script: '完整剧本内容...',
          scenes: ['场景1', '场景2'],
          characters: ['角色A', '角色B'],
          hook_type: '悬念类型'
        }
      };
    }
    return api.get(`/scripts/episode/${breakdownId}/${episodeNumber}`);
  },

  // 获取拆解下所有剧本列表
  getEpisodeScripts: async (breakdownId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { items: [], total: 0 } };
    }
    return api.get(`/scripts/episodes/${breakdownId}`);
  },

  // 更新剧本
  updateScript: async (scriptId: string, data: { title?: string; content?: any; full_script?: string }) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { message: '更新成功' } };
    }
    return api.put(`/scripts/${scriptId}`, data);
  },

  // 审核通过
  approveScript: async (scriptId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { message: '审核通过', status: 'approved' } };
    }
    return api.post(`/scripts/${scriptId}/approve`);
  },

  // 获取剧本历史版本列表
  getScriptHistory: async (projectId: string, episodeNumber: number) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: [] };
    }
    return api.get(`/scripts/episode/${projectId}/${episodeNumber}/history`);
  },

  // 获取指定剧本版本的完整数据
  getScriptDetail: async (scriptId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: null };
    }
    return api.get(`/scripts/${scriptId}/detail`);
  },

  // 停止剧本生成任务
  stopTask: async (taskId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { task_id: taskId, status: 'cancelled', message: '任务已停止' } };
    }
    return api.post(`/scripts/tasks/${taskId}/stop`);
  },

  // 获取项目的所有剧本任务（包括正在运行的）
  getProjectTasks: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: [] };
    }
    return api.get('/scripts/tasks', { params: { project_id: projectId } });
  },

  // 设置当前版本
  setCurrentScript: async (projectId: string, episodeNumber: number, scriptId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { message: '已设置为当前版本' } };
    }
    return api.post(`/scripts/${scriptId}/set-current`, {
      project_id: projectId,
      episode_number: episodeNumber
    });
  }
};

// 导出 API
export const exportApi = {
  // 导出单集
  exportSingle: async (scriptId: string, format: 'pdf' | 'docx' = 'pdf') => {
    return api.post('/export/single', { script_id: scriptId, format }, {
      responseType: 'blob',
      timeout: 60000  // 单集导出 60 秒超时
    });
  },

  // 批量导出（超时时间更长）
  exportBatch: async (projectId: string, format: 'pdf' | 'docx' = 'pdf', merged: boolean = false) => {
    return api.post('/export/batch', { project_id: projectId, format, merged }, {
      responseType: 'blob',
      timeout: 300000  // 批量导出 5 分钟超时
    });
  }
};

export const adminApi = {
  getStats: async () => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return {
        data: {
          total_users: 125,
          active_projects: 42,
          pending_tasks: 8,
          system_status: 'normal',
          credit_consumed_today: 1540
        }
      };
    }
    return api.get('/admin/stats');
  },

  getUsers: async (page = 1, pageSize = 20, keyword?: string) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return {
        data: {
          items: [
            { id: '1', email: 'admin@example.com', username: 'Admin', role: 'admin', tier: 'ENTERPRISE', credits: 99999, is_active: true, created_at: '2026-01-01' },
            { id: '2', email: 'user@example.com', username: 'User', role: 'user', tier: 'FREE', credits: 100, is_active: true, created_at: '2026-02-01' },
          ],
          total: 2
        }
      };
    }
    const skip = (page - 1) * pageSize;
    const response = await api.get('/admin/users', { params: { skip, limit: pageSize, keyword } });

    // Map backend response (users, total) to frontend expectation (items, total)
    return {
      data: {
        items: response.data.users,
        total: response.data.total
      }
    };
  },

  updateUser: async (userId: string, data: unknown) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return { data: { success: true } };
    }
    return api.put(`/admin/users/${userId}`, data);
  },

  // 获取正在运行的任务
  getRunningTasks: async () => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return {
        data: {
          tasks: [
            {
              id: 'task-001',
              task_type: 'breakdown',
              status: 'running',
              progress: 45,
              current_step: '正在执行剧情拆解...',
              user_id: 'user-001',
              username: '张三',
              project_id: 'proj-001',
              project_name: '测试项目',
              batch_id: 'batch-001',
              batch_number: 1,
              created_at: '2026-02-21T10:00:00Z',
              updated_at: '2026-02-21T10:05:00Z',
              running_time: 300,
              idle_time: 10
            }
          ]
        }
      };
    }
    return api.get('/admin/tasks/running');
  },

  // 停止任务
  stopTask: async (taskId: string) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return { data: { message: '任务已停止' } };
    }
    return api.post(`/admin/tasks/${taskId}/stop`);
  },

  // 查询卡住的任务（不自动终止）
  getStuckTasks: async () => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return {
        data: {
          tasks: [
            {
              id: 'stuck-task-1',
              task_type: 'breakdown',
              status: 'running',
              progress: 45,
              current_step: '正在处理第3章...',
              user_id: 'user-1',
              username: 'testuser',
              project_id: 'proj-1',
              project_name: '测试项目',
              batch_id: 'batch-1',
              batch_number: 1,
              created_at: new Date(Date.now() - 3700000).toISOString(),
              updated_at: new Date(Date.now() - 2000000).toISOString(),
              running_time: 3700,
              idle_time: 2000,
              reason: '停滞无响应（33 分钟）'
            }
          ],
          count: 1
        }
      };
    }
    return api.get('/admin/tasks/stuck');
  },

  // 拆分规则管理
  getSplitRules: async (activeOnly = false) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 300));
      return {
        data: [
          {
            id: '1',
            name: 'standard_chinese',
            display_name: '中文标准 - 第N章',
            pattern: '第[一二三四五六七八九十百千\\d]+章',
            pattern_type: 'regex',
            example: '第1章 初入江湖\n第二章 奇遇',
            is_default: true,
            is_active: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          },
          {
            id: '2',
            name: 'blank_line',
            display_name: '空行分隔',
            pattern: '',
            pattern_type: 'blank_line',
            example: '段落1\n\n段落2',
            is_default: false,
            is_active: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          }
        ]
      };
    }
    return api.get('/admin/split-rules', { params: { active_only: activeOnly } });
  },

  createSplitRule: async (data: {
    name: string;
    display_name: string;
    pattern: string;
    pattern_type: string;
    example?: string;
    is_default: boolean;
    is_active: boolean;
  }) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return {
        data: {
          id: '3',
          ...data,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      };
    }
    return api.post('/admin/split-rules', data);
  },

  updateSplitRule: async (id: string, data: {
    display_name?: string;
    pattern?: string;
    pattern_type?: string;
    example?: string;
    is_default?: boolean;
    is_active?: boolean;
  }) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return {
        data: {
          id,
          ...data,
          updated_at: new Date().toISOString()
        }
      };
    }
    return api.put(`/admin/split-rules/${id}`, data);
  },

  deleteSplitRule: async (id: string) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 500));
      return { data: { message: '删除成功' } };
    }
    return api.delete(`/admin/split-rules/${id}`);
  },

  initDefaultSplitRules: async () => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 800));
      return {
        data: {
          message: '初始化完成：创建 4 条，更新 0 条',
          created: 4,
          updated: 0
        }
      };
    }
    return api.post('/admin/split-rules/init-defaults');
  }
};

// 积分与账单 API
export const billingApi = {
  // 获取积分余额
  getBalance: async () => {
    if (USE_MOCK) {
      await delay(200);
      return { data: { credits: 2450 } };
    }
    return api.get('/billing/balance');
  },

  // 获取积分详情（含定价）
  getCreditsInfo: async () => {
    if (USE_MOCK) {
      await delay(200);
      return {
        data: {
          credits: 2450,
          monthly_granted: 3000,
          monthly_credits: 3000,
          next_grant_at: '2026-03-01T00:00:00Z',
          tier: 'creator',
          tier_display: '创作者版',
          pricing: {
            base: { breakdown: 100, script: 50, qa: 30, retry: 50 },
            token: { enabled: false, input_per_1k: 1, output_per_1k: 2 }
          }
        }
      };
    }
    return api.get('/billing/credits');
  },

  // 获取账单记录
  getRecords: async (limit = 20, offset = 0) => {
    if (USE_MOCK) {
      await delay(200);
      return {
        data: {
          records: [
            { id: '1', type: 'consume', credits: -100, balance_after: 2450, description: '剧情拆解（基础费）', created_at: '2026-02-12T10:30:00Z' },
            { id: '2', type: 'consume', credits: -50, balance_after: 2550, description: '剧本生成（基础费）', created_at: '2026-02-12T09:15:00Z' },
            { id: '3', type: 'grant', credits: 3000, balance_after: 2600, description: '月度积分赠送 (创作者版)', created_at: '2026-02-01T00:00:00Z' },
          ],
          limit,
          offset
        }
      };
    }
    return api.get('/billing/records', { params: { limit, offset } });
  },

  // 充值积分
  recharge: async (amount: number, paymentMethod: string) => {
    if (USE_MOCK) {
      await delay(500);
      return {
        data: {
          success: true,
          credits: 2450 + amount * 100,
          credits_added: amount * 100,
          message: '充值成功'
        }
      };
    }
    return api.post('/billing/recharge', { amount, payment_method: paymentMethod });
  }
};

// 后台数据分析 API
export const adminAnalyticsApi = {
  // 获取拆解概览统计
  getBreakdownOverview: async (period: string = 'week') => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          period,
          total: 156,
          passed: 128,
          failed: 18,
          pending: 10,
          pass_rate: 87.7,
          avg_score: 82.3,
          avg_retry: 0.45
        }
      };
    }
    return api.get('/admin/analytics/breakdown/overview', { params: { period } });
  },

  // 按模型统计
  getBreakdownByModel: async (period: string = 'week') => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          period,
          models: [
            { provider: 'openai', model_name: 'gpt-4-turbo', display_name: 'openai/gpt-4-turbo', total: 80, passed: 72, failed: 8, pass_rate: 90.0, avg_score: 85.2 },
            { provider: 'anthropic', model_name: 'claude-3-sonnet', display_name: 'anthropic/claude-3-sonnet', total: 50, passed: 42, failed: 8, pass_rate: 84.0, avg_score: 80.5 },
            { provider: 'openai', model_name: 'gpt-4o', display_name: 'openai/gpt-4o', total: 26, passed: 14, failed: 2, pass_rate: 87.5, avg_score: 81.0 }
          ]
        }
      };
    }
    return api.get('/admin/analytics/breakdown/by-model', { params: { period } });
  },

  // 按资源统计
  getBreakdownByResource: async (period: string = 'week') => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          period,
          resources: [
            { resource_id: 'r1', name: 'adapt_method_default', display_name: '默认改编方法论', total: 100, passed: 88, failed: 12, pass_rate: 88.0, avg_score: 83.5 },
            { resource_id: 'r2', name: 'adapt_method_drama', display_name: '剧情向方法论', total: 56, passed: 40, failed: 6, pass_rate: 87.0, avg_score: 81.2 }
          ]
        }
      };
    }
    return api.get('/admin/analytics/breakdown/by-resource', { params: { period } });
  },

  // 分数分布
  getScoreDistribution: async (period: string = 'week') => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          period,
          distribution: [
            { range: '90-100', label: '优秀', count: 35, color: '#22c55e' },
            { range: '80-89', label: '良好', count: 58, color: '#84cc16' },
            { range: '70-79', label: '中等', count: 32, color: '#eab308' },
            { range: '60-69', label: '及格', count: 18, color: '#f97316' },
            { range: '0-59', label: '不及格', count: 8, color: '#ef4444' },
            { range: '无分数', label: '未评分', count: 5, color: '#6b7280' }
          ]
        }
      };
    }
    return api.get('/admin/analytics/breakdown/score-distribution', { params: { period } });
  },

  // 时间趋势
  getBreakdownTrend: async (period: string = 'week') => {
    if (USE_MOCK) {
      await delay(300);
      const now = new Date();
      const trend = [];
      for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        trend.push({
          date: date.toISOString(),
          total: Math.floor(Math.random() * 30) + 10,
          passed: Math.floor(Math.random() * 25) + 8,
          failed: Math.floor(Math.random() * 5) + 1,
          pass_rate: Math.floor(Math.random() * 20) + 75,
          avg_score: Math.floor(Math.random() * 15) + 75
        });
      }
      return { data: { period, trend } };
    }
    return api.get('/admin/analytics/breakdown/trend', { params: { period } });
  },

  // 重试统计
  getRetryStats: async (period: string = 'week') => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          period,
          stats: [
            { retry_count: '0次', count: 120, color: '#22c55e' },
            { retry_count: '1次', count: 25, color: '#84cc16' },
            { retry_count: '2次', count: 8, color: '#eab308' },
            { retry_count: '3次+', count: 3, color: '#ef4444' }
          ],
          avg_retry: 0.45
        }
      };
    }
    return api.get('/admin/analytics/breakdown/retry-stats', { params: { period } });
  }
};

// ==================== 兑换码 API ====================
export const redeemApi = {
  // 用户使用兑换码
  useCode: async (code: string) => {
    return api.post('/redeem/use', { code });
  },

  // 管理端 API
  admin: {
    // 获取兑换码列表
    list: async (params?: {
      page?: number;
      page_size?: number;
      type?: string;
      is_active?: boolean;
    }) => {
      return api.get('/admin/redeem', { params });
    },

    // 创建兑换码
    create: async (data: {
      type: 'credits' | 'tier_upgrade';
      credits?: number;
      tier?: string;
      tier_days?: number;
      max_uses?: number;
      expires_at?: string;
      note?: string;
      code?: string;
      count?: number;
    }) => {
      return api.post('/admin/redeem', data);
    },

    // 获取兑换码详情
    get: async (id: string) => {
      return api.get(`/admin/redeem/${id}`);
    },

    // 更新兑换码
    update: async (id: string, data: {
      is_active?: boolean;
      max_uses?: number;
      expires_at?: string;
      note?: string;
    }) => {
      return api.put(`/admin/redeem/${id}`, data);
    },

    // 删除兑换码
    delete: async (id: string) => {
      return api.delete(`/admin/redeem/${id}`);
    },

    // 管理员为用户充值
    rechargeUser: async (userId: string, credits: number, reason?: string) => {
      return api.post(`/admin/users/${userId}/recharge`, {
        credits,
        reason: reason || '管理员手动充值'
      });
    },
  },
};

// ==================== 通知公告 API ====================
export const announcementApi = {
  // 管理端 API
  admin: {
    // 获取通知列表
    getAnnouncements: async (params?: {
      page?: number;
      page_size?: number;
      priority?: string;
      type?: string;
      is_published?: boolean;
      search?: string;
    }) => {
      return api.get('/admin/announcements', { params });
    },

    // 创建通知
    createAnnouncement: async (data: {
      title: string;
      content: string;
      priority?: string;
      type?: string;
      expires_at?: string;
    }) => {
      return api.post('/admin/announcements', data);
    },

    // 获取通知详情
    getAnnouncement: async (id: string) => {
      return api.get(`/admin/announcements/${id}`);
    },

    // 更新通知
    updateAnnouncement: async (id: string, data: {
      title?: string;
      content?: string;
      priority?: string;
      type?: string;
      expires_at?: string;
    }) => {
      return api.put(`/admin/announcements/${id}`, data);
    },

    // 删除通知
    deleteAnnouncement: async (id: string) => {
      return api.delete(`/admin/announcements/${id}`);
    },

    // 发布通知
    publishAnnouncement: async (id: string) => {
      return api.post(`/admin/announcements/${id}/publish`);
    },

    // 取消发布
    unpublishAnnouncement: async (id: string) => {
      return api.post(`/admin/announcements/${id}/unpublish`);
    },

    // 获取统计信息
    getAnnouncementStats: async (id: string) => {
      return api.get(`/admin/announcements/${id}/stats`);
    },
  },

  // 用户端 API
  user: {
    // 获取通知列表
    getAnnouncements: async (params?: {
      page?: number;
      page_size?: number;
    }) => {
      return api.get('/announcements', { params });
    },

    // 获取通知详情
    getAnnouncement: async (id: string) => {
      return api.get(`/announcements/${id}`);
    },

    // 标记为已读
    markAsRead: async (id: string) => {
      return api.post(`/announcements/${id}/read`);
    },

    // 获取未读数量
    getUnreadCount: async () => {
      return api.get('/announcements/unread-count');
    },
  },
};

// ==================== 用户反馈 API ====================
export const feedbackApi = {
  // 用户提交反馈
  create: async (data: {
    type: string;
    content: string;
    contact?: string;
  }) => {
    return api.post('/feedback', data);
  },

  // 管理端 API
  admin: {
    // 获取反馈列表
    list: async (params?: {
      page?: number;
      page_size?: number;
      type?: string;
      status?: string;
    }) => {
      return api.get('/admin/feedbacks', { params });
    },

    // 获取反馈详情
    get: async (id: string) => {
      return api.get(`/admin/feedbacks/${id}`);
    },

    // 更新反馈状态/备注
    update: async (id: string, data: {
      status?: string;
      admin_note?: string;
    }) => {
      return api.patch(`/admin/feedbacks/${id}`, data);
    },
  },
};

// ==================== 用户认证 API ====================
export const authApi = {
  // 更新用户资料
  updateProfile: async (data: {
    username?: string;
    full_name?: string;
    avatar_url?: string;
  }) => {
    return api.put('/auth/profile', data);
  },

  // 修改密码
  changePassword: async (data: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }) => {
    return api.put('/auth/password', data);
  },

  // 获取当前用户信息
  getCurrentUser: async () => {
    return api.get('/auth/me');
  },
};

export { USE_MOCK };
export default api;
