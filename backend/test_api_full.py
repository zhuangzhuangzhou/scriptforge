#!/usr/bin/env python3
"""
完整的 API 测试脚本 - 包括拆解功能测试
"""
import asyncio
import aiohttp
import json
import sys

BASE_URL = "http://localhost:8000"

async def test_full_api():
    """完整 API 测试"""
    results = []
    token = None

    async with aiohttp.ClientSession() as session:
        # 1. 基础检查
        print("=" * 60)
        print("1. 基础服务检查")
        print("=" * 60)

        async with session.get(f"{BASE_URL}/health") as resp:
            data = await resp.json()
            print(f"[{'✓' if resp.status == 200 else '✗'}] Health Check: {data}")

        # 2. 登录获取 Token
        print("\n" + "=" * 60)
        print("2. 用户认证")
        print("=" * 60)

        # 先尝试登录（测试用户可能已存在）
        login_data = "username=apitestuser&password=testpass123"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with session.post(f"{BASE_URL}/api/v1/auth/login", data=login_data, headers=headers) as resp:
            if resp.status == 200:
                result = await resp.json()
                token = result.get("access_token")
                print(f"[✓] Login success: {token[:30]}...")
            else:
                # 如果用户不存在，先注册
                print("[-] User not found, trying register...")
                register_data = {
                    "email": "apitest@example.com",
                    "username": "apitestuser",
                    "password": "testpass123",
                    "full_name": "API Test User"
                }
                async with session.post(f"{BASE_URL}/api/v1/auth/register", json=register_data) as resp:
                    if resp.status in [200, 201]:
                        print(f"[✓] Register success")
                        # 再次登录
                        async with session.post(f"{BASE_URL}/api/v1/auth/login", data=login_data, headers=headers) as resp:
                            result = await resp.json()
                            token = result.get("access_token")
                            print(f"[✓] Login after register: {token[:30]}...")
                    else:
                        error = await resp.text()
                        print(f"[✗] Register failed: {error}")

        if not token:
            print("[✗] Cannot get token, exiting...")
            return False

        auth_headers = {"Authorization": f"Bearer {token}"}

        # 3. 测试项目 API
        print("\n" + "=" * 60)
        print("3. 项目管理 API")
        print("=" * 60)

        # 创建项目
        project_data = {
            "name": "API 测试项目",
            "description": "API 自动测试创建的项目",
            "novel_type": "webnovel"
        }

        async with session.post(f"{BASE_URL}/api/v1/projects", json=project_data, headers=auth_headers) as resp:
            if resp.status in [200, 201]:
                project = await resp.json()
                project_id = project.get("id")
                print(f"[✓] Create project: {project_id}")
            else:
                error = await resp.text()
                print(f"[✗] Create project failed: {error}")
                project_id = None

        # 获取项目列表
        async with session.get(f"{BASE_URL}/api/v1/projects", headers=auth_headers) as resp:
            projects = await resp.json()
            print(f"[✓] Get projects: {len(projects)} projects")
            if projects and not project_id:
                project_id = projects[0].get("id")

        # 4. 测试批次 API
        print("\n" + "=" * 60)
        print("4. 批次管理 API")
        print("=" * 60)

        batch_id = None

        if project_id:
            # 获取项目详情（包含批次）
            async with session.get(f"{BASE_URL}/api/v1/projects/{project_id}", headers=auth_headers) as resp:
                if resp.status == 200:
                    project_detail = await resp.json()
                    batches = project_detail.get("batches", [])
                    print(f"[✓] Get project detail: {len(batches)} batches")
                    if batches:
                        batch_id = batches[0].get("id")
                        print(f"[+] First batch ID: {batch_id}")
                else:
                    error = await resp.text()
                    print(f"[✗] Get project detail failed: {error}")

            # 获取批次列表
            async with session.get(f"{BASE_URL}/api/v1/batches", headers=auth_headers) as resp:
                if resp.status == 200:
                    batches = await resp.json()
                    if isinstance(batches, dict):
                        batches_list = batches.get("batches", [])
                    else:
                        batches_list = batches
                    print(f"[✓] Get all batches: {len(batches_list)} batches")
                    if batches_list and not batch_id:
                        batch_id = batches_list[0].get("id") if isinstance(batches_list[0], dict) else None
                else:
                    print(f"[~] Get batches: {resp.status}")
                    batches_list = []

        # 5. 测试拆解 API
        print("\n" + "=" * 60)
        print("5. 拆解任务 API")
        print("=" * 60)

        # 获取可用的 AI 模型
        async with session.get(f"{BASE_URL}/api/v1/admin/models", headers=auth_headers) as resp:
            if resp.status == 200:
                models = await resp.json()
                print(f"[✓] Get AI models: {len(models)} models")
            else:
                print(f"[~] Get AI models: {resp.status} (may require admin)")

        # 获取拆解规则
        async with session.get(f"{BASE_URL}/api/v1/split-rules", headers=auth_headers) as resp:
            if resp.status == 200:
                rules = await resp.json()
                print(f"[✓] Get split rules: {len(rules)} rules")
            else:
                print(f"[~] Get split rules: {resp.status}")

        # 6. 测试 WebSocket 连接
        print("\n" + "=" * 60)
        print("6. WebSocket 连接测试")
        print("=" * 60)

        ws_url = f"{BASE_URL.replace('http', 'ws')}/ws"
        try:
            async with session.ws_connect(ws_url, headers=auth_headers) as ws:
                print(f"[✓] WebSocket connected: {ws_url}")
                # 发送测试消息
                await ws.send_json({"type": "ping"})
                # 接收响应
                msg = await ws.receive_json(timeout=5)
                print(f"[+] WebSocket response: {msg.get('type')}")
        except Exception as e:
            print(f"[✗] WebSocket failed: {str(e)[:100]}")

        # 7. 测试配额 API
        print("\n" + "=" * 60)
        print("7. 配额管理 API")
        print("=" * 60)

        async with session.get(f"{BASE_URL}/api/v1/user/quota", headers=auth_headers) as resp:
            quota = await resp.json()
            print(f"[✓] Get quota: tier={quota.get('tier')}, episodes={quota.get('used_episodes')}/{quota.get('total_episodes')}")

        # 8. 测试技能 API
        print("\n" + "=" * 60)
        print("8. 技能系统 API")
        print("=" * 60)

        async with session.get(f"{BASE_URL}/api/v1/skills/available", headers=auth_headers) as resp:
            skills = await resp.json()
            skills_list = skills if isinstance(skills, list) else skills.get('skills', [])
            print(f"[✓] Get available skills: {len(skills_list)} skills")
            for skill in skills_list[:3]:
                print(f"  - {skill.get('name', skill) if isinstance(skill, dict) else skill}")

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"Token: {token[:30] if token else 'None'}...")
    print(f"Project ID: {project_id}")
    print(f"Batch ID: {batch_id}")
    print(f"WebSocket: {ws_url}")

    return True

if __name__ == "__main__":
    success = asyncio.run(test_full_api())
    sys.exit(0 if success else 1)
