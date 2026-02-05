# 前端开发规范

## 技术栈

- **框架**: React 18.2.0
- **语言**: TypeScript 5.2.2
- **构建**: Vite 5.0.8
- **UI**: Ant Design 5.12.0
- **状态**: Zustand 4.4.7
- **路由**: React Router 6.21.0

## 目录结构

```
frontend/src/
├── pages/           # 页面组件
├── components/      # 公共组件
├── services/        # API 服务
├── store/           # 状态管理
├── context/         # React Context
└── utils/           # 工具函数
```

## 代码规范

### 组件
- 使用函数组件 + Hooks
- Props 使用 TypeScript 接口定义
- 使用 Ant Design 组件库

### 状态管理
- 全局状态使用 Zustand
- 认证状态使用 Context
- 组件状态使用 useState

### API 调用
- 使用 axios 实例
- 统一错误处理
- 使用 TypeScript 类型
