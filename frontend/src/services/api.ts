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

  getBatches: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: [] };
    }
    const response = await api.get(`/projects/${projectId}/batches`);
    return { data: response.data };
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

export { USE_MOCK };
export default api;
