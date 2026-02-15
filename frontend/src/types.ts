export type UserTier = 'FREE' | 'CREATOR' | 'STUDIO' | 'ENTERPRISE';

export interface UserState {
  tier: UserTier;
  credits: number;  // 积分余额
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
  breakdown_status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
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
  dimensions: Record<string, QADimension> | QADimension[];
  issues: string[] | { description?: string; issue?: string; target?: string }[];
  suggestions: string[] | { action?: string; suggestion?: string }[];
  fix_instructions?: string | { action?: string; suggestion?: string; target?: string }[];
  // 自动修正相关
  auto_fix_attempts?: number;
  auto_fix_success?: boolean;
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
  error_message?: string;       // 原始错误信息
  error_display?: {            // 人性化错误信息
    title: string;
    description: string;
    suggestion: string;
    icon: string;
    severity: 'error' | 'warning';
    failed_at?: string;
    retry_count?: number;
    code?: string;
    original_message?: string;
    technical_details?: string;
  };
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

// 剧本四段式结构
export interface ScriptStructure {
  opening: { content: string; word_count: number };      // 【起】开场冲突
  development: { content: string; word_count: number };  // 【承】推进发展
  climax: { content: string; word_count: number };       // 【转】反转高潮
  hook: { content: string; word_count: number };         // 【钩】悬念结尾
}

// 单集剧本
export interface EpisodeScript {
  id?: string;
  episode_number: number;
  title: string;
  word_count: number;
  structure: ScriptStructure;
  full_script: string;
  scenes: string[];
  characters: string[];
  hook_type: string;
  status?: 'pending' | 'generating' | 'completed' | 'failed' | 'approved';
  qa_status?: 'pending' | 'PASS' | 'FAIL';
  qa_score?: number;
  qa_report?: ScriptQAReport;
  created_at?: string;
}

// 剧本质检报告
export interface ScriptQAReport {
  status: 'PASS' | 'FAIL';
  score: number;
  dimensions: {
    word_count: { score: number; issues: string[]; actual?: number };
    structure: { score: number; issues: string[] };
    opening: { score: number; issues: string[] };
    hook_ending: { score: number; issues: string[] };
    visualization: { score: number; issues: string[] };
    dialogue: { score: number; issues: string[] };
  };
  fix_instructions: Array<{
    target: string;
    type: string;
    issue: string;
    suggestion: string;
  }>;
  summary: string;
}
