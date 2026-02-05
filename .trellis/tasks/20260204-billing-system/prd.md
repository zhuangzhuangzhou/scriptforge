# 计费系统实现

## Goal
实现完整的计费系统，支持积分消耗、充值、订阅管理和账单记录。

## Requirements

### 1. 数据库模型

#### 账单记录表 (billing_records)
- id, user_id, type, amount, credits, description, created_at

#### 订阅记录表 (subscriptions)
- id, user_id, tier, status, started_at, expires_at

### 2. 积分服务
文件: `backend/app/core/credits.py`
- consume_credits() - 消耗积分
- add_credits() - 充值积分
- get_credits_balance() - 查询余额

### 3. Token 计费
- AI 调用时计算 token 消耗
- 按 token 数量扣减积分

### 4. API 端点
文件: `backend/app/api/v1/billing.py`
- GET /billing/balance - 查询余额
- GET /billing/records - 账单记录
- POST /billing/recharge - 充值积分

## Acceptance Criteria
- [ ] 数据库模型创建
- [ ] 积分服务实现
- [ ] AI调用集成积分消耗
- [ ] API端点完善
