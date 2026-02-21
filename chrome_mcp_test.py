#!/usr/bin/env python3
"""
Chrome MCP UI测试工具
通过Chrome DevTools Protocol进行前端UI测试
"""
import json
import base64
import time
import websocket

# 配置
PAGE_ID = "3CD85B200A2C9B9EED146CE4E7C32A64"
WS_URL = f"ws://localhost:9222/devtools/page/{PAGE_ID}"

def send_cmd(ws, method, params=None):
    """发送Chrome DevTools Protocol命令"""
    msg_id = int(time.time() * 1000)
    msg = {"id": msg_id, "method": method}
    if params:
        msg["params"] = params

    ws.send(json.dumps(msg))
    return msg_id

def recv_response(ws):
    """接收响应"""
    while True:
        try:
            result = ws.recv()
            data = json.loads(result)
            # 跳过通知消息
            if "id" not in data:
                continue
            return data
        except:
            continue

def enable_page_domains(ws):
    """启用页面相关域"""
    print("=== 启用页面调试域 ===")
    send_cmd(ws, "Page.enable")
    time.sleep(0.5)
    recv_response(ws)

    send_cmd(ws, "Log.enable")
    time.sleep(0.5)
    recv_response(ws)

    send_cmd(ws, "Runtime.enable")
    time.sleep(0.5)
    recv_response(ws)

    print("页面调试域已启用\n")

def get_screenshot(ws):
    """获取页面截图"""
    print("=== 获取页面截图 ===")

    # 触发截图
    msg_id = send_cmd(ws, "Page.captureScreenshot", {"format": "png", "fromSurface": True})

    response = recv_response(ws)
    if "result" in response and "data" in response["result"]:
        img_data = response["result"]["data"]
        with open("/tmp/chrome_mcp_screenshot.png", "wb") as f:
            f.write(base64.b64decode(img_data))
        print("截图已保存到: /tmp/chrome_mcp_screenshot.png")
    else:
        print(f"截图失败: {response}")
    print()

def get_page_info(ws):
    """获取页面信息"""
    print("=== 获取页面信息 ===")
    send_cmd(ws, "Page.getLayoutMetrics")
    response = recv_response(ws)
    if "result" in response:
        metrics = response["result"]
        print(f"内容大小: {metrics.get('contentSize', 'N/A')}")
        print(f"视口大小: {metrics.get('viewport', 'N/A')}")
    print()

def get_console_logs(ws):
    """获取控制台日志"""
    print("=== 获取控制台日志 ===")

    # 清除之前的日志
    send_cmd(ws, "Log.clear")
    time.sleep(0.3)

    # 启用控制台域
    send_cmd(ws, "Log.enable")
    time.sleep(0.5)

    # 获取日志
    send_cmd(ws, "Log.getEntries")
    time.sleep(0.5)

    console_messages = []
    try:
        ws.settimeout(1)
        for _ in range(20):
            try:
                msg = json.loads(ws.recv())
                if msg.get("method") == "Log.entryAdded":
                    entry = msg.get("params", {}).get("entry", {})
                    console_messages.append(entry)
            except:
                break
    except:
        pass

    if console_messages:
        print(f"找到 {len(console_messages)} 条控制台日志:")
        for i, entry in enumerate(console_messages[:10], 1):
            level = entry.get("level", "info")
            text = entry.get("text", "")
            url = entry.get("url", "")
            print(f"  {i}. [{level}] {text[:100]}")
            if url:
                print(f"      来源: {url[:60]}")
        if len(console_messages) > 10:
            print(f"  ... 还有 {len(console_messages) - 10} 条日志")
    else:
        print("没有控制台日志")
    print()

def navigate_to(ws, url):
    """导航到指定URL"""
    print(f"=== 导航到: {url} ===")
    msg_id = send_cmd(ws, "Page.navigate", {"url": url})

    # 等待导航完成
    time.sleep(3)

    # 获取响应
    response = recv_response(ws)
    if "result" in response:
        print(f"导航请求已发送")
    else:
        print(f"响应: {response}")
    print()

def get_page_content(ws):
    """获取页面DOM内容"""
    print("=== 获取页面内容 ===")

    # 获取文档
    send_cmd(ws, "DOM.getDocument")
    response = recv_response(ws)

    if "result" in response:
        root = response["result"].get("root", {})
        node_id = root.get("nodeId")

        if node_id:
            # 获取html标签内容
            send_cmd(ws, "DOM.getOuterHTML", {"nodeId": node_id})
            response = recv_response(ws)
            if "result" in response:
                html = response["result"].get("outerHTML", "")
                print(f"页面HTML长度: {len(html)} 字符")
                # 保存到文件
                with open("/tmp/page_content.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("页面HTML已保存到: /tmp/page_content.html")
    print()

def click_element(ws, selector):
    """点击页面元素"""
    print(f"=== 点击元素: {selector} ===")

    # 先获取元素
    send_cmd(ws, "DOM.getDocument")
    response = recv_response(ws)

    if "result" in response:
        root = response["result"].get("root", {})
        node_id = root.get("nodeId")

        if node_id:
            # 查询选择器
            send_cmd(ws, "DOM.querySelector", {"nodeId": node_id, "selector": selector})
            response = recv_response(ws)

            if "result" in response and "nodeId" in response["result"]:
                target_node_id = response["result"]["nodeId"]

                # 获取元素位置并点击
                send_cmd(ws, "DOM.getBoxModel", {"nodeId": target_node_id})
                response = recv_response(ws)

                if "result" in response:
                    model = response["result"].get("model", {})
                    content = model.get("content", [])
                    if content:
                        x = (content[0] + content[2]) / 2
                        y = (content[1] + content[5]) / 2

                        # 模拟点击
                        send_cmd(ws, "Input.dispatchMouseEvent", {
                            "type": "mousePressed",
                            "x": x,
                            "y": y,
                            "button": "left",
                            "clickCount": 1
                        })
                        time.sleep(0.1)
                        send_cmd(ws, "Input.dispatchMouseEvent", {
                            "type": "mouseReleased",
                            "x": x,
                            "y": y,
                            "button": "left",
                            "clickCount": 1
                        })
                        print(f"已点击元素中心坐标: ({x}, {y})")
                        return

    print(f"未找到元素: {selector}")
    print()

def main():
    print("Chrome MCP UI测试工具")
    print("=" * 50)

    # 连接WebSocket
    print(f"连接到: {WS_URL}\n")
    ws = websocket.create_connection(WS_URL)

    try:
        # 1. 启用页面调试域
        enable_page_domains(ws)

        # 2. 获取页面截图
        get_screenshot(ws)

        # 3. 获取页面信息
        get_page_info(ws)

        # 4. 获取控制台日志
        get_console_logs(ws)

        # 5. 获取页面内容
        get_page_content(ws)

        # 6. 尝试点击登录相关元素
        print("=== 尝试查找登录元素 ===")
        for selector in ["button", "a[href*='login']", "input[type='submit']", ".login-btn", "#login"]:
            send_cmd(ws, "DOM.getDocument")
            response = recv_response(ws)
            if "result" in response:
                root = response["result"].get("root", {})
                node_id = root.get("nodeId")
                if node_id:
                    send_cmd(ws, "DOM.querySelector", {"nodeId": node_id, "selector": selector})
                    response = recv_response(ws)
                    if "result" in response and response["result"].get("nodeId"):
                        print(f"找到元素: {selector}")
                        break

        # 7. 测试访问其他路由
        routes = [
            "http://localhost:5173/login",
            "http://localhost:5173/dashboard",
            "http://localhost:5173/admin/logs"
        ]

        for route in routes:
            navigate_to(ws, route)
            time.sleep(2)
            get_screenshot(ws)
            get_console_logs(ws)

        # 导航回首页
        navigate_to(ws, "http://localhost:5173")
        time.sleep(2)
        get_screenshot(ws)

    except Exception as e:
        print(f"错误: {e}")
    finally:
        ws.close()
        print("\n测试完成!")

if __name__ == "__main__":
    main()
