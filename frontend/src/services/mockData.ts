export const mockProjects = [
  { id: '1', name: "沉默的真相·改编", type: "悬疑/惊悚", updatedAt: "2小时前", status: "进行中", progress: 65, totalChapters: 24, processedChapters: 15 },
  { id: '2', name: "星际穿越·前传", type: "科幻", updatedAt: "1天前", status: "已完成", progress: 100, totalChapters: 10, processedChapters: 10 },
  { id: '3', name: "大明王朝1566", type: "古装/历史", updatedAt: "3天前", status: "配置中", progress: 0, totalChapters: 50, processedChapters: 0 },
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
  balance: 2450,
  tier: 'FREE'
};
