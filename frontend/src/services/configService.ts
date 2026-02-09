import api from './api';

export interface AIConfiguration {
  id: string;
  key: string;
  value: any;
  description?: string;
  user_id?: string | null;
  category?: string;
  is_active?: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIConfigurationCreate {
  key: string;
  value: any;
  description?: string;
  category?: string;
  is_active?: boolean;
}

export const configService = {
  /**
   * 获取所有配置列表
   * @param merge - true: 返回合并后的生效配置(用户覆盖系统); false: 返回所有原始配置(用于管理)
   * @param category - 可选过滤分类
   */
  getConfigurations: async (merge: boolean = true, category?: string): Promise<AIConfiguration[]> => {
    const response = await api.get('/configurations', {
      params: { merge, category }
    });
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
