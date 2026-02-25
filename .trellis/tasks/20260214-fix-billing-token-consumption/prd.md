# 修复账单 Token 消费问题

## Goal
修复账单系统中 Token 消费记录和显示的三个问题。

## Requirements

### 问题 1: 剧集拆解后账单不扣除 Token 消费
- **现状**: `breakdown_tasks.py` 任务完成后没有调用 `consume_token_credits` 方法
- **原因**: 第 138-139 行注释表明 Token 计费待实现
- **修复**: 任务完成后调用 `credits_service.consume_token_credits()` 扣除实际 Token 费用

### 问题 2: 积分与账单弹窗中本月消耗数字为 0
- **现状**: 后端 `get_credits_info` 已计算 `monthly_consumed`，但 API 响应模型缺少该字段
- **原因**: `CreditsInfoResponse` 模型（`billing.py` 第 40-48 行）未包含 `monthly_consumed` 字段
- **修复**: 在响应模型中添加 `monthly_consumed` 字段

### 问题 3: 查看更多按钮功能未实现
- **现状**: `BillingModal.tsx` 中按钮没有 `onClick` 事件
- **修复**:
  - 实现分页加载逻辑
  - 如果没有更多数据，隐藏按钮或显示"没有更多了"

## Acceptance Criteria
- [ ] 剧集拆解完成后，账单记录中正确扣除 Token 消费积分
- [ ] 积分与账单弹窗中正确显示本月消耗数字
- [ ] 查看更多按钮点击后加载更多账单记录
- [ ] 没有更多数据时，按钮显示"没有更多了"或隐藏

## Technical Notes

### 文件修改清单
| 文件 | 修改内容 |
|------|---------|
| `backend/app/tasks/breakdown_tasks.py` | 调用 `consume_token_credits` |
| `backend/app/api/v1/billing.py` | `CreditsInfoResponse` 添加 `monthly_consumed` |
| `frontend/src/components/modals/BillingModal.tsx` | 实现分页加载 |

### 相关代码位置
- Token 扣费方法: `backend/app/core/credits.py:255-348`
- 本月消耗计算: `backend/app/core/credits.py:547-556`
- 前端弹窗: `frontend/src/components/modals/BillingModal.tsx`
