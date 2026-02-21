#!/usr/bin/env python3
"""Chrome DevTools UI测试脚本 - 改进版"""

import json
import base64
import urllib.request
import time
import os
import websocket

# 目标URL列表
PAGES = [
    ("登录页面", "http://localhost:5173/login"),
    ("仪表板", "http://localhost:5173/dashboard"),
    ("工作区", "http://localhost:5173/workspace"),
    ("用户管理", "http://localhost:5173/admin/users"),
    ("模型管理", "http://localhost:5173/admin/models"),
    ("技能管理", "http://localhost:5173/skills"),
]

SCREENSHOT_DIR = "/tmp"
CONSOLE_LOG_FILE = "/tmp/console_errors.log"

def get_tabs():
    """获取Chrome标签页列表"""
    with urllib.request.urlopen('http://localhost:9222/json/list') as response:
        return json.loads(response.read().decode())

def navigate_via_js(ws_url, url):
    """通过JavaScript导航到URL"""
    ws = websocket.create_connection(ws_url, timeout=10)

    # 先启用DOM
    ws.send(json.dumps({'id': 1, 'method': 'Page.enable'}))
    time.sleep(0.2)

    # 通过导航
    ws.send(json.dumps({
        'id': 2,
        'method': 'Page.navigate',
        'params': {'url': url}
    }))

    # 等待导航完成
    time.sleep(3)

    ws.close()
    return True

def capture_screenshot(ws_url, filename):
    """捕获屏幕截图"""
    ws = websocket.create_connection(ws_url, timeout=10)

    # 捕获截图
    ws.send(json.dumps({'id': 1, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    response = ws.recv()
    ws.close()

    data = json.loads(response)
    if 'result' in data and 'data' in data['result']:
        image_data = data['result']['data']
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return True
    return False

def get_console_errors(ws_url):
    """获取控制台错误"""
    ws = websocket.create_connection(ws_url, timeout=10)

    # 启用日志
    ws.send(json.dumps({'id': 1, 'method': 'Log.enable'}))
    time.sleep(0.3)

    # 获取控制台消息
    errors = []
    for _ in range(20):
        try:
            ws.settimeout(0.3)
            response = ws.recv()
            data = json.loads(response)
            if 'method' in data:
                if data['method'] == 'Runtime.exceptionThrown':
                    errors.append(data)
                elif data['method'] == 'Log.entryAdded':
                    entry = data.get('params', {}).get('entry', {})
                    if entry.get('level') == 'error':
                        errors.append(data)
        except:
            break

    ws.close()
    return errors

def main():
    print("=" * 60)
    print("Chrome DevTools UI 测试 - 改进版")
    print("=" * 60)

    # 获取标签页列表
    tabs = get_tabs()
    print(f"\n📋 当前标签页数量: {len(tabs)}")

    # 找到前端标签页
    frontend_tab = None
    for tab in tabs:
        url = tab.get('url', '')
        if 'localhost:5173' in url:
            frontend_tab = tab
            break

    if not frontend_tab:
        print("❌ 未找到前端标签页")
        return

    tab_id = frontend_tab.get('id')
    ws_url = frontend_tab.get('webSocketDebuggerUrl')

    print(f"\n✅ 使用标签页ID: {tab_id}")
    print(f"   WebSocket: {ws_url[:50]}...")
    print(f"   当前URL: {frontend_tab.get('url')}")

    # 清空控制台日志
    with open(CONSOLE_LOG_FILE, 'w') as f:
        f.write("控制台错误日志\n")
        f.write("=" * 50 + "\n")

    results = []

    # 遍历访问各个页面
    for title, url in PAGES:
        print(f"\n{'='*60}")
        print(f"🧪 测试页面: {title}")
        print(f"   URL: {url}")
        print("=" * 60)

        try:
            # 通过JavaScript导航
            print("   导航中...")
            navigate_via_js(ws_url, url)

            # 等待页面加载
            time.sleep(3)

            # 截图
            screenshot_name = f"{title.replace(' ', '_')}.png"
            screenshot_path = os.path.join(SCREENSHOT_DIR, screenshot_name)

            try:
                if capture_screenshot(ws_url, screenshot_path):
                    print(f"   📸 截图已保存: {screenshot_path}")
                    results.append((title, url, screenshot_path, "成功"))
                else:
                    print(f"   ❌ 截图失败")
                    results.append((title, url, None, "截图失败"))
            except Exception as e:
                print(f"   ❌ 截图出错: {e}")
                results.append((title, url, None, str(e)))

            # 获取控制台错误
            try:
                console_errors = get_console_errors(ws_url)

                if console_errors:
                    print(f"   ⚠️  控制台错误: {len(console_errors)}条")
                    with open(CONSOLE_LOG_FILE, 'a') as f:
                        f.write(f"\n页面: {title} ({url})\n")
                        for err in console_errors[:5]:
                            f.write(f"  - {json.dumps(err, ensure_ascii=False)[:200]}\n")
                else:
                    print(f"   ✅ 无控制台错误")

            except Exception as e:
                print(f"   ⚠️  获取控制台消息失败: {e}")

        except Exception as e:
            print(f"   ❌ 页面访问失败: {e}")
            results.append((title, url, None, str(e)))

    # 输出总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    for title, url, screenshot, status in results:
        status_icon = "✅" if "成功" in str(status) else "❌"
        print(f"{status_icon} {title}: {status}")
        if screenshot:
            print(f"   截图: {screenshot}")

    print(f"\n📝 控制台日志: {CONSOLE_LOG_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    main()
