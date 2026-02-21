#!/usr/bin/env python3
"""
Chrome MCP UI测试工具
使用AppleScript和截图进行基本测试
"""
import subprocess
import time
import os
import sys

def run_applescript(script):
    """运行AppleScript命令"""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr

def get_chrome_tabs():
    """获取Chrome标签页列表"""
    script = '''
    tell application "Google Chrome"
        set tabList to {}
        repeat with w in windows
            repeat with t in tabs of w
                set end of tabList to {title of t, URL of t}
            end repeat
        end repeat
        return tabList
    end tell
    '''

    stdout, stderr = run_applescript(script)
    print("=== Chrome标签页列表 ===")
    if stdout:
        lines = stdout.strip().split(", ")
        for i, line in enumerate(lines, 1):
            print(f"{i}. {line}")
    else:
        print("无标签页")
    print()
    return stdout

def get_active_tab_url():
    """获取当前活动标签页URL"""
    script = '''
    tell application "Google Chrome"
        return URL of active tab of front window
    end tell
    '''
    stdout, _ = run_applescript(script)
    return stdout.strip()

def navigate_to(url):
    """导航到指定URL"""
    script = f'''
    tell application "Google Chrome"
        tell active tab of front window
            set URL to "{url}"
        end tell
    end tell
    '''
    run_applescript(script)
    time.sleep(2)

def take_screenshot(filename):
    """使用screencapture截图"""
    cmd = f"screencapture -x {filename}"
    subprocess.run(cmd, shell=True)
    print(f"截图已保存: {filename}")

def test_routes():
    """测试不同路由"""
    routes = [
        ("http://localhost:5173", "首页"),
        ("http://localhost:5173/login", "登录页"),
        ("http://localhost:5173/dashboard", "仪表板"),
        ("http://localhost:5173/admin/logs", "管理日志"),
    ]

    for url, desc in routes:
        print(f"\n=== 访问: {desc} ({url}) ===")
        navigate_to(url)

        # 等待页面加载
        time.sleep(3)

        # 获取当前URL
        current_url = get_active_tab_url()
        print(f"当前URL: {current_url}")

        # 截图
        filename = f"/tmp/chrome_mcp_{desc.replace('/', '_')}.png"
        take_screenshot(filename)

    # 返回首页
    print("\n=== 返回首页 ===")
    navigate_to("http://localhost:5173")
    time.sleep(2)

def check_frontend_server():
    """检查前端服务器是否运行"""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:5173", timeout=5) as response:
            print(f"前端服务器状态: {response.status}")
            return True
    except Exception as e:
        print(f"前端服务器未运行: {e}")
        return False

def main():
    print("=" * 60)
    print("Chrome MCP 前端UI测试工具")
    print("=" * 60)

    # 1. 检查前端服务器
    print("\n=== 1. 检查前端服务器 ===")
    check_frontend_server()

    # 2. 获取标签页列表
    print("\n=== 2. Chrome标签页状态 ===")
    get_chrome_tabs()

    # 3. 测试首页截图
    print("\n=== 3. 首页截图 ===")
    navigate_to("http://localhost:5173")
    time.sleep(3)
    take_screenshot("/tmp/chrome_mcp_homepage.png")

    # 4. 测试不同路由
    print("\n=== 4. 测试不同路由 ===")
    test_routes()

    # 5. 列出截图文件
    print("\n=== 5. 测试结果 ===")
    print("生成的截图文件:")
    import glob
    screenshots = glob.glob("/tmp/chrome_mcp_*.png")
    for s in sorted(screenshots):
        print(f"  - {s}")

    print("\n测试完成!")
    print("注意: 查看截图需要手动打开 /tmp 目录")

if __name__ == "__main__":
    main()
