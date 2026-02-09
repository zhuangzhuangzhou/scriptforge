/**
 * 模型管理 API 服务
 *
 * 提供模型提供商、模型、凭证、计费规则和系统配置的管理接口
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加 token
api.interceptors.request.use(async (config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：处理错误
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

// ==================== 类型定义 ====================

export interface Provider {
  id: string;
  provider_key: string;
  display_name: string;
  provider_type: string;
  api_endpoint?: string;
  icon_url?: string;
  description?: string;
  is_enabled: boolean;
  is_system_default: boolean;
  models_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProviderCreate {
  provider_key: string;
  display_name: string;
  provider_type: string;
  api_endpoint?: string;
  icon_url?: string;
  description?: string;
}

export interface ProviderUpdate {
  display_name?: string;
  api_endpoint?: string;
  is_enabled?: boolean;
  icon_url?: string;
  description?: string;
}

// ==================== 提供商管理 API ====================

export const providerApi = {
  /**
   * 获取提供商列表
   */
  getProviders: async () => {
    return api.get<Provider[]>('/admin/models/providers');
  },

  /**
   * 获取提供商详情
   */
  getProvider: async (id: string) => {
    return api.get<Provider>(`/admin/models/providers/${id}`);
  },

  /**
   * 创建提供商
   */
  createProvider: async (data: ProviderCreate) => {
    return api.post<Provider>('/admin/models/providers', data);
  },

  /**
   * 更新提供商
   */
  updateProvider: async (id: string, data: ProviderUpdate) => {
    return api.put<Provider>(`/admin/models/providers/${id}`, data);
  },

  /**
   * 删除提供商
   */
  deleteProvider: async (id: string) => {
    return api.delete(`/admin/models/providers/${id}`);
  },

  /**
   * 启用/禁用提供商
   */
  toggleProvider: async (id: string) => {
    return api.post<Provider>(`/admin/models/providers/${id}/toggle`);
  },
};

// ==================== 模型管理类型定义 ====================

export interface AIModel {
  id: string;
  provider_id: string;
  provider_name: string;
  model_key: string;
  display_name: string;
  model_type?: string;
  max_tokens?: number;
  max_input_tokens?: number;
  max_output_tokens?: number;
  timeout_seconds: number;
  temperature_default: number;
  supports_streaming: boolean;
  supports_function_calling: boolean;
  description?: string;
  is_enabled: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIModelCreate {
  provider_id: string;
  model_key: string;
  display_name: string;
  model_type?: string;
  max_tokens?: number;
  max_input_tokens?: number;
  max_output_tokens?: number;
  timeout_seconds?: number;
  temperature_default?: number;
  supports_streaming?: boolean;
  supports_function_calling?: boolean;
  description?: string;
}

export interface AIModelUpdate {
  display_name?: string;
  model_type?: string;
  is_enabled?: boolean;
  max_tokens?: number;
  max_input_tokens?: number;
  max_output_tokens?: number;
  timeout_seconds?: number;
  temperature_default?: number;
  supports_streaming?: boolean;
  supports_function_calling?: boolean;
  description?: string;
}

// ==================== 模型管理 API ====================

export const modelApi = {
  /**
   * 获取模型列表
   */
  getModels: async (providerId?: string) => {
    const params = providerId ? { provider_id: providerId } : {};
    return api.get<AIModel[]>('/admin/models/models', { params });
  },

  /**
   * 获取模型详情
   */
  getModel: async (id: string) => {
    return api.get<AIModel>(`/admin/models/models/${id}`);
  },

  /**
   * 创建模型
   */
  createModel: async (data: AIModelCreate) => {
    return api.post<AIModel>('/admin/models/models', data);
  },

  /**
   * 更新模型
   */
  updateModel: async (id: string, data: AIModelUpdate) => {
    return api.put<AIModel>(`/admin/models/models/${id}`, data);
  },

  /**
   * 删除模型
   */
  deleteModel: async (id: string) => {
    return api.delete(`/admin/models/models/${id}`);
  },

  /**
   * 启用/禁用模型
   */
  toggleModel: async (id: string) => {
    return api.post<AIModel>(`/admin/models/models/${id}/toggle`);
  },

  /**
   * 设置为默认模型
   */
  setDefaultModel: async (id: string) => {
    return api.post<AIModel>(`/admin/models/models/${id}/set-default`);
  },
};

// ==================== 凭证管理类型定义 ====================

export interface ProviderInfo {
  id: string;
  provider_key: string;
  display_name: string;
}

export interface Credential {
  id: string;
  provider: ProviderInfo;
  credential_name: string;
  api_key_masked: string;
  is_active: boolean;
  is_system_default: boolean;
  quota_limit?: number;
  quota_used: number;
  quota_remaining?: number;
  expires_at?: string;
  last_used_at?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface CredentialCreate {
  provider_id: string;
  credential_name: string;
  api_key: string;
  api_secret?: string;
  quota_limit?: number;
  expires_at?: string;
}

export interface CredentialUpdate {
  credential_name?: string;
  api_key?: string;
  api_secret?: string;
  is_active?: boolean;
  quota_limit?: number;
  expires_at?: string;
}

// ==================== 凭证管理 API ====================

export const credentialApi = {
  /**
   * 获取凭证列表
   */
  getCredentials: async (providerId?: string) => {
    const params = providerId ? { provider_id: providerId } : {};
    return api.get<Credential[]>('/admin/models/credentials', { params });
  },

  /**
   * 获取凭证详情
   */
  getCredential: async (id: string) => {
    return api.get<Credential>(`/admin/models/credentials/${id}`);
  },

  /**
   * 创建凭证
   */
  createCredential: async (data: CredentialCreate) => {
    return api.post<Credential>('/admin/models/credentials', data);
  },

  /**
   * 更新凭证
   */
  updateCredential: async (id: string, data: CredentialUpdate) => {
    return api.put<Credential>(`/admin/models/credentials/${id}`, data);
  },

  /**
   * 删除凭证
   */
  deleteCredential: async (id: string) => {
    return api.delete(`/admin/models/credentials/${id}`);
  },

  /**
   * 启用/禁用凭证
   */
  toggleCredential: async (id: string) => {
    return api.post<Credential>(`/admin/models/credentials/${id}/toggle`);
  },

  /**
   * 测试凭证有效性
   */
  testCredential: async (id: string) => {
    return api.post<{ success: boolean; message: string }>(`/admin/models/credentials/${id}/test`);
  },
};

// ==================== 计费规则类型定义 ====================

export interface ModelInfo {
  id: string;
  model_key: string;
  display_name: string;
}

export interface Pricing {
  id: string;
  model: ModelInfo;
  input_credits_per_1k_tokens: number;
  output_credits_per_1k_tokens: number;
  min_credits_per_request: number;
  effective_from?: string;
  effective_until?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PricingCreate {
  model_id: string;
  input_credits_per_1k_tokens: number;
  output_credits_per_1k_tokens: number;
  min_credits_per_request?: number;
  effective_from?: string;
  effective_until?: string;
}

export interface PricingUpdate {
  input_credits_per_1k_tokens?: number;
  output_credits_per_1k_tokens?: number;
  min_credits_per_request?: number;
  effective_from?: string;
  effective_until?: string;
  is_active?: boolean;
}

// ==================== 计费规则管理 API ====================

export const pricingApi = {
  /**
   * 获取计费规则列表
   */
  getPricingRules: async (modelId?: string) => {
    const params = modelId ? { model_id: modelId } : {};
    return api.get<Pricing[]>('/admin/models/pricing', { params });
  },

  /**
   * 获取计费规则详情
   */
  getPricingRule: async (id: string) => {
    return api.get<Pricing>(`/admin/models/pricing/${id}`);
  },

  /**
   * 创建计费规则
   */
  createPricingRule: async (data: PricingCreate) => {
    return api.post<Pricing>('/admin/models/pricing', data);
  },

  /**
   * 更新计费规则
   */
  updatePricingRule: async (id: string, data: PricingUpdate) => {
    return api.put<Pricing>(`/admin/models/pricing/${id}`, data);
  },

  /**
   * 删除计费规则
   */
  deletePricingRule: async (id: string) => {
    return api.delete(`/admin/models/pricing/${id}`);
  },

  /**
   * 获取模型当前生效的计费规则
   */
  getModelCurrentPricing: async (modelId: string) => {
    return api.get<Pricing>(`/admin/models/pricing/model/${modelId}`);
  },
};

// ==================== 系统配置类型定义 ====================

export interface SystemConfig {
  id: string;
  config_key: string;
  config_value: Record<string, any>;
  value_type: string;
  description?: string;
  is_editable: boolean;
  created_at: string;
  updated_at: string;
}

export interface SystemConfigUpdate {
  config_value: Record<string, any>;
}

// ==================== 系统配置管理 API ====================

export const systemConfigApi = {
  /**
   * 获取所有系统配置
   */
  getSystemConfigs: async () => {
    return api.get<SystemConfig[]>('/admin/models/system-config');
  },

  /**
   * 获取单个系统配置
   */
  getSystemConfig: async (key: string) => {
    return api.get<SystemConfig>(`/admin/models/system-config/${key}`);
  },

  /**
   * 更新系统配置
   */
  updateSystemConfig: async (key: string, data: SystemConfigUpdate) => {
    return api.put<SystemConfig>(`/admin/models/system-config/${key}`, data);
  },
};
