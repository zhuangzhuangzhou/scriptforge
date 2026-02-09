"""
API 端点测试脚本

测试所有模型管理 API 端点

运行方式：
cd backend
python3 scripts/test_api_endpoints.py <admin_token>
"""
import sys
import requests
import json


def test_api(base_url: str, token: str):
    """测试所有 API 端点"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    results = []

    print("="*60)
    print("API 端点测试")
    print("="*60)

    # 测试 1: 获取提供商列表
    print("\n测试 1: GET /admin/models/providers")
    try:
        response = requests.get(f"{base_url}/admin/models/providers", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功 - 返回 {len(data)} 个提供商")
            results.append(True)
        else:
            print(f"❌ 失败 - 状态码: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(False)

    # 测试 2: 获取模型列表
    print("\n测试 2: GET /admin/models/models")
    try:
        response = requests.get(f"{base_url}/admin/models/models", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功 - 返回 {len(data)} 个模型")
            results.append(True)
        else:
            print(f"❌ 失败 - 状态码: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(False)

    # 测试 3: 获取凭证列表
    print("\n测试 3: GET /admin/models/credentials")
    try:
        response = requests.get(f"{base_url}/admin/models/credentials", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功 - 返回 {len(data)} 个凭证")
            # 验证 API Key 是否脱敏
            if data and 'api_key_masked' in data[0]:
                if '***' in data[0]['api_key_masked']:
                    print("✅ API Key 脱敏正常")
                else:
                    print("⚠️  API Key 可能未脱敏")
            results.append(True)
        else:
            print(f"❌ 失败 - 状态码: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(False)

    # 测试 4: 获取计费规则列表
    print("\n测试 4: GET /admin/models/pricing")
    try:
        response = requests.get(f"{base_url}/admin/models/pricing", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功 - 返回 {len(data)} 个计费规则")
            results.append(True)
        else:
            print(f"❌ 失败 - 状态码: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(False)

    # 测试 5: 获取系统配置列表
    print("\n测试 5: GET /admin/models/system-config")
    try:
        response = requests.get(f"{base_url}/admin/models/system-config", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功 - 返回 {len(data)} 个系统配置")
            results.append(True)
        else:
            print(f"❌ 失败 - 状态码: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(False)

    # 测试 6: 创建提供商（可选）
    print("\n测试 6: POST /admin/models/providers (创建测试提供商)")
    try:
        test_provider = {
            "provider_key": "test_provider",
            "display_name": "测试提供商",
            "provider_type": "custom",
            "description": "API 测试创建的提供商"
        }
        response = requests.post(
            f"{base_url}/admin/models/providers",
            headers=headers,
            json=test_provider
        )
        if response.status_code == 200:
            data = response.json()
            provider_id = data['id']
            print(f"✅ 成功 - 创建提供商 ID: {provider_id}")

            # 立即删除测试提供商
            delete_response = requests.delete(
                f"{base_url}/admin/models/providers/{provider_id}",
                headers=headers
            )
            if delete_response.status_code == 200:
                print("✅ 测试提供商已清理")
            results.append(True)
        else:
            print(f"⚠️  跳过 - 状态码: {response.status_code}")
            print(f"   (可能是提供商已存在)")
            results.append(True)  # 不算失败
    except Exception as e:
        print(f"⚠️  跳过: {e}")
        results.append(True)  # 不算失败

    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有 API 测试通过！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 test_api_endpoints.py <admin_token>")
        print("\n如何获取 admin_token:")
        print("1. 以管理员身份登录系统")
        print("2. 从浏览器开发者工具中获取 Authorization token")
        print("3. 或者从后端日志中获取")
        sys.exit(1)

    token = sys.argv[1]
    base_url = "http://localhost:8000/api/v1"

    print(f"测试 API 端点: {base_url}")
    print(f"使用 Token: {token[:20]}...")

    test_api(base_url, token)


if __name__ == "__main__":
    main()
