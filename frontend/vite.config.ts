import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // 超过 800KB 才警告
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          // React 核心
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // UI 组件库
          'vendor-antd': ['antd'],
          // 图标库
          'vendor-icons': ['@ant-design/icons', 'lucide-react'],
          // 动画库
          'vendor-motion': ['framer-motion'],
          // 代码编辑器（最大，单独拆）
          'vendor-monaco': ['@monaco-editor/react'],
          // 图表库
          'vendor-charts': ['recharts'],
          // Markdown 渲染
          'vendor-markdown': ['react-markdown', 'remark-gfm', 'remark-frontmatter'],
          // 拖拽库
          'vendor-dnd': ['@dnd-kit/core', '@dnd-kit/sortable', '@dnd-kit/utilities'],
          // 工具库
          'vendor-utils': ['axios', 'zustand'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('[Proxy] 错误:', err)
          })
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('[Proxy] 发送请求:', req.method, req.url)
          })
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('[Proxy] 收到响应:', proxyRes.statusCode, req.url)
          })
          proxy.on('upgrade', (req, socket, head) => {
            console.log('[Proxy] WebSocket 升级:', req.url)
          })
        },
      },
    },
  },
})
