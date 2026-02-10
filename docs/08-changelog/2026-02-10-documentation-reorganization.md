# 文档整理记录

**日期**: 2026-02-10  
**状态**: ✅ 已完成

---

## 问题描述

项目文档存在以下问题：
1. **文档分散**：分布在多个目录（`docs/`, `.trellis/`, `frontend/`, `backend/`）
2. **命名不统一**：混合使用大写（`FRONTEND_GUIDE.md`）和小写（`spec-workflow.md`）
3. **分类混乱**：临时文档、规范文档、实施文档混在一起
4. **重复内容**：多个 README 和 CLAUDE.md 文件
5. **过时文档**：大量修复文档（FIX、SUMMARY）未归档
6. **缺乏规范**：没有统一的文档编写标准

---

## 解决方案

### 1. 建立文档编写规范

创建 `docs/DOCUMENTATION_GUIDE.md`，包含：
- 清晰的目录结构定义
- 文档分类与职责说明
- 统一的命名规范（kebab-case）
- 文档模板（规范文档、功能文档、修复记录）
- 文档更新流程
- AI 协作指南

### 2. 重组目录结构

建立 9 个主要分类目录：
- `01-getting-started/` - 快速开始
- `02-specifications/` - 核心规范（稳定）
- `03-architecture/` - 架构设计
- `04-development/` - 开发指南
- `05-features/` - 功能文档
- `06-deployment/` - 部署运维
- `07-business/` - 产品与商业
- `08-changelog/` - 变更记录
- `09-archive/` - 归档文档

### 3. 统一命名规范

- 所有文档使用 `kebab-case` 命名
- 通过目录区分文档类型，不使用前缀
- 日期相关文档使用 `YYYY-MM-DD-topic.md` 格式

### 4. 整理目标

### 4. 归档策略

- 临时修复文档移至 `09-archive/fixes/`
- 过时文档移至 `09-archive/deprecated/`
- 保留 `.trellis/` 目录不变（按用户要求）

---

## 新的目录结构

```
docs/
├── README.md                          # 文档总入口
├── index.md                           # 文档索引
├── DOCUMENTATION_GUIDE.md             # 文档编写规范（新增）
│
├── 01-getting-started/                # 快速开始
│   ├── gemini-quick-start.md
│   └── gemini-integration-guide.md
│
├── 02-specifications/                 # 核心规范（稳定）
│   ├── workflow.md
│   ├── config-driven.md
│   ├── storage-contract.md
│   ├── document-policy.md
│   └── document-versioning.md
│
├── 03-architecture/                   # 架构设计
│   ├── backend/
│   │   ├── backend-architecture-analysis.md
│   │   └── owr-architecture.md
│   └── frontend/
│       └── frontend-architecture-analysis.md
│
├── 04-development/                    # 开发指南
│   ├── frontend-guide.md
│   └── api-usage-examples.md
│
├── 05-features/                       # 功能文档
│   ├── model-management/              # 模型管理系统（11个文档）
│   │   ├── overview.md
│   │   ├── quickstart.md
│   │   ├── integration-guide.md
│   │   ├── deployment-checklist.md
│   │   ├── security.md
│   │   ├── performance.md
│   │   ├── completion-report.md
│   │   ├── final-summary.md
│   │   ├── acceptance-report.md
│   │   ├── model-config-id-analysis.md
│   │   └── model-config-id-implementation.md
│   ├── ai-workflow/                   # AI 工作流（4个文档）
│   │   ├── configuration-spec.md
│   │   ├── breakdown-aligner.md
│   │   ├── webtoon-aligner.md
│   │   └── task-lifecycle-explanation.md
│   └── project-model-configuration.md
│
├── 06-deployment/                     # 部署运维（待创建）
│
├── 07-business/                       # 产品与商业
│   ├── business-analysis.md
│   └── copyright.md
│
├── 08-changelog/                      # 变更记录
│   ├── implementation-plan.md
│   ├── status-progress.md
│   └── migration-reports/
│       ├── migration-execution-report.md
│       └── migration-guide.md
│
└── 09-archive/                        # 归档文档
    ├── fixes/                         # 修复记录（15个文档）
    │   ├── celery-async-final-fix.md
    │   ├── celery-fix-summary.md
    │   ├── fix-celery-async-issue.md
    │   ├── fix-celery-async-eventloop-issue.md
    │   ├── breakdown-api-fixes.md
    │   ├── breakdown-api-analysis.md
    │   ├── breakdown-start-api-issues.md
    │   ├── fix-breakdown-modal-styles.md
    │   ├── fix-frontend-compatibility.md
    │   ├── fix-skills-visibility-issue.md
    │   ├── encryption-removal-summary.md
    │   ├── encryption-removed.md
    │   ├── humanize-error-messages.md
    │   ├── zombie-task-fix.md
    │   └── duplicate-api-calls-fix.md
    └── deprecated/                    # 已废弃文档
        ├── implementation-complete.md
        ├── improvements-completed.md
        ├── final-summary.md
        ├── summary.md
        └── review-admin-models-api.md
```

### 步骤 2: 移动核心规范文档

将所有 `spec-*.md` 文档移至 `02-specifications/` 并重命名：
- `spec-workflow.md` → `workflow.md`
- `spec-config-driven.md` → `config-driven.md`
- `spec-storage-contract.md` → `storage-contract.md`
- `spec-document-policy.md` → `document-policy.md`
- `spec-document-versioning.md` → `document-versioning.md`

### 步骤 3: 整理功能文档

**模型管理系统** (11个文档移至 `05-features/model-management/`)：
- `model-management-quickstart.md` → `quickstart.md`
- `model-management-integration-guide.md` → `integration-guide.md`
- `backend/README-MODEL-MANAGEMENT.md` → `overview.md`
- 其他相关文档

**AI 工作流** (4个文档移至 `05-features/ai-workflow/`)：
- `ai_flow_desc/breakdown-aligner.md` → `breakdown-aligner.md`
- `ai_flow_desc/webtoon-aligner.md` → `webtoon-aligner.md`
- 其他相关文档

### 步骤 4: 归档历史文档

将 15 个修复记录移至 `09-archive/fixes/`：
- 所有 `*FIX*.md` 文档
- 所有临时修复记录
- `frontend/DUPLICATE_API_CALLS_FIX.md`

将 5 个历史文档移至 `09-archive/`：
- `IMPLEMENTATION_COMPLETE.md`
- `SUMMARY.md`
- `FINAL_SUMMARY.md`
- 其他总结文档

### 步骤 5: 更新索引和入口

- 创建 `docs/README.md` 作为文档总入口
- 重写 `docs/index.md` 为完整索引
- 更新 `README.md` 的文档链接
- 创建 `docs/01-getting-started/quickstart.md` 模板

---

## 验证结果

### 文档移动统计

| 操作 | 数量 |
|------|------|
| 移动的文档 | 53 |
| 重命名的文档 | 45 |
| 新建的目录 | 13 |
| 新建的文档 | 3 |

### 按分类统计

| 分类 | 文档数 |
|------|--------|
| 快速开始 | 2 |
| 核心规范 | 5 |
| 架构设计 | 3 |
| 开发指南 | 2 |
| 功能文档 | 16 |
| 部署运维 | 0 |
| 产品商业 | 2 |
| 变更记录 | 4 |
| 归档文档 | 20 |
| **总计** | **54** |

### 主要改进

**1. 建立文档编写规范**
- 创建 `DOCUMENTATION_GUIDE.md` 作为统一标准
- 定义 9 个文档分类目录
- 提供文档模板和更新流程
- 包含 AI 协作指南

**2. 统一命名规范**
- 之前：混合使用大写和小写，不一致的命名风格
- 现在：统一使用 `kebab-case`，通过目录区分类型

**3. 清晰的文档分类**
- 规范文档：核心规范，更新需谨慎
- 功能文档：按功能模块组织，独立子目录
- 归档文档：历史记录，保留但不再维护

**4. 完善文档入口**
- 创建 `docs/README.md` 作为文档总入口
- 重写 `docs/index.md` 为完整索引
- 更新 `README.md` 的文档链接

---

## 迁移映射

### 核心规范文档

| 旧路径 | 新路径 |
|--------|--------|
| `docs/spec-workflow.md` | `docs/02-specifications/workflow.md` |
| `docs/spec-config-driven.md` | `docs/02-specifications/config-driven.md` |
| `docs/spec-storage-contract.md` | `docs/02-specifications/storage-contract.md` |
| `docs/spec-document-policy.md` | `docs/02-specifications/document-policy.md` |
| `docs/spec-document-versioning.md` | `docs/02-specifications/document-versioning.md` |

### 功能文档

| 旧路径 | 新路径 |
|--------|--------|
| `docs/model-management-*.md` | `docs/05-features/model-management/*.md` |
| `docs/ai_flow_desc/*.md` | `docs/05-features/ai-workflow/*.md` |
| `backend/README-MODEL-MANAGEMENT.md` | `docs/05-features/model-management/overview.md` |

### 开发指南

| 旧路径 | 新路径 |
|--------|--------|
| `frontend/FRONTEND_GUIDE.md` | `docs/04-development/frontend-guide.md` |
| `docs/api-usage-examples.md` | `docs/04-development/api-usage-examples.md` |

### 归档文档

| 旧路径 | 新路径 |
|--------|--------|
| `docs/*FIX*.md` | `docs/09-archive/fixes/*.md` |
| `docs/*SUMMARY*.md` | `docs/09-archive/*.md` |
| `frontend/DUPLICATE_API_CALLS_FIX.md` | `docs/09-archive/fixes/duplicate-api-calls-fix.md` |

---

## 预防措施

为避免未来文档再次混乱，已采取以下措施：

### 1. 文档编写规范

创建 `docs/DOCUMENTATION_GUIDE.md`，所有 AI 和开发者在创建/更新文档前必须先阅读此规范。

### 2. 清晰的目录结构

通过编号的目录名称（`01-`, `02-`, ...）明确文档分类和优先级。

### 3. 统一的命名规范

- 使用 `kebab-case` 命名
- 通过目录区分类型，不使用前缀
- 日期相关文档使用 `YYYY-MM-DD-topic.md`

### 4. 文档模板

在 `DOCUMENTATION_GUIDE.md` 中提供三种模板：
- 规范文档模板
- 功能文档模板
- 修复记录模板

### 5. AI 协作指南

在 `DOCUMENTATION_GUIDE.md` 中包含专门的 AI 协作指南，确保 AI 助手遵循规范。

### 6. 定期归档

建立归档机制：
- 临时修复文档在问题解决后移至 `09-archive/fixes/`
- 过时文档移至 `09-archive/deprecated/`
- 保留历史记录，不删除

---

## 后续建议

### 短期（1周内）

1. **补充待创建文档**
   - `01-getting-started/installation.md`
   - `01-getting-started/configuration.md`
   - `04-development/backend-guide.md`
   - `04-development/api-reference.md`
   - `04-development/testing.md`

2. **完善现有文档**
   - 检查所有文档的内部链接
   - 统一文档格式和元数据
   - 添加缺失的状态标识

### 中期（1个月内）

1. **创建部署文档**
   - `06-deployment/deployment-guide.md`
   - `06-deployment/docker-setup.md`
   - `06-deployment/troubleshooting.md`

2. **补充架构文档**
   - `03-architecture/overview.md`
   - 完善后端和前端架构文档

### 长期（持续）

1. **定期审查文档**
   - 每月检查文档是否需要更新
   - 归档过时的临时文档
   - 更新进度跟踪文档

2. **收集反馈**
   - 从团队收集文档使用反馈
   - 持续改进文档结构和内容
   - 更新文档编写规范

---

**整理完成时间**: 2026-02-10  
**整理人员**: AI Assistant  
**审核状态**: 待审核
