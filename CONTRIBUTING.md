# 贡献指南

感谢你对 ScriptForge 项目的关注！本文档将帮助你了解如何参与项目开发。

## 🤔 如何贡献

### 报告 Bug

如果你发现了 bug，请通过 [GitHub Issues](https://github.com/your-username/scriptforge/issues) 提交报告。

提交 Bug 报告时，请包含：

1. **清晰的标题**：简要描述问题
2. **复现步骤**：详细说明如何复现该问题
3. **预期行为**：说明你期望发生什么
4. **实际行为**：说明实际发生了什么
5. **环境信息**：操作系统、Python 版本、Node.js 版本等
6. **截图**：如果适用，添加截图帮助解释问题

### 提出新功能

如果你有新功能的想法，欢迎通过 GitHub Issues 提出。请详细描述：

1. 功能的用途和价值
2. 可能的实现方式
3. 是否愿意自己实现

### 提交代码

1. **Fork 项目**
   ```bash
   git clone https://github.com/your-username/scriptforge.git
   cd scriptforge
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **编写代码**
   - 遵循项目的代码规范
   - 添加必要的测试
   - 更新相关文档

4. **提交变更**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

   提交信息格式：
   - `feat`: 新功能
   - `fix`: Bug 修复
   - `docs`: 文档更新
   - `refactor`: 代码重构
   - `test`: 测试相关
   - `chore`: 其他修改

5. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 等待代码审查

## 📝 代码规范

### Python (后端)

- 遵循 PEP 8 规范
- 使用 Black 格式化代码
- 使用 Flake8 检查代码质量
- 为函数和类添加类型注解
- 编写文档字符串

### TypeScript (前端)

- 遵循 ESLint 规则
- 使用函数式组件和 Hooks
- 组件命名使用 PascalCase
- 文件命名使用 camelCase

### Git 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档
- `refactor`: 重构
- `test`: 测试
- `chore`: 其他

**示例**:
```
feat(api): 添加用户认证接口

- 实现 JWT 认证
- 添加登录/注册接口
- 添加单元测试

Closes #123
```

## 🧪 测试

### 后端测试

```bash
cd backend
pytest
```

### 前端测试

```bash
cd frontend
npm test
```

## 📚 文档贡献

如果你发现文档有错误或需要改进：

1. 文档位于 `docs/` 目录
2. 使用 Markdown 格式
3. 保持简洁明了
4. 添加示例代码

## 💬 交流

- GitHub Issues: 用于 Bug 报告和功能请求
- GitHub Discussions: 用于一般讨论和问答

## ⚖️ 行为准则

请阅读并遵守我们的行为准则，保持友善和尊重。

## 📄 许可证

通过贡献代码，你同意你的代码将按照 AGPL-3.0 许可证进行授权。

---

再次感谢你的贡献！🎉