import axios from 'axios';
import { mockProjects, mockLogs, mockUser } from './mockData';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

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
    return api.get(`/projects/${id}`);
  },
  
  createProject: async (data: { name: string; novel_type?: string; description?: string; batch_size?: number }) => {
    if (USE_MOCK) {
      await delay(500);
      const newProject = {
        id: String(mockProjects.length + 1),
        ...data,
        type: data.novel_type || '未知',
        updatedAt: '刚刚',
        status: '配置中',
        progress: 0,
        totalChapters: data.batch_size || 10,
        processedChapters: 0
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

  getBatches: async (projectId: string) => {
    if (USE_MOCK) {
      await delay(300);
      return { data: [] }; // 暂时返回空，或后续完善 mockData
    }
    return api.get(`/projects/${projectId}/batches`);
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
