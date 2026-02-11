export type UserTier = 'FREE' | 'CREATOR' | 'STUDIO' | 'ENTERPRISE';

export interface UserState {
  tier: UserTier;
  balance: number;
  avatar: string;
  name: string;
}

// 批次相关类型
export interface Batch {
  id: string;
  project_id: string;
  batch_number: number;
  start_chapter: number;
  end_chapter: number;
  total_chapters: number;
  total_words: number;
  breakdown_status: 'pending' | 'processing' | 'completed' | 'failed';
  script_status: string;
}

// 剧情拆解相关类型
export interface Conflict {
  id?: string;
  title: string;
  description?: string;
  tension: number;
}

export interface PlotHook {
  id?: string;
  hook: string;
  episode?: number;
}

export interface Character {
  id?: string;
  name: string;
  role?: string;
  description?: string;
}

export interface Scene {
  id?: string;
  title: string;
  location?: string;
  description?: string;
}

export interface EmotionPoint {
  position: number;
  emotion: string;
  intensity: number;
}

export interface Episode {
  episode_number: number;
  title: string;
  main_conflict: string;
  key_scenes: string[];
  chapter_range: [number, number];
  conflicts: Conflict[];
  plot_hooks: PlotHook[];
  characters: Character[];
  scenes: Scene[];
  emotions: EmotionPoint[];
}

// 新增：统一剧情点格式（v2）
export interface PlotPoint {
  id: number;
  scene: string;
  characters: string[];
  event: string;
  hook_type: string;
  episode: number;
  status: 'unused' | 'used';
  source_chapter: number;
}

// 质检报告维度
export interface QADimension {
  pass: boolean;
  score: number;
  issues: string[];
}

// 质检报告
export interface QAReport {
  status: 'PASS' | 'FAIL';
  score: number;
  dimensions: Record<string, QADimension>;
  issues: string[];
  suggestions: string[];
  fix_instructions?: string;
}

export interface PlotBreakdown {
  batch_id: string;
  format_version: 1 | 2;  // 1=旧6字段格式, 2=新统一格式

  // v2 新格式
  plot_points?: PlotPoint[];
  qa_status?: 'pending' | 'PASS' | 'FAIL';
  qa_score?: number;
  qa_report?: QAReport;
  qa_retry_count?: number;

  // v1 旧格式（保留兼容）
  conflicts?: Conflict[];
  plot_hooks?: PlotHook[];
  characters?: Character[];
  scenes?: Scene[];
  emotions?: EmotionPoint[];
  episodes?: Episode[];

  // 通用字段
  consistency_status?: string;
  consistency_score?: number;
  consistency_results?: Record<string, unknown>;
  used_adapt_method_id?: string;
  created_at?: string;
  updated_at?: string;
}

// 新增：AI 资源文档类型
export interface AIResource {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  category: 'adapt_method' | 'output_style' | 'template' | 'example';
  content: string;
  is_builtin: boolean;
  owner_id?: string;
  visibility: 'public' | 'private';
  is_active: boolean;
  version: number;
  parent_id?: string;
  created_at: string;
  updated_at: string;
}

// 新增：AI 资源列表响应
export interface AIResourceListResponse {
  items: AIResource[];
  total: number;
  page: number;
  page_size: number;
}

// AI 任务状态
export interface AITaskStatus {
  task_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  current_step?: string;
  error_message?: string;
  retry_count?: number;
}

// 技能类型
export interface Skill {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  category: 'breakdown' | 'script' | 'analysis';
  is_active: boolean;
  is_builtin: boolean;
  is_template_based: boolean;
  owner_id?: string;
}
