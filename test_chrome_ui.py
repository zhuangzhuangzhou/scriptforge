#!/usr/bin/env python3
"""Chrome DevTools UI测试脚本"""

import json
import subprocess
import time
import urllib.request

def get_tabs():
    """获取Chrome标签页列表"""
    with urllib.request.urlopen('http://localhost:9222/json/list') as response:
        return json.loads(response.read().decode())

def navigate_to_url(tab_id, url):
    """导航到指定URL"""
    req = urllib.request.Request(
        f'http://localhost:9222/json/navigate/{tab_id}',
        data=json.dumps({'url': url}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def get_page_info(tab_id):
    """获取页面信息"""
    with urllib.request.urlopen(f'http://localhost:9222/json/inspect/{tab_id}') as response:
        return json.loads(response.read().decode())

def main():
    print("🔍 Chrome DevTools UI 测试")
    print("=" * 50)

    # 获取标签页列表
    tabs = get_tabs()
    print(f"\n📋 当前标签页数量: {len(tabs)}")

    # 查找或创建前端页面标签页
    frontend_tab = None
    for tab in tabs:
        if 'localhost:5173' in tab.get('url', ''):
            frontend_tab = tab
            break

    # 打开前端页面
    target_url = "http://localhost:5173/"
    print(f"\n🌐 打开前端页面: {target_url}")

    # 使用命令行打开页面
    subprocess.run(['open', target_url], check=True)
    time.sleep(3)

    # 重新获取标签页
    tabs = get_tabs()
    for tab in tabs:
        if 'localhost:5173' in tab.get('url', ''):
            frontend_tab = tab
            print(f"✅ 找到前端标签页: {tab.get('title')}")
            print(f"   URL: {tab.get('url')}")
            break

    if not frontend_tab:
        print("❌ 未找到前端标签页")
        return

    # 获取页面标题
    print(f"\n📄 页面标题: {frontend_tab.get('title')}")

    # 获取页面DOM
    print(f"\n🔧 标签页ID: {frontend_tab.get('id')}")
    print(f"   WebSocket: {frontend_tab.get('webSocketDebuggerUrl', 'N/A')[:50]}...")

    print("\n" + "=" * 50)
    print("✅ 前端页面测试完成")
    print(f"   页面标题: {frontend_tab.get('title')}")
    print(f"   页面URL: {frontend_tab.get('url')}")

if __name__ == '__main__':
    main()
