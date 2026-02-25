export const mockProjects = [
  { id: '1', name: "沉默的真相·改编", novel_type: "悬疑/惊悚", updated_at: "2小时前", status: "processing", progress: 65, total_chapters: 24, processed_chapters: 15, batch_size: 6, description: "改编自长夜难明" },
  { id: '2', name: "星际穿越·前传", novel_type: "科幻", updated_at: "1天前", status: "completed", progress: 100, total_chapters: 10, processed_chapters: 10, batch_size: 6, description: "星际穿越前传故事" },
  { id: '3', name: "大明王朝1566", novel_type: "古装/历史", updated_at: "3天前", status: "draft", progress: 0, total_chapters: 50, processed_chapters: 0, batch_size: 6, description: "嘉靖末年，国库空虚..." },
];

export const mockLogs = [
  { id: '1', timestamp: '10:00:01', type: 'info', message: 'Initializing breakdown agent...' },
  { id: '2', timestamp: '10:00:02', type: 'thinking', message: 'Reading context: Chapter 1-5...' },
  { id: '3', timestamp: '10:00:05', type: 'thinking', message: 'Identifying conflict nodes in scene 3...' },
  { id: '4', timestamp: '10:00:08', type: 'success', message: 'Extracted 3 core conflicts.' },
  { id: '5', timestamp: '10:00:09', type: 'info', message: 'Formatting output...' }
];

export const mockUser = {
  username: 'Alex Writer',
  credits: 2450,
  tier: 'FREE'
};
