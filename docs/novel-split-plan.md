# 小说拆分与结构化存储功能实现计划

本文档记录了关于小说文件拆分、混合存储、批量读取及 Skill 处理功能的讨论结果与实现计划。

## 1. 核心需求
1. **智能拆分**：支持将 Word (.docx) 文件按规则（如“中文 - 第N章”）拆分为独立章节。
2. **规则管理**：后台管理系统可配置拆分正则表达式，前端用户选择规则。
3. **混合存储**：
   - 小章节 (≤5万字) 存储在数据库 `chapters.content`。
   - 大章节 (>5万字) 存储在 MinIO，数据库存储路径引用。
4. **批量读取与 Skill 处理**：
   - 支持按项目/用户查询章节列表。
   - 支持一次读取 N 个章节作为上下文发送给大模型。
   - 读取结果需经过用户指定的 Skill 处理，输出格式化的结构化 JSON。

## 2. 数据模型设计

### 2.1 拆分规则表 (SplitRule)
存储在 `split_rules` 表中：
- `id`: UUID
- `name`: 规则内部标识 (如 standard_chinese)
- `display_name`: 给用户显示的名称 (如 中文 - 第N章)
- `pattern`: 正则表达式模式
- `pattern_type`: 模式类型 (默认 regex)
- `example`: 示例文字
- `is_default`: 是否默认
- `is_active`: 是否启用

### 2.2 Chapter 模型扩展
为 `chapters` 表新增字段：
- `txt_file_path`: MinIO 中的存储路径 (用于大章节)
- `txt_file_size`: 文件大小
- `skill_processed`: JSONB，存储最近一次 Skill 处理的结果快照

### 2.3 Batch 模型扩展
为 `batches` 表新增字段：
- `ai_processed`: 是否经过 AI 处理
- `context_size`: 每批次推荐的章节数量

## 3. 接口设计

### 3.1 Admin：拆分规则管理
- `GET /api/v1/admin/split-rules`: 获取规则列表
- `POST /api/v1/admin/split-rules`: 创建规则
- `PUT /api/v1/admin/split-rules/{id}`: 更新规则
- `DELETE /api/v1/admin/split-rules/{id}`: 删除规则

### 3.2 项目上传与拆分
- `POST /api/v1/projects/split`: 上传文件并自动拆分章节
  - 参数：`file`, `project_name` (可选), `split_rule_id` (可选), `context_size` (可选)

### 3.3 章节查询与读取
- `GET /api/v1/projects/{id}/chapters`: 获取章节列表
- `GET /api/v1/projects/{id}/chapters/{chapter_id}`: 获取单章详情
- `POST /api/v1/projects/{id}/chapters/batch-read`: 批量读取并处理
  - 参数：`start_chapter`, `batch_size`, `skill_id` (必填)
  - 逻辑：读取 N 章内容 -> 调用指定 Skill -> 返回结构化 JSON

## 4. 存储逻辑
1. 用户上传文件。
2. `DocxParser` 解析为全文。
3. `ChapterSplitter` 按选定 `SplitRule` 拆分为章节数组。
4. 遍历章节：
   - 如果字数超过阈值，调用 `MinIOClient` 上传 `.txt`。
   - 否则直接存入数据库字段。
5. 自动创建 `Batch` 记录，关联章节。

## 5. 实现阶段
- **Phase 1**: 数据库模型与迁移。
- **Phase 2**: 章节拆分服务与混合存储逻辑。
- **Phase 3**: 管理后台规则管理 API。
- **Phase 4**: 项目上传与拆分接口实现。
- **Phase 5**: 批量读取与 Skill 处理逻辑集成。
- **Phase 6**: 连通性测试。

## 6. 预设规则
| 名称 | 显示名称 | 正则表达式 |
|---|---|---|
| standard_chinese | 中文 - 第N章 | `第[一二三四五六七八九十百千\d]+章` |
| chinese_prefix | 中文 - 第N章 标题 | `第[一二三四五六七八九十百千\d]+章\s*[-–—]\s*\S+` |
| english_chapter | English - Chapter N | `Chapter\s+\d+` |
