# 剧集拆解配置系统 - 实施计划

## 实施策略：一次性完成所有6个阶段

### 实施顺序（按依赖关系）

#### 阶段1：后端基础设施（第1-4阶段）
**预计时间**: 4-6小时

1. **配置初始化脚本** (1小时)
   - 创建 `backend/scripts/init_breakdown_configs.py`
   - 解析3个方法论文档
   - 导入系统默认配置

2. **API 增强** (1.5小时)
   - 修改 `BreakdownStartRequest` 添加配置字段
   - 新增 `/available-configs` 端点
   - 测试 API 端点

3. **PipelineExecutor 集成** (1.5小时)
   - 添加配置读取方法
   - 修改 `run_breakdown()` 支持配置注入

4. **Celery 任务集成** (1小时)
   - 修改 `run_breakdown_task` 传递配置
   - 测试配置传递链路

#### 阶段2：前端实现（第5-6阶段）
**预计时间**: 3-4小时

5. **ConfigSelector 组件** (1.5小时)
   - 创建 `ConfigSelector.tsx`
   - 实现3个下拉选择器
   - 测试组件独立功能

6. **Workspace 集成** (1小时)
   - 在 PlotTab 中集成 ConfigSelector
   - 修改启动拆解逻辑传递配置

7. **API Service 层** (0.5小时)
   - 修改 `breakdownApi.start()`
   - 新增 `getAvailableConfigs()`

8. **AIConfigurationModal 增强** (0.5小时)
   - 添加配置使用说明

#### 阶段3：验证与测试
**预计时间**: 1-2小时

9. **后端验证**
   - 运行配置初始化脚本
   - 验证数据库配置
   - 测试 API 端点

10. **前端验证**
    - 测试配置选择器
    - 测试启动拆解流程
    - 验证配置正确传递

11. **端到端测试**
    - 完整流程测试
    - 用户自定义配置测试

### 总预计时间：8-12小时

## 关键依赖关系

```
配置脚本 → API增强 → PipelineExecutor → Celery任务
                ↓
         ConfigSelector → Workspace集成 → 端到端测试
```

## 实施检查点

- [x] Checkpoint 1: 配置脚本运行成功，数据库有3个配置 ✅ (2026-02-08)
- [x] Checkpoint 2: API 端点测试通过 ✅ (2026-02-08)
- [x] Checkpoint 3: ConfigSelector 组件独立测试通过 ✅ (2026-02-08)
- [x] Checkpoint 4: Workspace 集成完成 ✅ (2026-02-08)
- [ ] Checkpoint 5: 端到端测试通过 (待测试)

## 风险控制

1. **配置解析风险**：方法论文档结构复杂，可能需要调整解析逻辑
2. **API 兼容性**：确保新增字段不影响现有功能
3. **前端状态管理**：配置状态需要正确管理

## 回滚策略

- 每个阶段完成后立即 git commit
- 如果某个阶段失败，可以回滚到上一个检查点
- 保持现有功能不受影响
