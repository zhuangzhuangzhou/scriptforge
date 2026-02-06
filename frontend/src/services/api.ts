import axios from 'axios';
import { mockProjects, mockLogs, mockUser } from './mockData';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
// 增强判断：打印日志并支持字符串或布尔值
const rawMockEnv = import.meta.env.VITE_USE_MOCK;
const USE_MOCK = rawMockEnv === 'true' || rawMockEnv === true;

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
        ...data,
        type: data.novel_type || '未知',
        updated_at: '刚刚',
        status: 'draft',
        progress: 0,
        total_chapters: data.batch_size || 10,
        processed_chapters: 0
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
  }) => {
    if (USE_MOCK) {
      await delay(500);
      return { data: { task_id: 'mock-task-1', status: 'queued' } };
    }
    return api.post('/breakdown/start', {
      batch_id: batchId,
      model_config_id: options?.modelConfigId,
      selected_skills: options?.selectedSkills,
      pipeline_id: options?.pipelineId
    });
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
    return api.post('/breakdown/start-continue', null, { params: { project_id: projectId } });
  },

  // 获取任务状态
  getTaskStatus: async (taskId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: { task_id: taskId, status: 'completed', progress: 100 } };
    }
    return api.get(`/breakdown/tasks/${taskId}`);
  },

  // 获取拆解结果
  getBreakdownResults: async (batchId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return {
        data: {
          batch_id: batchId,
          conflicts: [
            { title: '档案缺失', tension: 75 },
            { title: '上级施压', tension: 60 }
          ],
          plot_hooks: [{ hook: '发现神秘纸条' }],
          characters: [],
          scenes: [],
          emotions: [],
          consistency_score: 85
        }
      };
    }
    return api.get(`/breakdown/results/${batchId}`);
  }
};

export { USE_MOCK };
export default api;
