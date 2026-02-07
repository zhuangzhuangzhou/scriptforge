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

export interface PlotBreakdown {
  batch_id: string;
  conflicts: Conflict[];
  plot_hooks: PlotHook[];
  characters: Character[];
  scenes: Scene[];
  emotions: EmotionPoint[];
  consistency_status?: string;
  consistency_score?: number;
  consistency_results?: Record<string, unknown>;
  qa_status?: string;
  qa_report?: any;
  used_adapt_method_id?: string;
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
