# 订阅管理服务实现

## 目标
实现用户等级的订阅管理，支持等级升级、续费以及过期自动降级。

## 需求

### 1. 订阅核心逻辑
文件: `backend/app/core/subscription.py`
- `create_subscription(user_id, tier, months)`：创建或更新订阅。
- `check_subscription_status(user_id)`：检查用户当前订阅是否有效。
- `cancel_subscription(user_id)`：取消订阅（到期后不再续费）。
- `sync_user_tier(user_id)`：根据订阅状态同步 `users` 表中的 `tier` 字段。

### 2. API 端点
文件: `backend/app/api/v1/subscription.py`
- `GET /subscription/me`：获取当前用户的订阅详情。
- `POST /subscription/upgrade`：模拟购买订阅。
- `GET /subscription/history`：获取订阅历史记录。

### 3. 定时任务（可选/基础版）
- 在用户登录或获取配额时，自动触发 `sync_user_tier` 检查。

## 验收标准
- [ ] 能够成功创建订阅记录并更新用户等级。
- [ ] 订阅记录准确反映开始和结束时间。
- [ ] 订阅过期后，用户等级能够回退到 `free`。
- [ ] API 能够返回正确的订阅状态。
