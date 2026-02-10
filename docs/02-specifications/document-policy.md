# 文档使用与更新策略

版本：v1.2.0
更新日期：2026-02-05

## 目标
明确文档类型与更新频率，防止流程口径与实施进度混淆。

---

## 一、规范文档（应稳定）

这些文档用于定义统一口径和规则，应保持稳定，更新需谨慎：
- `docs/spec-workflow.md`：系统流程规范
- `docs/spec-config-driven.md`：配置驱动规范
- `docs/spec-storage-contract.md`：数据与文件关系
- `docs/spec-document-policy.md`：文档使用与更新策略
- `docs/spec-document-versioning.md`：文档版本号规范
- `.trellis/spec/frontend/index.md`：前端开发规范
- `.trellis/spec/backend/index.md`：后端开发规范
- `.trellis/spec/guides/index.md`：通用开发指南
- `.trellis/workflow.md`：Trellis 工作流

更新原则：
- 只有在流程/规范发生明确变化时更新
- 更新后需同步 README 和 docs/index.md

---

## 二、实施进度文档（可频繁更新）

这些文档用于跟踪状态和进度，可以频繁更新：
- `docs/status-progress.md`
- `docs/plan-implementation.md`
- `.zcf/plan/current/小说改编剧本系统.md`

更新原则：
- 进度更新需注明日期
- 与规范文档不冲突

---

## 三、日志文档（历史记录）

这些文档为历史记录或阶段性问题记录：
- `docs/log-2026-02-03-auth-integration.md`

更新原则：
- 不与现行规范冲突
- 保留为历史参考

---

## 四、产品与商业文档

这些文档用于策略与商业模型：
- `docs/product-business-analysis.md`
- `docs/product-copyright.md`

更新原则：
- 可以随策略调整而更新
- 需保证与系统能力描述一致

---

## 五、索引与入口

入口文档负责导航与快速定位：
- `README.md`
- `docs/index.md`

更新原则：
- 新增或移动文档时必须同步

---

## 六、命名规则（统一规范）

**通用规则**
- 文件名统一使用小写 `kebab-case`
- 命名清晰、可读，避免缩写
- 文档分类以“名称语义”区分，不强制目录拆分

**分类命名**
- 规范文档：`spec-<name>.md`（示例：`spec-workflow.md`）
- 进度/计划：`status-<name>.md`、`plan-<name>.md`
- 产品/商业：`product-<name>.md`
- 日志文档：`log-YYYY-MM-DD-<topic>.md`（示例：`log-2026-02-03-auth-integration.md`）
- 索引入口：`index.md`

更新记录：
- 2026-02-05 v1.0.0 初版整理与流程口径统一
- 2026-02-05 v1.1.0 补充文档命名规则与统一约束
- 2026-02-05 v1.2.0 文档命名前缀统一（spec/plan/status/product/log）
