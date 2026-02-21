#!/usr/bin/env python3
"""
Chrome MCP UI测试工具 - 简化版
使用HTTP API与Chrome DevTools Protocol交互
"""
import json
import base64
import time
import subprocess
import urllib.request
import urllib.error

# 配置
PAGE_ID = "3CD85B200A2C9B9EED146CE4E7C32A64"
DEVTOOLS_URL = f"http://localhost:9222/json"

def send_devtools_command(method, params=None):
    """发送Chrome DevTools Protocol命令"""
    url = f"http://localhost:9222/json/function/{PAGE_ID}"

    data = {"method": method}
    if params:
        data["params"] = params

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def get_page_list():
    """获取页面列表"""
    try:
        with urllib.request.urlopen(DEVTOOLS_URL, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"获取页面列表失败: {e}")
        return []

def main():
    print("Chrome MCP UI测试工具 - 简化版")
    print("=" * 50)

    # 1. 获取页面列表
    print("\n=== 1. 获取Chrome标签页 ===")
    pages = get_page_list()
    for i, page in enumerate(pages):
        print(f"{i+1}. [{page.get('type')}] {page.get('title')} - {page.get('url')}")

    # 找到目标页面
    target_page = None
    for page in pages:
        if page.get('id') == PAGE_ID:
            target_page = page
            break

    if not target_page:
        print(f"\n未找到目标页面: {PAGE_ID}")
        return

    print(f"\n目标页面: {target_page.get('title')}")
    print(f"URL: {target_page.get('url')}")

    # 2. 尝试使用 CDP HTTP API 进行操作
    print("\n=== 2. 使用Chrome DevTools API测试 ===")

    # 测试获取页面截图
    print("\n--- 截图测试 ---")
    # Chrome CDP HTTP API不支持直接截图，需要使用websocket
    # 改用其他方式验证

    # 测试页面加载
    result = send_devtools_command("Runtime.evaluate", {
        "expression": "document.title",
        "returnByValue": True
    })
    print(f"页面标题: {result}")

    # 测试获取页面URL
    result = send_devtools_command("Runtime.evaluate", {
        "expression": "window.location.href",
        "returnByValue": True
    })
    print(f"页面URL: {result}")

    # 测试获取页面DOM
    result = send_devtools_command("Runtime.evaluate", {
        "expression": "document.body.innerHTML.substring(0, 500)",
        "returnByValue": True
    })
    print(f"页面内容片段: {result}")

    # 3. 访问不同路由
    print("\n=== 3. 测试不同路由 ===")

    routes = [
        ("/login", "登录页"),
        ("/dashboard", "仪表板"),
        ("/admin/logs", "管理日志")
    ]

    for route, desc in routes:
        url = f"http://localhost:5173{route}"
        print(f"\n访问: {desc} ({url})")

        # 使用AppleScript打开新标签页
        cmd = f'''osascript -e 'tell application "Google Chrome"
            tell window 1
                make new tab with properties {{URL:"{url}"}}
            end tell
        end tell' '''

        subprocess.run(cmd, shell=True, capture_output=True)
        time.sleep(2)

    print("\n=== 测试完成 ===")
    print("注意: Chrome DevTools HTTP API功能有限，建议使用WebSocket或Puppeteer进行更深入的测试")

if __name__ == "__main__":
    main()
