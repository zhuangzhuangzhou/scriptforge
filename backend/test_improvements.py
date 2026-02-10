"""测试改进后的 API 接口"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

# 测试用的 token（需要替换为实际的管理员 token）
# 可以通过登录接口获取
TOKEN = None


async def get_admin_token():
    """获取管理员 token"""
    async with httpx.AsyncClient() as client:
        # 假设有一个测试管理员账号
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"登录失败: {response.status_code}")
            print(response.text)
            return None


async def test_providers_pagination():
    """测试提供商列表分页功能"""
    print("\n" + "="*50)
    print("测试 1: 提供商列表分页")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        # 测试分页
        response = await client.get(
            f"{BASE_URL}/admin/models/providers",
            headers=headers,
            params={
                "page": 1,
                "page_size": 10,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 分页查询成功")
            print(f"  总数: {data['total']}")
            print(f"  当前页: {data['page']}")
            print(f"  每页数量: {data['page_size']}")
            print(f"  总页数: {data['total_pages']}")
            print(f"  返回条目数: {len(data['items'])}")
        else:
            print(f"✗ 分页查询失败: {response.status_code}")
            print(response.text)


async def test_providers_search():
    """测试提供商搜索功能"""
    print("\n" + "="*50)
    print("测试 2: 提供商搜索")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        # 测试搜索
        response = await client.get(
            f"{BASE_URL}/admin/models/providers",
            headers=headers,
            params={
                "search": "openai",
                "page": 1,
                "page_size": 10
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 搜索成功")
            print(f"  搜索关键词: openai")
            print(f"  找到 {data['total']} 个结果")
            if data['items']:
                print(f"  第一个结果: {data['items'][0]['display_name']}")
        else:
            print(f"✗ 搜索失败: {response.status_code}")
            print(response.text)


async def test_batch_operations():
    """测试批量操作"""
    print("\n" + "="*50)
    print("测试 3: 批量操作")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        # 先获取一些提供商 ID
        response = await client.get(
            f"{BASE_URL}/admin/models/providers",
            headers=headers,
            params={"page": 1, "page_size": 3}
        )
        
        if response.status_code != 200:
            print("✗ 无法获取提供商列表")
            return
        
        data = response.json()
        if not data['items']:
            print("✗ 没有可用的提供商")
            return
        
        provider_ids = [item['id'] for item in data['items'][:2]]
        print(f"  选择了 {len(provider_ids)} 个提供商进行测试")
        
        # 测试批量禁用
        response = await client.post(
            f"{BASE_URL}/admin/models/providers/batch/toggle",
            headers=headers,
            params={"enable": False},
            json={"ids": provider_ids}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 批量禁用成功")
            print(f"  成功: {result['success_count']}")
            print(f"  失败: {result['failed_count']}")
            print(f"  消息: {result['message']}")
        else:
            print(f"✗ 批量禁用失败: {response.status_code}")
            print(response.text)
        
        # 恢复状态：批量启用
        response = await client.post(
            f"{BASE_URL}/admin/models/providers/batch/toggle",
            headers=headers,
            params={"enable": True},
            json={"ids": provider_ids}
        )
        
        if response.status_code == 200:
            print(f"✓ 已恢复提供商状态")


async def test_credential_test():
    """测试凭证测试功能"""
    print("\n" + "="*50)
    print("测试 4: 凭证测试")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        # 先获取一个凭证
        response = await client.get(
            f"{BASE_URL}/admin/models/credentials",
            headers=headers
        )
        
        if response.status_code != 200:
            print("✗ 无法获取凭证列表")
            return
        
        data = response.json()
        if not data:
            print("✗ 没有可用的凭证")
            return
        
        credential_id = data[0]['id']
        credential_name = data[0]['credential_name']
        print(f"  测试凭证: {credential_name}")
        
        # 测试凭证
        response = await client.post(
            f"{BASE_URL}/admin/models/credentials/{credential_id}/test",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 凭证测试完成")
            print(f"  结果: {'成功' if result['success'] else '失败'}")
            print(f"  消息: {result['message']}")
            print(f"  提供商: {result['provider_name']}")
        else:
            print(f"✗ 凭证测试失败: {response.status_code}")
            print(response.text)


async def test_delete_response_format():
    """测试删除操作的响应格式"""
    print("\n" + "="*50)
    print("测试 5: 删除操作响应格式")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        # 创建一个测试提供商
        test_provider = {
            "provider_key": "test_delete_format",
            "display_name": "Test Delete Format",
            "provider_type": "openai"
        }
        
        response = await client.post(
            f"{BASE_URL}/admin/models/providers",
            headers=headers,
            json=test_provider
        )
        
        if response.status_code != 200:
            print("✗ 无法创建测试提供商")
            return
        
        provider_id = response.json()['id']
        print(f"✓ 创建测试提供商: {provider_id}")
        
        # 删除提供商
        response = await client.delete(
            f"{BASE_URL}/admin/models/providers/{provider_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 删除成功")
            print(f"  响应格式: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 验证响应格式
            if 'success' in result and 'message' in result:
                print(f"✓ 响应格式符合规范")
            else:
                print(f"✗ 响应格式不符合规范")
        else:
            print(f"✗ 删除失败: {response.status_code}")
            print(response.text)


async def main():
    """主测试函数"""
    global TOKEN
    
    print("开始测试改进后的 API 接口")
    print("="*50)
    
    # 获取 token
    print("正在获取管理员 token...")
    TOKEN = await get_admin_token()
    
    if not TOKEN:
        print("✗ 无法获取 token，请确保：")
        print("  1. 后端服务正在运行")
        print("  2. 存在管理员账号 (username: admin, password: admin123)")
        return
    
    print(f"✓ 获取 token 成功")
    
    # 运行测试
    try:
        await test_providers_pagination()
        await test_providers_search()
        await test_batch_operations()
        await test_credential_test()
        await test_delete_response_format()
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    print("测试完成")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
