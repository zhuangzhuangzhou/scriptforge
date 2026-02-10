# AI 模型管理系统

一个完整的 AI 模型管理系统，支持动态配置和管理不同厂商的 AI 模型、API 凭证、计费规则等。

## ✨ 核心特性

- 🔐 **安全的 API Key 管理** - AES-256-GCM 加密存储 + 脱敏显示
- 🎛️ **灵活的模型配置** - 支持多个提供商和模型，动态配置无需重启
- 💰 **智能计费系统** - 输入/输出 Token 分别计费，支持时间范围管理
- 🛠️ **实用工具** - 价格计算器、凭证测试等
- 🎨 **优秀的用户体验** - Glass UI 设计，实时反馈
- 🔄 **向后兼容** - 环境变量降级方案，平滑迁移

## 📦 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── models/              # 数据模型（5个）
│   │   ├── schemas/             # Pydantic Schema（5个）
│   │   ├── api/v1/admin/        # API 端点（29个）
│   │   ├── core/                # 核心服务（加密、积分）
│   │   ├── ai/adapters/         # 适配器系统
│   │   └── utils/               # 工具函数
│   ├── scripts/                 # 脚本工具
│   │   ├── init_model_data.py           # 数据初始化
│   │   ├── test_model_management.py     # 系统测试
│   │   ├── migrate_env_to_db.py         # 环境变量迁移
│   │   └── test_api_endpoints.py        # API 测试
│   └── alembic/versions/        # 数据库迁移
│
├── frontend/
│   └── src/
│       ├── services/            # API 服务层
│       └── pages/admin/ModelManagement/  # 管理组件（5个）
│
└── docs/                        # 文档（7个）
    ├── model-management-quickstart.md
    ├── model-management-integration-guide.md
    ├── model-management-deployment-checklist.md
    └── ...
```

## 🚀 快速开始

### 1. 生成加密密钥

```bash
python3 -c "import os, base64; print('ENCRYPTION_KEY=' + base64.b64encode(os.urandom(32)).decode())"
```

### 2. 设置环境变量

```bash
export ENCRYPTION_KEY="<生成的密钥>"
```

### 3. 运行数据库迁移

```bash
cd backend
alembic upgrade head
```

### 4. 初始化数据

```bash
python3 scripts/init_model_data.py
```

### 5. 访问管理界面

```
http://localhost:3000/admin/models
```

## 📚 文档

### 快速参考
- [快速开始指南](docs/model-management-quickstart.md) - 5分钟部署
- [部署检查清单](docs/model-management-deployment-checklist.md) - 完整的部署检查

### 详细文档
- [项目完成报告](docs/model-management-completion-report.md) - 详细的功能说明
- [集成指南](docs/model-management-integration-guide.md) - 如何集成到现有系统
- [安全审计报告](docs/model-management-security.md) - 安全性分析
- [性能优化建议](docs/model-management-performance.md) - 性能优化指南
- [最终交付总结](docs/model-management-final-summary.md) - 项目总结

## 🛠️ 实用脚本

### 测试系统

```bash
cd backend
python3 scripts/test_model_management.py
```

### 迁移环境变量

```bash
cd backend
python3 scripts/migrate_env_to_db.py
```

### 测试 API 端点

```bash
cd backend
python3 scripts/test_api_endpoints.py <admin_token>
```

## 🎯 功能模块

### 1. 提供商管理
- 创建、编辑、删除提供商
- 支持 OpenAI、Anthropic、自定义提供商
- 启用/禁用控制

### 2. 模型配置
- 管理 AI 模型参数
- Token 限制配置
- 超时和温度设置
- 设置默认模型

### 3. 凭证管理
- AES-256-GCM 加密存储
- API Key 脱敏显示
- 配额管理
- 凭证测试

### 4. 计费规则
- 输入/输出 Token 分别计费
- 时间范围管理
- 价格计算器
- 历史价格查询

### 5. 系统配置
- 全局配置管理
- 类型化配置编辑
- 默认模型设置

## 🔒 安全特性

- **加密存储** - AES-256-GCM 加密 API Key
- **脱敏显示** - 所有界面 API Key 脱敏
- **HTTPS 强制** - 生产环境强制 HTTPS
- **权限控制** - 严格的管理员权限验证
- **输入验证** - 完整的 Pydantic 验证

## 📊 技术栈

### 后端
- FastAPI
- SQLAlchemy 2.0 (Async)
- PostgreSQL
- Alembic
- Cryptography

### 前端
- React 18
- TypeScript
- Ant Design
- Tailwind CSS
- Dayjs

## 🔄 向后兼容

系统完全向后兼容：

1. **环境变量降级** - 数据库配置不可用时自动降级
2. **传统计费方法** - 保留原有的计费方法
3. **可选参数** - 所有新参数都是可选的

## 📈 性能优化

- 数据库索引优化
- 查询优化（JOIN 代替多次查询）
- Redis 缓存支持（可选）
- 连接池配置

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 支持

如有问题，请查看文档或提交 Issue。

---

**版本:** v1.0.0
**最后更新:** 2026-02-08
**开发者:** Claude (Anthropic)
