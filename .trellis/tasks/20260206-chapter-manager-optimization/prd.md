# 章节管理功能优化与增强

## 目标
优化小说章节列表的加载性能，增强章节管理功能（删除、插入上传），并完善正文操作（下载）。

## 需求详情

### 1. 章节列表优化
- **分页加载**:
  - 后端接口支持分页 (`page`, `page_size`)。
  - 前端侧边栏实现“加载更多”或滚动到底部自动加载 (Infinite Scroll)。
  - **样式**: 行高降低 10px (CSS `py` padding reduction)。

### 2. 章节管理
- **删除章节**:
  - 选中章节时，右侧出现删除图标。
  - 点击删除 -> `DELETE /projects/{id}/chapters/{chapter_id}`。
  - 删除后刷新列表，选中下一章。
- **插入上传**:
  - 修改底部的“导入章节”按钮。
  - 点击弹出 `Modal`：
    - **标题**: 上传章节
    - **内容**: “上传章节将自动追加到当前选择的章节【{selected_chapter_title}】后”
    - **输入**: 文件选择框 (accept `.txt`, max 1MB)。
  - **逻辑**: 调用后端 `POST /projects/{id}/chapters/{chapter_id}/insert` (需新增接口)。

### 3. 正文功能
- **下载**:
  - 正文右上角已有下载图标。
  - 点击触发下载当前章节内容 (`{title}.txt`)。

## 技术方案

### Backend (`backend/app/api/v1/projects.py`)
1.  **更新 GET /chapters**: 增加 `page`, `page_size` 参数。
2.  **新增 DELETE /chapters/{chapter_id}**: 删除指定章节。
3.  **新增 POST /chapters/upload**:
    - 参数: `prev_chapter_id` (用于定位插入位置), `file`.
    - 逻辑: 读取文件 -> 插入到 `prev_chapter_id` 之后 -> 重排后续章节序号。

### Frontend (`frontend/src/pages/user/Workspace.tsx`)
1.  **State**: `chapters` 改为追加模式，增加 `page` state。
2.  **UI**:
    - 列表项高度调整 (`py-4` -> `py-2`).
    - 增加删除按钮 (Hover 显示)。
    - 实现上传 Modal。
3.  **Logic**:
    - `handleLoadMore`: 请求下一页并追加。
    - `handleDelete`: 调用 API 并移除本地 state。
    - `handleUpload`: 调用 API 并刷新列表。
    - `handleDownload`: `Blob` 下载。

## 验收标准
- [ ] 章节列表支持分页加载，且行高更紧凑。
- [ ] 选中章节可删除。
- [ ] 可在选中章节后插入上传新章节（txt格式）。
- [ ] 点击下载按钮可下载当前章节文本。
