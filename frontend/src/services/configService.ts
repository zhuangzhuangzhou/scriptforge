import api from './api';

export interface AIConfiguration {
  id: string;
  key: string;
  value: any;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface AIConfigurationCreate {
  key: string;
  value: any;
  description?: string;
}

export const configService = {
  /**
   * 获取所有配置列表
   */
  getConfigurations: async (): Promise<AIConfiguration[]> => {
    const response = await api.get('/configurations');
    return response.data;
  },

  /**
   * 获取特定 Key 的配置
   */
  getConfiguration: async (key: string): Promise<AIConfiguration> => {
    const response = await api.get(`/configurations/${key}`);
    return response.data;
  },

  /**
   * 创建或更新配置 (Upsert)
   */
  upsertConfiguration: async (data: AIConfigurationCreate): Promise<AIConfiguration> => {
    const response = await api.post('/configurations', data);
    return response.data;
  },

  /**
   * 删除配置
   */
  deleteConfiguration: async (key: string): Promise<void> => {
    await api.delete(`/configurations/${key}`);
  }
};
