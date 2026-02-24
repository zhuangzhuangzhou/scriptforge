# 完整验证清单

## 验证目标
确保 WebSocket 批次切换推送功能的完整性和正确性

## 验证步骤

### 阶段 1: 后端代码验证
1. [ ] RedisLogPublisher.publish_batch_switch 方法
2. [ ] _trigger_next_task_sync 调用时机
3. [ ] 消息格式和频道命名
4. [ ] WebSocket 端点转发逻辑

### 阶段 2: 前端代码验证
1. [ ] useConsoleLogger 接口定义
2. [ ] batch_switch 消息处理
3. [ ] WebSocket 关闭时机
4. [ ] Workspace 组件集成

### 阶段 3: 数据流验证
1. [ ] 完整数据流路径
2. [ ] 消息发送顺序
3. [ ] 错误处理和降级

### 阶段 4: 边界情况验证
1. [ ] 最后一个批次完成
2. [ ] Redis 不可用
3. [ ] WebSocket 断开
4. [ ] 推送失败处理

