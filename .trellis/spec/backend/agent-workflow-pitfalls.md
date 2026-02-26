# Agent 工作流常见陷阱 (Agent Workflow Pitfalls)

## 概述

本文档记录 Agent 工作流系统中发现的常见陷阱和最佳实践，帮助避免重复踩坑。

---

## 1. 循环工作流初始化陷阱

### 问题描述

**症状**：
- 连续拆解（全部拆解）时，第二个批次及后续批次失败
- 错误信息：`EMPTY_RESULT - 拆解结果为空`
- 单批次拆解正常，连续拆解失败

**根本原因**：

循环工作流初始化时预设了空数组和空对象：

```python
# ❌ 错误的初始化
results = {
    "context": context,
    "_iteration": 0,
    "plot_points": [],      # 空数组污染
    "qa_result": {}         # 空对象污染
}
```

**问题机制**：

1. 循环开始时，`plot_points` 被初始化为空数组 `[]`
2. 第一轮 `breakdown` 步骤执行，应该返回 `{"plot_points": [数组], "breakdown": [数组]}`
3. 如果步骤返回值因某种原因没有正确更新 `results`（例如异常、返回 None 等）
4. `qa` 步骤通过 `${plot_points}` 引用时，获取到的是初始化的**空数组**
5. `format_plot_points_to_text([])` 返回空字符串
6. LLM 收到空内容，质检失败
7. 任务标记为 `EMPTY_RESULT` 失败

**为什么"连续拆解"时才出现**：
- 第一个批次通常能成功（新启动的任务，环境干净）
- 第二个批次开始时，可能因为某些边界条件导致步骤返回值异常
- 空数组污染问题被触发

### 解决方案

**不要预初始化步骤输出变量**：

```python
# ✅ 正确的初始化
results = {
    "context": context,
    "_iteration": 0
    # 不预初始化 plot_points 和 qa_result
}
```

**好处**：
- 如果步骤成功，会正确设置变量
- 如果步骤失败，变量不存在会**明确报错**（KeyError）
- 而不是使用错误的空值，导致难以追踪的问题

### 最佳实践

1. **循环工作流初始化**：
   - 只初始化 `context` 和 `_iteration`
   - 不要预设步骤输出变量

2. **步骤输出验证**：
   - 在关键步骤后验证输出是否存在
   - 使用 `results.get("key")` 而不是 `results["key"]`

3. **错误处理**：
   - 让错误明确暴露，而不是被空值掩盖
   - 使用调试日志记录关键变量的状态

### 相关代码

- 文件：`backend/app/ai/simple_executor.py`
- 方法：`SimpleAgentExecutor._execute_loop_workflow()`
- 行号：~1300

### 修复提交

- Commit: `1478cd6` - fix: 修复循环工作流中空数组污染问题
- Date: 2026-02-26

---

## 2. 退出条件评估陷阱

### 问题描述

**症状**：
- 循环工作流不会在满足退出条件时停止
- 即使 QA 通过（status=PASS, score>=70），仍然继续执行

**可能原因**：

1. **字段名不匹配**：
   ```python
   # 退出条件
   "exit_condition": "qa_result.status == 'PASS' and qa_result.score >= 70"

   # QA 结果数据结构
   {
       "qa_status": "PASS",  # 主字段
   "qa_score": 75,       # 主字段
       "status": "PASS",     # 别名
       "score": 75           # 别名
   }
   ```

2. **条件评估失败**：
   - `_evaluate_condition()` 抛出异常时返回 `False`
   - 导致条件永远不满足

3. **数据类型问题**：
   - `qa_result` 可能是列表而不是字典
   - 需要兼容处理（第 1459-1463 行）

### 解决方案

**根本原因**：

1. **字段名不匹配**：
   - 退出条件使用 `qa_result.status` 和 `qa_result.score`
   - 但扁平化后的字段是 `qa_result.qa_status` 和 `qa_result.qa_score`
   - 变量替换失败，`_safe_eval()` 抛出异常
   - 异常被捕获后返回 `False`，循环永远不会停止

2. **为什么之前没发现**：
   - QA 结果中有别名 `status` 和 `score`
   - 但扁平化时只有 `qa_status` 和 `qa_score`（带前缀）
   - `_substitute_variables()` 无法匹配 `qa_result.status`

**修复方案**：

```python
# ❌ 错误 - 字段名不匹配
"exit_condition": "qa_result.status == 'PASS' and qa_result.score >= 70"

# ✅ 正确 - 使用主字段名
"exit_condition": "qa_result.qa_status == 'PASS' and qa_result.qa_score >= 70"
```

**添加调试日志**：
```python
logger.info(f"[退出条件] qa_result.keys: {list(qa_result.keys())}")
logger.info(f"[退出条件] status={qa_result.get('status')}")
logger.info(f"[退出条件] 评估结果: {condition_met}")
```

**兼容列表输出**：
```python
if output_key in ("qa_result", "qa") and isinstance(result, list):
    if len(result) == 1 and isinstance(result[0], dict):
        result = result[0]
    elif len(result) == 0:
        result = {}
```

### 修复提交

- Commit: `0b9b68c` - fix: 修复退出条件字段名错误导致循环不停止
- Date: 2026-02-26

---

## 3. 数据传递链路陷阱

### 问题描述

**症状**：
- LLM 成功返回数据，但后续步骤收到空值
- 日志显示"解析成功"，但实际使用时数据丢失

**常见原因**：

1. **解析失败但未报错**：
   - `parse_text_plot_points()` 返回空数组
   - 但没有抛出异常，导致静默失败

2. **数据格式转换丢失**：
   - `_resolve_inputs()` 返回原始数据
   - `execute_skill()` 预处理时转换失败
   - 但没有明确的错误提示

3. **步骤返回值未更新 results**：
   - `_execute_step()` 返回 `None`
   - `results.update()` 不执行
   - 后续步骤使用旧值或空值

### 最佳实践

1. **添加关键点日志**：
   ```python
   logger.info(f"[解析] 响应长度: {len(response)}")
   logger.info(f"[格式化] 开始格式化 {len(plot_points)} 个剧情点")
   logger.info(f"[步骤输出] {step_id}: {type(result)}, len={len(result)}")
   ```

2. **验证数据完整性**：
   ```python
   if not plot_points or len(plot_points) == 0:
       raise AITaskException(code="EMPTY_RESULT", message="解析结果为空")
   ```

3. **明确错误传播**：
   - 不要静默失败
   - 让错误在第一时间暴露

---

## 4. 连续任务状态污染

### 问题描述

**症状**：
- 第一个任务成功，第二个任务失败
- 错误信息不明确，难以定位

**可能原因**：

1. **数据库会话污染**：
   - 多个任务共享同一个数据库会话
   - 前一个任务的数据影响后续任务

2. **模型适配器状态**：
   - 模型适配器可能保留了前一个任务的状态
   - 导致后续任务行为异常

3. **配置继承问题**：
   - 新任务继承了前一个任务的完整配置
   - 包含了不应该继承的上下文数据

### 解决方案

1. **每个任务独立创建执行器**：
   ```python
   agent_executor = SimpleAgentExecutor(db, model_adapter, log_publisher)
   ```

2. **配置清理**：
   ```python
   # 只继承必要的配置项
   new_config = {
       "auto_continue": task_config.get("auto_continue"),
       "model_config_id": task_config.get("model_config_id"),
       # 不继承 chapters_text 等批次特定数据
   }
   ```

3. **数据库会话健康检查**：
   ```python
   def ensure_db_connection(db: Session) -> Session:
       try:
           db.execute(text("SELECT 1"))
           return db
       except Exception:
           db.close()
           return SyncSessionLocal()
   ```

---

## 总结

### 核心原则

1. **明确失败优于静默失败**
   - 让错误在第一时间暴露
   - 不要用空值掩盖问题

2. **不要预设步骤输出**
   - 只初始化必要的上下文
   - 让步骤自己设置输出变量

3. **添加关键点日志**
   - 数据解析、格式转换、步骤输出
   - 帮助快速定位问题

4. **验证数据完整性**
   - 在关键步骤后验证数据
   - 不要假设数据一定存在

### 调试技巧

1. **完整代码分析优于增量调试**
   - 先理解完整的数据流
   - 再定位具体问题

2. **追踪数据传递链路**
   - LLM 响应 → 解析 → 格式转换 → 步骤输出 → 下一步输入
   - 在每个环节添加日志

3. **模拟数据流**
   - 用简单的 Python 脚本模拟问题场景
   - 快速验证假设

---

## 相关文档

- [AI Skills 系统](./ai-skills.md)
- [工作流规范](./workflow.md)
- [错误处理规范](./error-handling.md)
