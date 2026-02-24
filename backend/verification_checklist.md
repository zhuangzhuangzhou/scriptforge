# WebSocket 批次切换推送 - 完整验证清单

## 验证目标
确保批次完成时能通过 WebSocket 实时推送下一批次信息到前端

## 验证步骤

### 1. 后端代码验证
- [ ] RedisLogPublisher.publish_batch_switch 方法存在且正确
- [ ] _trigger_next_task_sync 调用推送方法
- [ ] 消息格式正确
- [ ] Redis 频道命名正确
- [ ] WebSocket 端点能转发消息

### 2. 消息流验证
- [ ] 批次完成 → 触发 _trigger_next_task_sync
- [ ] 创建新任务成功
- [ ] 推送消息到 Redis
- [ ] WebSocket 订阅正确的频道
- [ ] 前端能收到消息

### 3. 边界情况验证
- [ ] Redis 不可用时的降级处理
- [ ] WebSocket 断开时的处理
- [ ] 推送失败不影响主流程
- [ ] 最后一个批次完成时的处理

### 4. 集成验证
- [ ] 与现有轮询机制兼容
- [ ] 不影响单批次拆解
- [ ] 只在 auto_continue 模式下生效

