# 模型管理系统集成指南

## 概述

本文档说明如何将新的模型管理系统集成到现有的代码库中。

## 集成步骤

### 步骤1：数据库迁移

如果你的项目使用 Alembic 进行数据库迁移：

```bash
cd backend

# 创建迁移文件（如果还没有）
alembic revision --autogenerate -m "add model management tables"

# 运行迁移
alembic upgrade head

# 初始化数据
python3 scripts/init_model_data.py
```

如果你的项目不使用 Alembic，需要手动创建表。参考 `backend/app/models/` 目录下的模型定义。

### 步骤2：设置加密密钥

**重要：** 生产环境必须设置 `ENCRYPTION_KEY` 环境变量。

```bash
# 生成加密密钥
python3 -c "import os, base64; print('ENCRYPTION_KEY=' + base64.b64encode(os.urandom(32)).decode())"

# 将输出的密钥添加到环境变量
export ENCRYPTION_KEY="<生成的密钥>"

# 或者添加到 .env 文件
echo 'ENCRYPTION_KEY="<生成的密钥>"' >> .env
```

### 步骤3：注册 API 路由

在你的主路由文件中注册模型管理路由。

**示例：** 如果你有 `backend/app/api/v1/router.py`：

```python
from fastapi import APIRouter
from app.api.v1.admin import models_router

router = APIRouter()

# 注册模型管理路由
router.include_router(
    models_router.router,
    prefix="/api/v1",
    tags=["模型管理"]
)

# 其他路由...
```

### 步骤4：改造适配器系统

#### 4.1 改造 get_adapter 函数

找到你的适配器工厂函数（通常在 `backend/app/ai/adapters/__init__.py`），添加数据库配置支持。

**原有代码：**
```python
def get_adapter(provider: str = "openai"):
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIAdapter(api_key=api_key)
    # ...
```

**改造后：**
```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.adapters.model_config_service import ModelConfigService

async def get_adapter(
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Optional[AsyncSession] = None
):
    """获取适配器（支持数据库配置）"""

    # 1. 尝试从数据库获取配置
    if db:
        config_service = ModelConfigService(db)
        config = await config_service.get_model_config(
            provider_key=provider,
            model_id=model_id,
            user_id=user_id
        )

        if config:
            # 使用数据库配置创建适配器
            if config["provider_type"] == "openai_compatible":
                return OpenAIAdapter(
                    api_key=config["api_key"],
                    model=config["model_name"],
                    base_url=config.get("api_endpoint")
                )
            elif config["provider_type"] == "anthropic":
                return AnthropicAdapter(
                    api_key=config["api_key"],
                    model=config["model_name"]
                )

    # 2. 降级到环境变量配置
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIAdapter(api_key=api_key)
    # ...
```

参考文件：`backend/app/ai/adapters/adapter_factory_example.py`

#### 4.2 更新任务代码

在所有使用 `get_adapter` 的地方，传递 `db` 参数。

**示例：** 剧情拆解任务

**原有代码：**
```python
def breakdown_task(plot_id: str):
    adapter = get_adapter(provider="openai")
    response = adapter.chat(messages=[...])
```

**改造后：**
```python
async def breakdown_task(plot_id: str, db: AsyncSession):
    adapter = await get_adapter(
        provider="openai",
        db=db
    )
    response = await adapter.chat(messages=[...])
```

需要更新的文件（示例）：
- `backend/app/tasks/breakdown_tasks.py`
- `backend/app/tasks/script_tasks.py`
- `backend/app/tasks/pipeline_tasks.py`
- `backend/app/ai/skills/template_skill_executor.py`

### 步骤5：改造积分计算

#### 5.1 添加新的计费方法

在你的 `CreditsService` 类中添加新方法。

**添加到 `backend/app/core/credits.py`：**

```python
from typing import Optional, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select, and_
from app.models.ai_model_pricing import AIModelPricing

class CreditsService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def get_pricing_rule(
        self,
        model_id: Optional[str] = None
    ) -> Tuple[Decimal, Decimal]:
        """从数据库获取计费规则"""
        if not self.db or not model_id:
            return (Decimal('1.0'), Decimal('1.0'))

        try:
            now = datetime.utcnow()
            result = await self.db.execute(
                select(AIModelPricing)
                .where(
                    and_(
                        AIModelPricing.model_id == model_id,
                        AIModelPricing.is_active == True,
                        AIModelPricing.effective_from <= now,
                        (AIModelPricing.effective_until == None) |
                        (AIModelPricing.effective_until > now)
                    )
                )
                .order_by(AIModelPricing.effective_from.desc())
            )

            pricing = result.scalars().first()
            if pricing:
                return (
                    pricing.input_credits_per_1k_tokens,
                    pricing.output_credits_per_1k_tokens
                )
        except Exception as e:
            print(f"获取计费规则失败: {e}")

        return (Decimal('1.0'), Decimal('1.0'))

    async def calculate_model_credits(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: Optional[str] = None
    ) -> int:
        """根据模型计费规则计算积分"""
        input_price, output_price = await self.get_pricing_rule(model_id)

        input_credits = (Decimal(input_tokens) / Decimal('1000')) * input_price
        output_credits = (Decimal(output_tokens) / Decimal('1000')) * output_price

        total_credits = int((input_credits + output_credits).to_integral_value())
        return total_credits
```

参考文件：`backend/app/core/credits_service_example.py`

#### 5.2 更新积分扣除逻辑

**原有代码：**
```python
total_tokens = response.usage.total_tokens
credits = calculate_credits(total_tokens)
await deduct_credits(user_id, credits)
```

**改造后：**
```python
input_tokens = response.usage.prompt_tokens
output_tokens = response.usage.completion_tokens

credits_service = CreditsService(db=db)
credits = await credits_service.calculate_model_credits(
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    model_id=model_id
)
await deduct_credits(user_id, credits)
```

### 步骤6：前端路由注册

在前端路由文件中添加模型管理页面路由。

**示例：** `frontend/src/App.tsx`

```typescript
import ModelManagement from './pages/admin/ModelManagement';

// 在路由配置中添加
<Route path="/admin/models" element={<ModelManagement />} />
```

### 步骤7：添加导航入口

在管理员仪表盘添加"模型管理"入口。

**示例：** `frontend/src/pages/admin/Dashboard.tsx`

```typescript
<GlassCard
  title="模型管理"
  description="管理 AI 模型提供商、配置和计费规则"
  onClick={() => navigate('/admin/models')}
/>
```

## 向后兼容性

新系统完全向后兼容：

1. **环境变量降级**：如果数据库配置不可用，自动降级到环境变量配置
2. **传统计费方法**：保留原有的 `calculate_credits` 方法
3. **可选参数**：所有新参数都是可选的，不影响现有代码

## 测试

### 测试数据库配置

```bash
cd backend
python3 scripts/test_model_management.py
```

### 测试 API 端点

```bash
# 获取提供商列表
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/admin/models/providers

# 获取模型列表
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/admin/models/models
```

### 测试前端页面

1. 启动前端服务
2. 以管理员身份登录
3. 访问 `http://localhost:3000/admin/models`
4. 测试各个功能

## 常见问题

### Q1: 如何在不影响现有功能的情况下逐步迁移？

**A:** 采用渐进式迁移策略：

1. 先部署数据库表和 API（不影响现有功能）
2. 在管理界面配置模型和凭证
3. 逐个任务/功能迁移到新系统
4. 保留环境变量作为降级方案

### Q2: 如何处理现有的 API Key？

**A:** 两种方式：

1. **手动迁移**：在管理界面重新添加 API Key
2. **脚本迁移**：编写脚本从环境变量导入到数据库

### Q3: 数据库配置失败会怎样？

**A:** 系统会自动降级到环境变量配置，不影响服务可用性。

### Q4: 如何回滚？

**A:** 如果需要回滚：

1. 不传递 `db` 参数给 `get_adapter`
2. 系统会自动使用环境变量配置
3. 数据库表可以保留，不影响现有功能

## 下一步

完成集成后，建议：

1. 阅读性能优化文档：`docs/model-management-performance.md`
2. 阅读安全审计报告：`docs/model-management-security.md`
3. 根据实际情况调整配置和计费规则
4. 监控系统运行情况

## 获取帮助

如果遇到问题：

1. 查看完整文档：`docs/model-management-completion-report.md`
2. 查看快速开始指南：`docs/model-management-quickstart.md`
3. 查看示例代码：`backend/app/ai/adapters/*_example.py`
