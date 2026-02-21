#!/bin/bash
# Chrome MCP 快速启动脚本

echo "🚀 启动 Chrome MCP 服务..."

# 检查 Chrome 调试端口是否已开启
if curl -s http://localhost:9222/json > /dev/null 2>&1; then
    echo "✅ Chrome 调试端口已开启 (9222)"
else
    echo "🔄 Chrome 未开启调试端口，尝试重启 Chrome..."

    # 强制关闭 Chrome（确保以调试模式启动）
    osascript -e 'tell application "Google Chrome" to quit' 2>/dev/null
    sleep 1

    # 使用默认配置启动 Chrome（保持登录状态）
    # 添加 --remote-allow-origins=* 允许 WebSocket 连接
    # 使用 --user-data-dir 指定数据目录
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
        --remote-debugging-port=9222 \
        --remote-allow-origins=* \
        --user-data-dir=/tmp/chrome-debug \
        --new-window about:blank &

    # 等待 Chrome 启动
    sleep 3

    echo "✅ Chrome 已启动，调试端口: 9222"
fi

# 验证连接
echo "🔍 验证连接..."
if curl -s http://localhost:9222/json | head -5; then
    echo ""
    echo "🎉 Chrome MCP 服务就绪！"
    echo "📝 现在可以重启 Claude Code 使用 MCP 工具"
else
    echo "❌ 连接验证失败，请手动检查 Chrome 是否正常开启"
fi
