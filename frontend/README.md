# AI ScriptFlow Frontend

本项目是 AI ScriptFlow 的前端部分，基于 React + Vite + Ant Design 构建。

## 🛠 开发流程 (Development Workflow)

### 1. 启动开发服务器
确保后端服务已启动（默认 http://127.0.0.1:8000），然后运行：
```bash
npm run dev
```

### 2. 同步 API 类型
当后端 API 定义发生变化时，运行以下命令自动生成最新的 TypeScript 类型：
```bash
npm run gen:types
```
该命令会从后端的 OpenAPI 文档同步类型至 `src/types/schema.d.ts`。

## 🗺 导航与路由 (Usage Guide)

应用采用基于功能模块的路由结构：

*   **认证模块**: `/auth/login`, `/auth/register`
*   **用户工作区**: `/user/dashboard`, `/user/workspace/:projectId`
*   **管理后台**: `/admin/pipelines`, `/admin/skills`, `/admin/users`

## 🧪 验证
在提交代码前，请确保通过 Lint 检查：
```bash
npm run lint
```
