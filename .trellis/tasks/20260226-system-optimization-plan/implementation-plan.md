# 系统优化计划 - 实施方案

## 概述

本文档包含各模块的详细实施方案，供开发参考。

---

## 一、新手引导系统

### 1.1 数据库迁移

```python
# backend/alembic/versions/20260226_add_onboarding.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '20260226_add_onboarding'
down_revision = 'xxx'  # 替换为实际的上一个版本

def upgrade():
    op.create_table(
        'user_onboarding',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('welcome_seen', sa.Boolean, default=False),
        sa.Column('tour_completed', sa.Boolean, default=False),
        sa.Column('first_project_created', sa.Boolean, default=False),
        sa.Column('first_upload_done', sa.Boolean, default=False),
        sa.Column('first_breakdown_done', sa.Boolean, default=False),
        sa.Column('first_script_done', sa.Boolean, default=False),
        sa.Column('welcome_credits_claimed', sa.Boolean, default=False),
        sa.Column('first_project_credits_claimed', sa.Boolean, default=False),
        sa.Column('skipped_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_user_onboarding_user_id', 'user_onboarding', ['user_id'])

def downgrade():
    op.drop_table('user_onboarding')
```

### 1.2 后端文件清单

| 文件 | 说明 |
|-----|-----|
| `backend/app/models/onboarding.py` | 数据模型 |
| `backend/app/api/v1/onboarding.py` | API 路由 |
| `backend/app/api/v1/router.py` | 注册路由 |

### 1.3 前端文件清单

| 文件 | 说明 |
|-----|-----|
| `frontend/src/components/Onboarding/OnboardingProvider.tsx` | 状态管理 |
| `frontend/src/components/Onboarding/OnboardingTour.tsx` | 引导弹窗 |
| `frontend/src/components/Onboarding/WelcomeModal.tsx` | 欢迎页 |
| `frontend/src/components/Onboarding/RewardModal.tsx` | 奖励弹窗 |
| `frontend/src/services/api.ts` | 添加 onboardingApi |

---

## 二、任务系统优化

### 2.1 后端文件清单

| 文件 | 说明 |
|-----|-----|
| `backend/app/core/credits_transaction.py` | 积分事务管理器 |
| `backend/app/core/task_recovery.py` | 任务恢复服务 |
| `backend/app/main.py` | 集成启动恢复 |

### 2.2 数据库变更

```sql
-- 为 billing_records 添加 status 字段
ALTER TABLE billing_records ADD COLUMN status VARCHAR(20) DEFAULT 'confirmed';
-- 可选值: pending, confirmed, refunded
```

### 2.3 Celery Beat 配置

```python
# backend/app/core/celery_config.py

CELERY_BEAT_SCHEDULE = {
    'check-timeout-tasks': {
        'task': 'app.core.task_recovery.check_timeout_tasks_periodic',
        'schedule': 300.0,  # 每 5 分钟
    },
}
```

---

## 三、邀请系统

### 3.1 数据库迁移

```python
# backend/alembic/versions/20260226_add_referral.py

def upgrade():
    # 邀请码表
    op.create_table(
        'referral_codes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('code', sa.String(12), unique=True, nullable=False),
        sa.Column('total_referrals', sa.Integer, default=0),
        sa.Column('total_credits_earned', sa.Integer, default=0),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_referral_codes_code', 'referral_codes', ['code'])

    # 邀请记录表
    op.create_table(
        'referral_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('referrer_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('referee_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('referrer_rewarded', sa.Boolean, default=False),
        sa.Column('referee_rewarded', sa.Boolean, default=False),
        sa.Column('referrer_credits', sa.Integer, default=0),
        sa.Column('referee_credits', sa.Integer, default=0),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
```

### 3.2 后端文件清单

| 文件 | 说明 |
|-----|-----|
| `backend/app/models/referral.py` | 数据模型 |
| `backend/app/api/v1/referral.py` | API 路由 |
| `backend/app/api/v1/auth.py` | 注册时处理邀请码 |

### 3.3 前端文件清单

| 文件 | 说明 |
|-----|-----|
| `frontend/src/pages/user/Referral.tsx` | 邀请页面 |
| `frontend/src/pages/auth/Register.tsx` | 修改注册流程 |
| `frontend/src/App.tsx` | 添加路由 |

---

## 四、项目搜索

### 4.1 后端文件清单

| 文件 | 说明 |
|-----|-----|
| `backend/app/api/v1/projects.py` | 添加 search 端点 |

### 4.2 前端文件清单

| 文件 | 说明 |
|-----|-----|
| `frontend/src/components/ProjectSearch.tsx` | 搜索组件 |
| `frontend/src/pages/user/Dashboard.tsx` | 集成搜索 |

---

## 五、监控告警

### 5.1 文件清单

| 文件 | 说明 |
|-----|-----|
| `backend/app/core/metrics.py` | Prometheus 指标定义 |
| `backend/app/main.py` | 集成指标中间件 |
| `monitoring/docker-compose.yml` | 监控服务编排 |
| `monitoring/prometheus/prometheus.yml` | Prometheus 配置 |
| `monitoring/prometheus/alerts.yml` | 告警规则 |
| `monitoring/grafana/dashboards/*.json` | Grafana 仪表盘 |
| `monitoring/alertmanager/alertmanager.yml` | AlertManager 配置 |

### 5.2 部署命令

```bash
cd monitoring
docker-compose up -d
```

### 5.3 访问地址

| 服务 | 地址 |
|-----|-----|
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |
| AlertManager | http://localhost:9093 |

---

## 六、测试清单

### 6.1 新手引导
- [ ] 新用户注册后显示欢迎页
- [ ] 完成引导后领取奖励
- [ ] 跳过引导功能正常
- [ ] 老用户不显示引导

### 6.2 任务系统
- [ ] 任务失败自动返还积分
- [ ] 重启服务后任务状态正确
- [ ] 超时任务被正确标记

### 6.3 邀请系统
- [ ] 生成唯一邀请码
- [ ] 通过邀请链接注册获得奖励
- [ ] 邀请统计准确

### 6.4 项目搜索
- [ ] 关键词搜索正常
- [ ] 筛选条件生效
- [ ] 分页正常

### 6.5 监控告警
- [ ] 指标正常采集
- [ ] 仪表盘数据正确
- [ ] 告警触发正常
