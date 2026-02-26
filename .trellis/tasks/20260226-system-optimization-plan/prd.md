# 系统优化计划 PRD

## 概述

基于对系统的全面梳理，从用户体验、系统架构、运营三个维度制定优化方案，预计 4 周完成。

## 背景

当前系统核心流程已跑通（上传小说 → 章节拆分 → 剧情拆解 → 剧本生成 → 导出），但存在以下问题：

1. **用户体验**：新用户不知道如何开始，缺少引导；项目多了无法搜索
2. **系统架构**：积分事务分散，任务失败可能导致积分泄漏；缺少监控告警
3. **运营增长**：缺少用户裂变机制，付费转化路径不清晰

---

## 一、新手引导系统

### 1.1 目标
- 降低新用户流失率
- 提升用户激活率（完成首个项目）

### 1.2 功能设计

#### 数据模型
```sql
CREATE TABLE user_onboarding (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),

    -- 引导步骤
    welcome_seen BOOLEAN DEFAULT FALSE,
    tour_completed BOOLEAN DEFAULT FALSE,
    first_project_created BOOLEAN DEFAULT FALSE,
    first_upload_done BOOLEAN DEFAULT FALSE,
    first_breakdown_done BOOLEAN DEFAULT FALSE,
    first_script_done BOOLEAN DEFAULT FALSE,

    -- 奖励状态
    welcome_credits_claimed BOOLEAN DEFAULT FALSE,
    first_project_credits_claimed BOOLEAN DEFAULT FALSE,

    skipped_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### API 端点
| 方法 | 路径 | 说明 |
|-----|------|-----|
| GET | /onboarding/status | 获取引导状态 |
| POST | /onboarding/step | 更新引导步骤 |
| POST | /onboarding/claim-reward/{type} | 领取奖励 |
| POST | /onboarding/skip | 跳过引导 |

#### 奖励配置
- 完成引导：+100 积分
- 创建首个项目：+50 积分

### 1.3 前端组件
- `OnboardingProvider`: 状态管理
- `OnboardingTour`: 功能引导弹窗
- `WelcomeModal`: 欢迎页
- `RewardModal`: 奖励领取弹窗

### 1.4 验收标准
- [ ] 新用户注册后自动显示欢迎页
- [ ] 引导流程可跳过
- [ ] 奖励正确发放并记录账单
- [ ] 引导状态持久化

---

## 二、任务系统优化

### 2.1 目标
- 解决积分泄漏风险
- 实现任务状态恢复
- 检测超时任务

### 2.2 统一积分事务管理

#### 核心类：CreditsTransaction
```python
class CreditsTransaction:
    async def reserve(user, task_id, credits, description) -> dict
    async def confirm(task_id) -> bool
    async def rollback(task_id, user_id, reason) -> dict
```

#### 使用方式
```python
async with credits_transaction(db, user, "breakdown", 50) as tx:
    task = create_task(...)
    tx.task_id = task.id
# 自动处理：成功则确认，异常则返还
```

### 2.3 任务状态恢复

#### 核心类：TaskRecoveryService
```python
class TaskRecoveryService:
    async def recover_interrupted_tasks() -> dict  # 服务启动时调用
    async def check_timeout_tasks(timeout_minutes=30) -> dict  # 定时调用
```

#### 恢复逻辑
1. 服务启动时检查 RUNNING/IN_PROGRESS 状态的任务
2. 查询 Celery 任务实际状态
3. 状态不一致则修正，失败则返还积分

### 2.4 验收标准
- [ ] 任务失败自动返还积分
- [ ] 服务重启后任务状态正确恢复
- [ ] 超时任务自动标记失败
- [ ] 账单记录完整

---

## 三、用户增长：邀请系统

### 3.1 目标
- 实现用户裂变增长
- 降低获客成本

### 3.2 功能设计

#### 数据模型
```sql
-- 邀请码表
CREATE TABLE referral_codes (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    code VARCHAR(12) UNIQUE NOT NULL,
    total_referrals INT DEFAULT 0,
    total_credits_earned INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 邀请记录表
CREATE TABLE referral_records (
    id UUID PRIMARY KEY,
    referrer_id UUID NOT NULL,
    referee_id UUID NOT NULL UNIQUE,
    referrer_rewarded BOOLEAN DEFAULT FALSE,
    referee_rewarded BOOLEAN DEFAULT FALSE,
    referrer_credits INT DEFAULT 0,
    referee_credits INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### API 端点
| 方法 | 路径 | 说明 |
|-----|------|-----|
| GET | /referral/code | 获取/创建邀请码 |
| GET | /referral/stats | 获取邀请统计 |

#### 奖励配置
- 邀请人：+200 积分
- 被邀请人：+100 积分

### 3.3 前端页面
- 邀请码展示
- 一键复制链接
- 分享到社交平台
- 邀请统计和记录

### 3.4 验收标准
- [ ] 每个用户有唯一邀请码
- [ ] 通过邀请链接注册自动关联
- [ ] 双方奖励正确发放
- [ ] 邀请统计准确

---

## 四、项目搜索功能

### 4.1 目标
- 项目多时快速定位
- 支持多维度筛选

### 4.2 功能设计

#### API 端点
```
GET /projects/search?keyword=&status=&novel_type=&sort_by=&sort_order=&page=&page_size=
```

#### 支持的筛选
- 关键词：项目名称、描述
- 状态：draft, uploaded, ready, parsing, scripting, completed
- 小说类型
- 排序：更新时间、创建时间、名称

### 4.3 前端组件
- 搜索输入框（防抖）
- 筛选面板（可折叠）
- 排序选择器

### 4.4 验收标准
- [ ] 搜索响应 < 500ms
- [ ] 筛选条件可组合
- [ ] 支持分页
- [ ] 清除筛选功能

---

## 五、监控告警基础设施

### 5.1 目标
- 实时监控系统状态
- 异常自动告警

### 5.2 技术选型
- 指标采集：Prometheus
- 可视化：Grafana
- 告警：AlertManager
- 日志：Loki

### 5.3 核心指标

#### 业务指标
| 指标名 | 说明 |
|-------|-----|
| scriptflow_users_total | 用户数（按等级） |
| scriptflow_projects_total | 项目数（按状态） |
| scriptflow_tasks_total | 任务数（按类型和状态） |
| scriptflow_tasks_duration_seconds | 任务执行时长 |
| _credits_consumed_total | 积分消耗 |
| scriptflow_llm_calls_total | LLM 调用次数 |
| scriptflow_llm_latency_seconds | LLM 调用延迟 |

#### 系统指标
| 指标名 | 说明 |
|-------|-----|
| scriptflow_http_requests_total | HTTP 请求数 |
| scriptflow_http_request_duration_seconds | HTTP 请求延迟 |

### 5.4 告警规则
| 告警名 | 条件 | 级别 |
|-------|-----|-----|
| ServiceDown | 服务停止响应 > 1min | critical |
| HighErrorRate | 5xx 错误率 > 5% | warning |
| TaskQueueBacklog | 任务积压 > 50 | warning |
| LLMErrorRateHigh | LLM 错误率 > 10% | critical |

### 5.5 验收标准
- [ ] Prometheus 正常采集指标
- [ ] Grafana 仪表盘可用
- [ ] 告警规则生效
- [ ] 告警通知到达

---

## 六、实施计划

### 第 1 周：基础优化
| 任务 | 负责 | 预估 |
|-----|-----|-----|
| 新手引导后端 API | 后端 | 1.5 天 |
| 新手引导前端组件 | 前端 | 1.5 天 |
| 项目搜索功能 | 全栈 | 1 天 |

### 第 2 周：任务系统
| 任务 | 负责 | 预估 |
|-----|-----|-----|
| 积分事务管理器 | 后端 | 1 天 |
| 任务恢复服务 | 后端 | 1 天 |
| 集成测试 | 后端 | 1 天 |

### 第 3 周：用户增长
| 任务 | 负责 | 预估 |
|-----|-----|-----|
| 邀请系统后端 | 后端 | 1 天 |
| 邀请页面前端 | 前端 | 1 天 |
| 注册流程集成 | 全栈 | 0.5 天 |

### 第 4 周：监控告警
| 任务 | 负责 | 预估 |
|-----|-----|-----|
| Prometheus 埋点 | 后端 | 1 天 |
| Grafana 仪表盘 | 运维 | 1 天 |
| AlertManager 配置 | 运维 | 0.5 天 |

---

## 七、风险与依赖

### 风险
1. 新手引导可能影响老用户体验 → 仅对新注册用户启用
2. 积分事务改造涉及核心逻辑 → 充分测试，灰度发布
3. 监控系统增加运维复杂度 → 使用 Docker Compose 简化部署

### 依赖
- 数据库迁移工具（Alembic）
- Docker 环境
- 告警通知渠道（邮件/钉钉）
