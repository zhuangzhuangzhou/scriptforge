# Google Gemini 集成指南

## 📋 概述

本指南介绍如何在系统中集成和使用 Google Gemini 模型。

**完成时间**: 2026-02-09

---

## 🎯 Gemini 模型特点

### 优势
- ✅ **超长上下文**: Gemini 1.5 Pro 支持 2M tokens 上下文
- ✅ **多模态支持**: 支持文本、图像、音频、视频输入
- ✅ **高性价比**: Flash 系列模型价格极低
- ✅ **快速响应**: Flash-8B 模型响应速度极快
- ✅ **函数调用**: 支持 Function Calling
- ✅ **流式输出**: 支持流式响应

### 模型对比

| 模型 | 上下文长度 | 输入价格 | 输出价格 | 适用场景 |
|------|-----------|---------|---------|---------|
| Gemini 1.5 Pro | 2M tokens | $0.00125/1K | $0.005/1K | 复杂任务、长文档分析 |
| Gemini 1.5 Flash | 1M tokens | $0.000075/1K | $0.0003/1K | 通用任务、高频调用 |
| Gemini 1.5 Flash-8B | 1M tokens | $0.0000375/1K | $0.00015/1K | 简单任务、极高频调用 |
| Gemini 1.0 Pro | 32K tokens | $0.0005/1K | $0.0015/1K | 稳定可靠的基础模型 |

---

## 🚀 快速开始

### 1. 获取 API Key

访问 Google AI Studio 获取 API Key：
```
https://aistudio.google.com/app/apikey
```

**注意事项**:
- 需要 Google 账号
- 某些地区可能需要 VPN
- 免费配额：每分钟 60 次请求

### 2. 初始化 Gemini 配置

运行初始化脚本：
```bash
cd backend
source venv/bin/activate
python scripts/init_gemini_provider.py
```

**脚本会自动创建**:
- ✅ Google Gemini 提供商
- ✅ 4 个 Gemini 模型配置
- ✅ 对应的计费规则

**输出示例**:
```
============================================================
初始化 Google Gemini 提供商和模型配置
============================================================

✓ 创建 Gemini 提供商 (ID: xxx)
  ✓ 创建模型: Gemini 1.5 Pro
  ✓ 创建模型: Gemini 1.5 Flash
  ✓ 创建模型: Gemini 1.5 Flash-8B
  ✓ 创建模型: Gemini 1.0 Pro

总结:
  - 创建了 4 个模型
  - 跳过了 0 个已存在的模型

下一步:
  1. 访问管理界面: http://localhost:5173/admin/models
  2. 在「凭证管理」中添加 Google API Key
  3. 测试凭证是否有效
```

### 3. 添加 API 凭证

#### 方式一：通过管理界面（推荐）

1. 访问 http://localhost:5173/admin/models
2. 切换到「凭证管理」标签
3. 点击「新建凭证」
4. 填写信息：
   - **提供商**: 选择 "Google Gemini"
   - **凭证名称**: 例如 "Production Key"
   - **API Key**: 粘贴你的 Google API Key
   - **配额限制**: 可选，设置每月使用限制
5. 点击「保存」
6. 点击「测试」按钮验证凭证

#### 方式二：通过 API

```bash
curl -X POST http://localhost:8000/api/v1/admin/models/credentials \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "GEMINI_PROVIDER_ID",
    "credential_name": "Production Key",
    "api_key": "YOUR_GOOGLE_API_KEY",
    "quota_limit": 1000000
  }'
```

### 4. 测试凭证

```bash
# 通过 API 测试
curl -X POST http://localhost:8000/api/v1/admin/models/credentials/{credential_id}/test \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**成功响应**:
```json
{
  "success": true,
  "message": "Google Gemini API 凭证验证成功",
  "provider_type": "gemini",
  "provider_name": "Google Gemini",
  "credential_name": "Production Key"
}
```

---

## 💻 使用 Gemini API

### Python 示例

#### 基础使用

```python
from app.ai.adapters.gemini_adapter import GeminiAdapter

async def example():
    async with GeminiAdapter(
        api_key="YOUR_API_KEY",
        model="gemini-1.5-pro"
    ) as adapter:
        # 发送消息
        messages = [
            {"role": "user", "content": "你好，请介绍一下自己"}
        ]
        
        # 生成响应
        response = await adapter.generate_content(
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        # 提取文本
        text = adapter.extract_text_from_response(response)
        print(f"响应: {text}")
        
        # 获取使用信息
        usage = adapter.get_usage_info(response)
        print(f"Token 使用: {usage}")
```

#### 流式响应

```python
async def streaming_example():
    async with GeminiAdapter(
        api_key="YOUR_API_KEY",
        model="gemini-1.5-flash"
    ) as adapter:
        messages = [
            {"role": "user", "content": "写一首关于春天的诗"}
        ]
        
        print("流式响应:")
        async for chunk in adapter.generate_content_stream(messages):
            text = adapter.extract_text_from_response(chunk)
            if text:
                print(text, end="", flush=True)
        print()
```

#### 多轮对话

```python
async def conversation_example():
    async with GeminiAdapter(
        api_key="YOUR_API_KEY",
        model="gemini-1.5-pro"
    ) as adapter:
        messages = [
            {"role": "user", "content": "我想学习 Python"},
            {"role": "assistant", "content": "太好了！Python 是一门很棒的编程语言..."},
            {"role": "user", "content": "从哪里开始学习比较好？"}
        ]
        
        response = await adapter.generate_content(messages)
        text = adapter.extract_text_from_response(response)
        print(text)
```

#### 系统提示词

```python
async def system_prompt_example():
    async with GeminiAdapter(
        api_key="YOUR_API_KEY",
        model="gemini-1.5-pro"
    ) as adapter:
        messages = [
            {"role": "system", "content": "你是一个专业的 Python 编程助手"},
            {"role": "user", "content": "如何读取文件？"}
        ]
        
        response = await adapter.generate_content(messages)
        text = adapter.extract_text_from_response(response)
        print(text)
```

---

## 🔧 高级配置

### 温度参数

```python
# 更有创意的响应
response = await adapter.generate_content(
    messages=messages,
    temperature=0.9  # 0.0 - 1.0
)

# 更确定性的响应
response = await adapter.generate_content(
    messages=messages,
    temperature=0.1
)
```

### Top-P 和 Top-K

```python
response = await adapter.generate_content(
    messages=messages,
    temperature=0.7,
    top_p=0.95,  # Nucleus sampling
    top_k=40     # Top-K sampling
)
```

### 最大输出长度

```python
response = await adapter.generate_content(
    messages=messages,
    max_tokens=4096  # 最多生成 4096 tokens
)
```

---

## 📊 计费说明

### 价格对比（每 1K tokens）

| 模型 | 输入价格 | 输出价格 | 系统积分（输入） | 系统积分（输出） |
|------|---------|---------|----------------|----------------|
| Gemini 1.5 Pro | $0.00125 | $0.005 | 1.25 | 5.0 |
| Gemini 1.5 Flash | $0.000075 | $0.0003 | 0.075 | 0.3 |
| Gemini 1.5 Flash-8B | $0.0000375 | $0.00015 | 0.0375 | 0.15 |
| Gemini 1.0 Pro | $0.0005 | $0.0015 | 0.5 | 1.5 |

### 成本估算

**示例 1: 文档摘要（Gemini 1.5 Flash）**
- 输入: 10,000 tokens (长文档)
- 输出: 500 tokens (摘要)
- 成本: $0.00075 + $0.00015 = $0.0009
- 系统积分: 0.75 + 0.15 = 0.9

**示例 2: 对话助手（Gemini 1.5 Flash-8B）**
- 输入: 1,000 tokens (对话历史)
- 输出: 200 tokens (回复)
- 成本: $0.0000375 + $0.00003 = $0.0000675
- 系统积分: 0.0375 + 0.03 = 0.0675

**示例 3: 复杂分析（Gemini 1.5 Pro）**
- 输入: 100,000 tokens (超长文档)
- 输出: 2,000 tokens (详细分析)
- 成本: $0.125 + $0.01 = $0.135
- 系统积分: 125 + 10 = 135

---

## 🎯 最佳实践

### 1. 选择合适的模型

**Gemini 1.5 Pro**:
- ✅ 需要理解超长文档（>100K tokens）
- ✅ 复杂的推理任务
- ✅ 多模态输入（图像、视频）
- ❌ 高频率简单任务（成本较高）

**Gemini 1.5 Flash**:
- ✅ 通用对话和文本生成
- ✅ 中等长度文档处理
- ✅ 需要平衡性能和成本
- ✅ 大多数生产场景

**Gemini 1.5 Flash-8B**:
- ✅ 简单的分类任务
- ✅ 短文本生成
- ✅ 极高频率调用
- ✅ 成本敏感的场景

### 2. 优化 Token 使用

```python
# ❌ 不好的做法：每次都发送完整历史
messages = conversation_history  # 可能有几千条消息

# ✅ 好的做法：只保留最近的对话
messages = conversation_history[-10:]  # 只保留最近 10 条

# ✅ 更好的做法：智能截断
def truncate_messages(messages, max_tokens=4000):
    # 保留系统提示词和最近的消息
    system_msgs = [m for m in messages if m["role"] == "system"]
    recent_msgs = [m for m in messages if m["role"] != "system"][-5:]
    return system_msgs + recent_msgs
```

### 3. 错误处理

```python
from httpx import HTTPStatusError, TimeoutException

async def safe_generate(adapter, messages):
    try:
        response = await adapter.generate_content(messages)
        return adapter.extract_text_from_response(response)
    except HTTPStatusError as e:
        if e.response.status_code == 429:
            print("请求频率超限，请稍后重试")
        elif e.response.status_code == 400:
            print("请求参数错误")
        else:
            print(f"API 错误: {e}")
        return None
    except TimeoutException:
        print("请求超时")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        return None
```

### 4. 使用流式响应

```python
# ✅ 对于长文本生成，使用流式响应提升用户体验
async for chunk in adapter.generate_content_stream(messages):
    text = adapter.extract_text_from_response(chunk)
    if text:
        # 实时显示给用户
        yield text
```

---

## 🔍 故障排查

### 问题 1: API Key 无效

**错误信息**:
```
API Key 无效或权限不足
```

**解决方案**:
1. 检查 API Key 是否正确复制
2. 确认 API Key 是否已启用
3. 检查是否有地区限制
4. 尝试重新生成 API Key

### 问题 2: 请求频率超限

**错误信息**:
```
API 请求频率超限
```

**解决方案**:
1. 实现请求限流
2. 使用指数退避重试
3. 考虑升级到付费计划
4. 分散请求到多个 API Key

### 问题 3: 上下文长度超限

**错误信息**:
```
Input too long
```

**解决方案**:
1. 截断输入文本
2. 使用摘要技术压缩上下文
3. 切换到支持更长上下文的模型（Pro）

### 问题 4: 网络连接问题

**错误信息**:
```
请求超时，请检查网络连接
```

**解决方案**:
1. 检查网络连接
2. 确认是否需要代理
3. 增加超时时间
4. 使用重试机制

---

## 📚 参考资源

### 官方文档
- **Gemini API 文档**: https://ai.google.dev/docs
- **定价信息**: https://ai.google.dev/pricing
- **API 参考**: https://ai.google.dev/api/rest
- **快速开始**: https://ai.google.dev/tutorials/python_quickstart

### 社区资源
- **GitHub 示例**: https://github.com/google/generative-ai-python
- **Discord 社区**: https://discord.gg/google-ai
- **Stack Overflow**: 标签 `google-gemini`

---

## 🎓 总结

### 关键要点
1. ✅ Gemini 提供超长上下文和多模态支持
2. ✅ Flash 系列模型性价比极高
3. ✅ 支持流式响应和函数调用
4. ✅ 简单易用的 API 接口

### 下一步
1. 运行初始化脚本创建配置
2. 添加 API 凭证并测试
3. 在项目中集成 Gemini 适配器
4. 根据场景选择合适的模型

---

**文档版本**: 1.0  
**创建日期**: 2026-02-09  
**作者**: Kiro AI Assistant
