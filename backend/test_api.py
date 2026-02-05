#!/usr/bin/env python3
"""
后端接口测试脚本
"""
import asyncio
import aiohttp
import json
import sys

BASE_URL = "http://localhost:8000"

async def test_api():
    results = []
    
    async with aiohttp.ClientSession() as session:
        # 1. 基础接口测试
        print("=" * 60)
        print("1. 测试基础接口")
        print("=" * 60)
        
        # 测试根路径
        async with session.get(f"{BASE_URL}/") as resp:
            data = await resp.json()
            results.append(("GET /", resp.status, data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET / : {resp.status}")
        
        # 测试健康检查
        async with session.get(f"{BASE_URL}/health") as resp:
            data = await resp.json()
            results.append(("GET /health", resp.status, data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /health : {resp.status} - {data}")
        
        # 测试等级配置
        async with session.get(f"{BASE_URL}/api/v1/user/quota/tiers") as resp:
            data = await resp.json()
            results.append(("GET /api/v1/user/quota/tiers", resp.status, len(data.get('tiers', []))))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/user/quota/tiers : 等级数={len(data.get('tiers', []))}")
        
        # 2. 用户注册和登录
        print("\n" + "=" * 60)
        print("2. 测试认证接口")
        print("=" * 60)
        
        # 注册
        register_data = {
            "email": "apitest@example.com",
            "username": "apitestuser",
            "password": "testpass123",
            "full_name": "API Test User"
        }
        async with session.post(f"{BASE_URL}/api/v1/auth/register", json=register_data) as resp:
            result = await resp.json()
            reg_status = resp.status
            results.append(("POST /api/v1/auth/register", resp.status, "email" in result))
            print(f"[{'✓' if resp.status == 201 else '✗'}] POST /api/v1/auth/register : {resp.status}")
            user_id = result.get("id") if "id" in result else None
        
        # 登录
        login_data = "username=apitestuser&password=testpass123"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(f"{BASE_URL}/api/v1/auth/login", data=login_data, headers=headers) as resp:
            result = await resp.json()
            token = result.get("access_token")
            results.append(("POST /api/v1/auth/login", resp.status, token is not None))
            print(f"[{'✓' if resp.status == 200 else '✗'}] POST /api/v1/auth/login : {resp.status} - token={token[:20]}...")
        
        auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # 3. 需要认证的接口测试
        print("\n" + "=" * 60)
        print("3. 测试需要认证的接口")
        print("=" * 60)
        
        # 获取配额
        async with session.get(f"{BASE_URL}/api/v1/user/quota", headers=auth_headers) as resp:
            data = await resp.json()
            results.append(("GET /api/v1/user/quota", resp.status, "tier" in data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/user/quota : tier={data.get('tier')}")
        
        # 获取技能列表
        async with session.get(f"{BASE_URL}/api/v1/skills/available", headers=auth_headers) as resp:
            data = await resp.json()
            results.append(("GET /api/v1/skills/available", resp.status, "skills" in data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/skills/available : skills={len(data.get('skills', []))}")
        
        # 获取项目列表
        async with session.get(f"{BASE_URL}/api/v1/projects", headers=auth_headers) as resp:
            data = await resp.json()
            results.append(("GET /api/v1/projects", resp.status, isinstance(data, list)))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/projects : count={len(data)}")
        
        # 获取 Pipelines
        async with session.get(f"{BASE_URL}/api/v1/pipelines/pipelines?include_default=true", headers=auth_headers) as resp:
            data = await resp.json()
            results.append(("GET /api/v1/pipelines/pipelines", resp.status, "total" in data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/pipelines/pipelines : total={data.get('total')}")
        
        # 获取 Agent 定义
        async with session.get(f"{BASE_URL}/api/v1/agents/definitions", headers=auth_headers) as resp:
            data = await resp.json()
            results.append(("GET /api/v1/agents/definitions", resp.status, "agents" in data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/agents/definitions : count={data.get('pagination', {}).get('total')}")
        
        # 获取账单记录
        async with session.get(f"{BASE_URL}/api/v1/billing/records", headers=auth_headers) as resp:
            data = await resp.json()
            results.append(("GET /api/v1/billing/records", resp.status, "records" in data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/billing/records : count={len(data.get('records', []))}")
        
        # 获取订阅状态
        async with session.get(f"{BASE_URL}/api/v1/subscription/me", headers=auth_headers) as resp:
            data = await resp.json()
            results.append(("GET /api/v1/subscription/me", resp.status, "current_tier" in data))
            print(f"[{'✓' if resp.status == 200 else '✗'}] GET /api/v1/subscription/me : tier={data.get('current_tier')}")
        
        # 4. 测试需要管理员权限的接口
        print("\n" + "=" * 60)
        print("4. 测试需要管理员权限的接口")
        print("=" * 60)
        
        async with session.get(f"{BASE_URL}/api/v1/admin/stats", headers=auth_headers) as resp:
            data = await resp.json()
            is_403 = resp.status == 403 and "权限" in str(data)
            results.append(("GET /api/v1/admin/stats (should 403)", resp.status, is_403))
            print(f"[{'✓' if is_403 else '✗'}] GET /api/v1/admin/stats : {resp.status} (需要管理员权限)")
    
    # 打印测试总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, status, check in results:
        if check and status < 300:
            passed += 1
            status_icon = "✓"
        else:
            failed += 1
            status_icon = "✗"
        print(f"[{status_icon}] {name}: HTTP {status}")
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(test_api())
    sys.exit(0 if success else 1)
