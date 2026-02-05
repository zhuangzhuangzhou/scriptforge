import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor for Auth
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

/**
 * 项目管理相关 API
 */
export const projectApi = {
  // 获取项目列表
  getProjects: () => api.get('/projects'),
  
  // 获取单个项目详情
  getProject: (id: string) => api.get(`/projects/${id}`),
  
  // 创建项目
  createProject: (data: { name: string; novel_type?: string; description?: string; batch_size?: number }) => 
    api.post('/projects', data),
  
  // 更新项目
  updateProject: (id: string, data: any) => api.put(`/projects/${id}`, data),
  
  // 删除项目
  deleteProject: (id: string) => api.delete(`/projects/${id}`),
  
  // 上传小说源文件
  uploadFile: (id: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/projects/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};

export { USE_MOCK };
export default api;
