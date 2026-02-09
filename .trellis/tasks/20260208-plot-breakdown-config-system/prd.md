# 剧集拆解配置系统：方法论导入与API增强

## 目标 (Goal)

将 `docs/ai_flow_desc/` 下的 AI 工作流方法论文档导入到现有的 `AIConfiguration` 系统，并增强 Breakdown API 和前端 UI，使用户可以在启动拆解时选择和自定义配置。

## 背景 (Context)

当前系统已具备：
- ✅ `AIConfiguration` 模型 + `/api/v1/configurations` API
- ✅ 前端 `AIConfigurationModal` 配置管理界面
- ✅ 用户级配置覆盖机制（user_id=NULL 为系统默认，user_id=用户ID 为自定义）

需要实现：
- ❌ 将方法论文档（adapt-method.md, breakdown-aligner.md, output-style.md）导入数据库
- ❌ Breakdown API 支持配置选择参数
- ❌ 前端 ConfigSelector 组件
- ❌ Workspace PLOT Tab 集成配置选择

## 需求 (Requirements)

### P0 - 核心功能（本次实现）

#### 1. 配置初始化脚本
- **文件**：`backend/scripts/init_breakdown_configs.py`
- **功能**：
  - 解析 `docs/ai_flow_desc/webtoon-skill/adapt-method.md`
  - 解析 `docs/ai_flow_desc/breakdown-aligner.md`
  - 解析 `docs/ai_flow_desc/webtoon-skill/output-style.md`
  - 提取结构化配置（冲突分级、情绪钩子评分、质检维度等）
  - 写入 `ai_configurations` 表（user_id=NULL，系统默认配置）
- **配置 Key**：
  - `adapt_method_default` (category: adapt_method)
  - `qa_breakdown_default` (category: quality_rule)
  - `output_style_default` (category: prompt_template)

#### 2. Breakdown API 增强
- **文件**：`backend/app/api/v1/breakdown.py`
- **修改**：
  - 在 `BreakdownStartRequest` 中新增字段：
    - `adapt_method_key: Optional[str] = "adapt_method_default"`
    - `quality_rule_key: Optional[str] = "qa_breakdown_default"`
    - `output_style_key: Optional[str] = "output_style_default"`
  - 将配置 Key 保存到 `AITask.config` 字段
  - 新增端点 `GET /available-configs`：返回可用的配置列表（系统默认 + 用户自定义）

#### 3. 前端 ConfigSelector 组件
- **文件**：`frontend/src/components/ConfigSelector.tsx`（新建）
- **功能**：
  - 3 个下拉选择器：适配方法、质检规则、输出风格
  - 调用 `/api/v1/breakdown/available-configs` 加载配置列表
  - 显示配置描述和标签（系统默认 / 用户自定义）
  - 支持受控组件模式（value + onChange）

#### 4. Workspace PLOT Tab 集成
- **文件**：`frontend/src/pages/user/Workspace.tsx`
- **修改**：
  - 在拆解配置弹窗中集成 `ConfigSelector` 组件
  - 启动拆解时传递配置参数到 API

#### 5. API Service 层
- **文件**：`frontend/src/services/api.ts`
- **修改**：
  - `breakdownApi.start()` 新增配置参数
  - 新增 `breakdownApi.getAvailableConfigs()` 方法

## 验收标准 (Acceptance Criteria)

### 后端
- [ ] 运行 `python backend/scripts/init_breakdown_configs.py` 成功导入 3 个配置
- [ ] 数据库中 `ai_configurations` 表包含系统默认配置（user_id=NULL）
- [ ] `POST /api/v1/breakdown/start` 接受配置参数并保存到 `AITask.config`
- [ ] `GET /api/v1/breakdown/available-configs` 返回配置列表

### 前端
- [ ] `ConfigSelector` 组件正确显示配置列表
- [ ] Workspace PLOT Tab 拆解配置弹窗包含配置选择器
- [ ] 启动拆解时配置参数正确传递到后端

### 测试
- [ ] 后端 API 测试通过（curl 或 Python 脚本验证）
- [ ] 前端功能测试通过（可选择配置并启动拆解）
- [ ] 用户可在 AIConfigurationModal 中克隆系统配置并修改

## 技术注意事项

### 后端
1. **配置解析**：从 Markdown 文档中提取关键结构（冲突级别关键词、评分标准、质检维度）
2. **幂等性**：使用 `db.merge()` 确保脚本可重复运行
3. **异步 API**：遵循 FastAPI + AsyncSession 模式
4. **类型注解**：强制使用 Type Hints

### 前端
1. **Glass UI 风格**：使用 `GlassSelect` 组件保持视觉一致性
2. **状态管理**：配置选择状态存储在 Workspace 组件
3. **类型定义**：为 ConfigSelector props 定义 TypeScript 接口
4. **错误处理**：API 调用失败时显示友好提示

## 文件清单

### 新建文件
- `backend/scripts/init_breakdown_configs.py`
- `frontend/src/components/ConfigSelector.tsx`

### 修改文件
- `backend/app/api/v1/breakdown.py`
- `frontend/src/pages/user/Workspace.tsx`
- `frontend/src/services/api.ts`

### 参考文件
- `backend/app/api/v1/configurations.py`（配置 API 参考）
- `frontend/src/components/modals/AIConfigurationModal.tsx`（配置管理界面参考）
- `frontend/src/components/SkillSelector.tsx`（选择器组件模式参考）

## 依赖资源
- `docs/ai_flow_desc/webtoon-skill/adapt-method.md`（方法论源文档）
- `docs/ai_flow_desc/breakdown-aligner.md`（质检规则源文档）
- `docs/ai_flow_desc/webtoon-skill/output-style.md`（输出风格源文档）
- `backend/app/models/ai_configuration.py`（AIConfiguration 模型）
- `frontend/src/components/ui/GlassSelect.tsx`（Glass UI 组件）
