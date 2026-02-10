# Gemini 快速开始指南

## ✅ 已完成的工作

我已经为你的系统添加了完整的 Google Gemini 支持！

### 🎉 新增功能

1. **Gemini 凭证测试** ✅
   - 支持真实的 API 验证
   - 详细的错误提示

2. **Gemini 提供商配置** ✅
   - 已在数据库中创建
   - ID: `ad4da85c-d888-4870-9b38-64f7cfd4f7ab`

3. **4 个 Gemini 模型** ✅
   - Gemini 1.5 Pro (2M tokens 上下文)
   - Gemini 1.5 Flash (1M tokens 上下文)
   - Gemini 1.5 Flash-8B (最快速)
   - Gemini 1.0 Pro (稳定版)

4. **计费规则配置** ✅
   - 所有模型都已配置价格
   - 自动计算积分消耗

5. **Python 适配器** ✅
   - 完整的 API 封装
   - 支持流式响应
   - 支持多轮对话

---

## 🚀 立即使用

### 第一步：获取 API Key

访问 Google AI Studio：
```
https://aistudio.google.com/app/apikey
```

点击「Create API Key」获取你的密钥。

### 第二步：添加凭证

1. 访问管理界面：http://localhost:5173/admin/models
2. 切换到「凭证管理」标签
3. 点击「新建凭证」
4. 填写信息：
   - **提供商**: 选择 "Google Gemini"
   - **凭证名称**: 例如 "My Gemini Key"
   - **API Key**: 粘贴你的 Google API Key
5. 点击「保存」
6. 点击「测试」验证凭证

### 第三步：开始使用

#### Python 代码示例

```python
from app.ai.adapters.gemini_adapter import GeminiAdapter

async def use_gemini():
    async with GeminiAdapter(
        api_key="YOUR_API_KEY",
        model="gemini-1.5-flash"  # 推荐使用 Flash，性价比高
    ) as adapter:
        messages = [
            {"role": "user", "content": "你好，请介绍一下自己"}
        ]
        
        response = await adapter.generate_content(messages)
        text = adapter.extract_text_from_response(response)
        print(text)
```

---

## 📊 模型选择建议

### Gemini 1.5 Flash（推荐）
- **价格**: 输入 $0.000075/1K, 输出 $0.0003/1K
- **上下文**: 1M tokens
- **适用**: 大多数场景，性价比最高
- **示例**: 对话助手、文档分析、代码生成

### Gemini 1.5 Flash-8B（最便宜）
- **价格**: 输入 $0.0000375/1K, 输出 $0.00015/1K
- **上下文**: 1M tokens
- **适用**: 简单任务、高频调用
- **示例**: 分类、简单问答、数据提取

### Gemini 1.5 Pro（最强大）
- **价格**: 输入 $0.00125/1K, 输出 $0.005/1K
- **上下文**: 2M tokens
- **适用**: 复杂任务、超长文档
- **示例**: 长文档分析、复杂推理、多模态任务

### Gemini 1.0 Pro（稳定版）
- **价格**: 输入 $0.0005/1K, 输出 $0.0015/1K
- **上下文**: 32K tokens
- **适用**: 需要稳定性的场景
- **示例**: 生产环境、关键业务

---

## 💡 使用技巧

### 1. 成本优化

```python
# ❌ 不好：每次都用 Pro
adapter = GeminiAdapter(model="gemini-1.5-pro")

# ✅ 好：根据任务选择
# 简单任务用 Flash-8B
adapter = GeminiAdapter(model="gemini-1.5-flash-8b")

# 复杂任务用 Flash
adapter = GeminiAdapter(model="gemini-1.5-flash")

# 超长文档用 Pro
adapter = GeminiAdapter(model="gemini-1.5-pro")
```

### 2. 流式响应

```python
# 对于长文本生成，使用流式响应
async for chunk in adapter.generate_content_stream(messages):
    text = adapter.extract_text_from_response(chunk)
    if text:
        print(text, end="", flush=True)
```

### 3. 控制输出长度

```python
# 限制输出长度节省成本
response = await adapter.generate_content(
    messages=messages,
    max_tokens=500  # 只生成 500 tokens
)
```

---

## 📁 相关文件

### 后端
- `backend/app/utils/credential_tester.py` - 凭证测试（已添加 Gemini 支持）
- `backend/app/ai/adapters/gemini_adapter.py` - Gemini API 适配器
- `backend/scripts/init_gemini_provider.py` - 初始化脚本

### 前端
- `frontend/src/pages/admin/ModelManagement/ProviderManagement.tsx` - 提供商管理（已添加 Gemini 选项）

### 文档
- `docs/gemini-integration-guide.md` - 完整集成指南
- `GEMINI_QUICK_START.md` - 本文档

---

## 🔍 验证安装

### 检查提供商
```bash
curl http://localhost:8000/api/v1/admin/models/providers \
  -H "Authorization: Bearer YOUR_TOKEN" | grep -i gemini
```

### 检查模型
```bash
curl http://localhost:8000/api/v1/admin/models/models \
  -H "Authorization: Bearer YOUR_TOKEN" | grep -i gemini
```

---

## 🆘 常见问题

### Q: API Key 在哪里获取？
A: 访问 https://aistudio.google.com/app/apikey

### Q: 需要付费吗？
A: 有免费配额，每分钟 60 次请求。超出需要付费。

### Q: 支持中文吗？
A: 完全支持中文，效果很好。

### Q: 如何选择模型？
A: 
- 日常使用：Gemini 1.5 Flash
- 成本敏感：Gemini 1.5 Flash-8B
- 复杂任务：Gemini 1.5 Pro

### Q: 凭证测试失败？
A: 
1. 检查 API Key 是否正确
2. 确认网络连接（可能需要 VPN）
3. 检查是否超出配额

---

## 📚 更多信息

详细文档请查看：`docs/gemini-integration-guide.md`

包含：
- 完整的 API 使用示例
- 高级配置选项
- 最佳实践
- 故障排查
- 成本估算

---

**创建时间**: 2026-02-09  
**状态**: ✅ 已完成并测试
