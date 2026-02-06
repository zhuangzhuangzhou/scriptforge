# 章节列表体验优化与功能补全

## 目标
优化章节列表的交互细节、性能与布局，实现无限滚动和搜索功能，并修复统计显示错误。

## 需求详情

### 1. UI 布局与样式
- **列表项**:
  - 删除图标 (`Trash2`) 移至章节编号 (`Chapter X`) 后方。
  - 状态图标 (`StatusTag`) 距右侧 `margin-right: 20px`。
  - 行高增加 5px (`py-2` -> `py-3` 或自定义 padding)。
- **头部**:
  - 左侧标题 "章节目录" -> 显示实际的小说名称 (`project.name`)。
  - 移除右侧正文区域顶部的 "小说标题栏"（已在左侧显示）。
  - 统计数字: 修正为从 `/chapters` 接口返回的 `total` (需后端支持)。

### 2. 交互优化
- **无限滚动**:
  - 移除 "加载更多" 按钮。
  - 监听列表容器滚动事件，触底自动加载下一页。
  - `page_size` 调整为 20。
- **删除体验**:
  - 删除章节后，**不刷新整个列表**（不重置 `page` 为 1）。
  - 仅在本地状态中移除该项 (`setChapters(prev => prev.filter(c => c.id !== id))`)。
- **搜索功能**:
  - 实现头部搜索框逻辑。
  - 输入防抖 (Debounce) -> 调用 API (需新增 `keyword` 参数) -> 替换列表内容。

### 3. 功能补全
- **导入/下载**: 用户反馈之前未实现，需检查代码并确保逻辑正确绑定。
  - 导入: 绑定 `Modal` 确认逻辑。
  - 下载: 绑定 `Blob` 下载逻辑。

## 技术方案

### Backend (`backend/app/api/v1/projects.py`)
1.  **GET /chapters 更新**:
    - 增加 `keyword` 参数 (支持搜索)。
    - 返回结构调整: 返回 `{ items: [], total: 100 }` 而非纯列表，以便前端获取总数。
    - 或者保留列表返回，利用 Response Header 或独立字段返回 Total (建议改为包裹格式)。

### Frontend (`Workspace.tsx`)
1.  **API 适配**: 处理新的 `{ items, total }` 返回结构。
2.  **Scroll Listener**:
    - `onScroll` 检测 `scrollTop + clientHeight >= scrollHeight - 50`。
    - 防抖触发 `fetchChapters` (page + 1)。
3.  **Search Logic**:
    - `searchTerm` state。
    - `useEffect` dependency on `searchTerm` -> reset list & fetch.
4.  **Optimistic UI**: 删除时直接操作 State。

## 验收标准
- [ ] 列表项布局符合新要求（删除按钮位置、间距、行高）。
- [ ] 滚动到底部自动加载，无卡顿。
- [ ] 删除章节后页面不闪烁，当前阅读位置保留（或平滑切换）。
- [ ] 搜索框可用，能搜到特定章节。
- [ ] 章节总数显示准确。
- [ ] 导入和下载功能真实可用。
