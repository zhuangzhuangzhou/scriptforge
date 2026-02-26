# 系统优化计划 - 子任务拆分

## 任务总览

| ID | 任务名称 | 优先级 | 预估 | 状态 |
|----|---------|-------|------|------|
| T1 | 新手引导系统 | P0 | 3天 | pending |
| T2 | 任务系统优化 | P0 | 3天 | pending |
| T3 | 邀请奖励系统 | P1 | 2天 | pending |
| T4 | 项目搜索功能 | P1 | 1天 | pending |
| T5 | 监控告警基础设施 | P2 | 3天 | pending |

---

## T1: 新手引导系统

### 子任务

| 序号 | 任务 | 类型 | 预估 |
|-----|------|-----|------|
| T1.1 | 创建 user_onboarding 表迁移 | 后端 | 0.5h |
| T1.2 | 创建 UserOnboarding 模型 | 后端 | 0.5h |
| T1.3 | 实现 onboarding API (status/step/claim/skip) | 后端 | 3h |
| T1.4 | 注册路由到 router.py | 后端 | 0.5h |
| T1.5 | 创建 OnboardingProvider 状态管理 | 前端 | 2h |
| T1.6 | 创建 OnboardingTour 引导组件 | 前端 | 3h |
| T1.7 | 创建 WelcomeModal 欢迎弹窗 | 前端 | 1h |
| T1.8 | 创建 RewardModal 奖励弹窗 | 前端 | 1h |
| T1.9 | 集成到 App.tsx | 前端 | 1h |
| T1.10 | 添加 onboardingApi 到 api.ts | 前端 | 0.5h |
| T1.11 | 测试完整流程 | 测试 | 2h |

### 依赖关系
```
T1.1 → T1.2 → T1.3 → T1.4
                ↓
T1.10 → T1.5 → T1.6 → T1.9
              ↘ T1.7 ↗
              ↘ T1.8 ↗
```

---

## T2: 任务系统优化

### 子任务

| 序号 | 任务 | 类型 | 预估 |
|-----|------|-----|------|
| T2.1 | 为 billing_records 添加 status 字段迁移 | 后端 | 0.5h |
| T2.2 | 实现 CreditsTransaction 类 | 后端 | 3h |
| T2.3 | 实现 TaskRecoveryService 类 | 后端 | 3h |
| T2.4 | 集成启动恢复到 main.py | 后端 | 1h |
| T2.5 | 配置 Celery Beat 定时任务 | 后端 | 1h |
| T2.6 | 重构 breakdown.py 使用新事务 | 后端 | 2h |
| T2.7 | 重构 scripts.py 使用新事务 | 后端 | 2h |
| T2.8 | 编写单元测试 | 测试 | 3h |
| T2.9 | 集成测试 | 测试 | 2h |

### 依赖关系
```
T2.1 → T2.2 → T2.6
         ↘ → T2.7
T2.3 → T2.4
     ↘ T2.5
```

---

## T3: 邀请奖励系统

### 子任务

| 序号 | 任务 | 类型 | 预估 |
|-----|------|-----|------|
| T3.1 | 创建 referral_codes/referral_records 表迁移 | 后端 | 0.5h |
| T3.2 | 创建 ReferralCode/ReferralRecord 模型 | 后端 | 0.5h |
| T3.3 | 实现 referral API (code/stats) | 后端 | 2h |
| T3.4 | 实现 process_referral 函数 | 后端 | 1h |
| T3.5 | 修改 auth.py 注册接口支持邀请码 | 后端 | 1h |
| T3.6 | 创建 Referral.tsx 邀请页面 | 前端 | 3h |
| T3.7 | 修改 Register.tsx 支持邀请码 | 前端 | 1h |
| T3.8 | 添加路由和 API | 前端 | 0.5h |
| T3.9 | 测试邀请流程 | 测试 | 1h |

### 依赖关系
```
T3.1 → T3.2 → T3.3 → T3.8 → T3.6
            ↘ T3.4 → T3.5 → T3.7
```

---

## T4: 项目搜索功能

### 子任务

| 序号 | 任务 | 类型 | 预估 |
|-----|------|-----|------|
| T4.1 | 实现 /projects/search API | 后端 | 2h |
| T4.2 | 创建 ProjectSearch.tsx 组件 | 前端 | 3h |
| T4.3 | 集成到 Dashboard.tsx | 前端 | 1h |
| T4.4 | 添加 searchProjects 到 api.ts | 前端 | 0.5h |
| T4.5 | 测试搜索功能 | 测试 | 1h |

### 依赖关系
```
T4.1 → T4.4 → T4.2 → T4.3
```

---

## T5: 监控告警基础设施

### 子任务

| 序号 | 任务 | 类型 | 预估 |
|-----|------|-----|------|
| T5.1 | 创建 metrics.py 定义指标 | 后端 | 2h |
| T5.2 | 实现 MetricsMiddleware | 后端 | 1h |
| T5.3 | 集成到 main.py | 后端 | 0.5h |
| T5.4 | 在关键位置埋点 | 后端 | 2h |
| T5.5 | 编写 docker-compose.yml | 运维 | 1h |
| T5.6 | 配置 prometheus.yml | 运维 | 1h |
| T5.7 | 配置 alerts.yml | 运维 | 1h |
| T5.8 | 创建 Grafana 仪表盘 | 运维 | 2h |
| T5.9 | 配置 AlertManager | 运维 | 1h |
| T5.10 | 部署测试 | 运维 | 2h |

### 依赖关系
```
T5.1 → T5.2 → T5.3 → T5.4
T5.5 → T5.6 → T5.7
     ↘ T5.8
     ↘ T5.9
```

---

## 执行顺序建议

```
Week 1: T1 (新手引导) + T4 (项目搜索)
Week 2: T2 (任务系统优化)
Week 3: T3 (邀请系统)
Week 4: T5 (监控告警)
```

## 里程碑

| 里程碑 | 日期 | 交付物 |
|-------|------|-------|
| M1 | Week 1 结束 | 新手引导上线，项目搜索可用 |
| M2 | Week 2 结束 | 积分事务稳定，任务恢复机制生效 |
| M3 | Week 3 结束 | 邀请系统上线，可开始推广 |
| M4 | Week 4 结束 | 监控仪表盘可用，告警配置完成 |
