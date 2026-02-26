# LLM Token 统计追踪

## 概述

所有 LLM adapter 必须在流式和非流式响应中正确提取并记录 token 统计，以确保计费准确性。

## 实现要求

### 1. Token 字段

每个 LLM 调用必须记录：
- `prompt_tokens` (输入 token 数量)
- `response_tokens` (输出 token 数量)

### 2. Adapter 实现

#### Anthropic Adapter

**非流式** (`generate`):
- 从 `message_start` 事件的 `usage.input_tokens` 获取输入 tokens
- 从 `message_delta` 事件的 `usage.output_tokens` 获取输出 tokens

**流式** (`stream_generate`):
- 在 SSE 流中监听 `message_start` 和 `message_delta` 事件
- 提取 `usage` 字段中的 token 统计

```python
# 示例代码
if data.get("type") == "message_start":
    usage = data.get("message", {}).get("usage", {})
    prompt_tokens = usage.get("input_tokens")

elif data.get("type") == "message_delta":
    usage = data.get("usage", {})
    response_tokens = usage.get("output_tokens")
```

#### OpenAI Adapter

**非流式** (`generate`):
- 从 `response.usage` 获取 token 统计

**流式** (`stream_generate`):
- 必须在创建流时添加 `stream_options={"include_usage": True}`
- 在最后一个 chunk 中提取 `usage` 字段

```python
stream = self.client.chat.completions.create(
    model=self.model_name,
    messages=messages,
    stream=True,
    stream_options={"include_usage": True}  # 关键！
)

for chunk in stream:
    if hasattr(chunk, 'usage') and chunk.usage:
        prompt_tokens = chunk.usage.prompt_tokens
        response_tokens = chunk.usage.completion_tokens
```

#### Gemini Adapter

**非流式** (`generate`):
- 从 `response.usageMetadata` 获取 token 统计

**流式** (`stream_generate`):
- 每个 chunk 都可能包含 `usageMetadata`
- 保存最后一个有效的 usage 数据

```python
for chunk in self.generate_content_stream(...):
    usage = chunk.get("usageMetadata")
    if usage:
        prompt_tokens = usage.get("promptTokenCount")
        response_tokens = usage.get("candidatesTokenCount")
```

### 3. 日志记录

所有 adapter 必须调用 `_log_call_sync` 时传入 token 数据：

```python
self._log_call_sync(
    prompt=prompt,
    response=response_content,
    prompt_tokens=prompt_tokens,      # 必须
    response_tokens=response_tokens,  # 必须
    temperature=temperature,
    max_tokens=max_tokens,
    latency_ms=latency_ms,
    status="success",
    metadata={...}
)
```

## 常见问题

### Q: 为什么 token 统计很重要？

A: Token 统计直接影响计费准确性。如果缺失，系统会使用文本长度估算，可能导致：
- 计费不准确（过高或过低）
- 无法追踪实际 API 消耗
- 成本分析失真

### Q: 如果 API 不返回 token 统计怎么办？

A:
1. 优先使用 API 提供的 token 统计
2. 如果 API 不支持，在 metadata 中标记 `estimated: true`
3. 使用 tiktoken 等库进行准确估算（不要用简单的字符长度）

### Q: 流式响应中如何获取 token 统计？

A: 不同提供商的实现方式：
- **Anthropic**: 在 SSE 事件流中分段返回
- **OpenAI**: 需要 `stream_options={"include_usage": True}`，在最后返回
- **Gemini**: 在每个 chunk 的 metadata 中包含

## 历史问题

### 2026-02-26: Token 统计缺失导致计费错误

**问题**: 流式响应中未提取 token 统计，导致 `prompt_tokens` 和 `response_tokens` 为 `None`

**影响**:
- 计费系统使用文本长度估算（不准确）
- 配合高倍率的模型定价，导致计费异常（如 1069 tokens 扣 8000 积分）

**修复**:
- 在所有 adapter 的 `stream_generate` 方法中添加 token 提取逻辑
- 确保日志记录时传入 token 数据

**相关文件**:
- `backend/app/ai/adapters/anthropic_adapter.py`
- `backend/app/ai/adapters/openai_adapter.py`
- `backend/app/ai/adapters/gemini_adapter.py`

**教训**:
1. 流式响应的 token 统计容易被忽略
2. 必须在开发时验证 token 字段是否正确记录
3. 计费逻辑应该在 token 缺失时报警，而不是静默降级到估算
