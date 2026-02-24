#!/usr/bin/env python3
"""测试拆分规则管理 API"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 从环境变量或配置文件获取管理员 token
# 这里需要先登录获取 token
def get_admin_token():
    """获取管理员 token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.status_code}")
        print(response.text)
        return None

def test_split_rules():
    """测试拆分规则 API"""
    token = get_admin_token()
    if not token:
        print("❌ 无法获取管理员 token")
        return

    headers = {"Authorization": f"Bearer {token}"}

    print("\n" + "="*60)
    print("测试拆分规则管理 API")
    print("="*60)

    # 1. 初始化默认规则
    print("\n1️⃣  初始化默认规则...")
    response = requests.post(
        f"{BASE_URL}/admin/split-rules/init-defaults",
        headers=headers
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['message']}")
    else:
        print(f"❌ 失败: {response.text}")

    # 2. 获取所有规则
    print("\n2️⃣  获取所有规则...")
    response = requests.get(
        f"{BASE_URL}/admin/split-rules",
        headers=headers
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        rules = response.json()
        print(f"✅ 共 {len(rules)} 条规则:")
        for rule in rules:
            status = "✓ 启用" if rule['is_active'] else "✗ 禁用"
            default = " [默认]" if rule['is_default'] else ""
            print(f"  - {rule['display_name']} ({rule['name']}) {status}{default}")
    else:
        print(f"❌ 失败: {response.text}")

    # 3. 创建自定义规则
    print("\n3️⃣  创建自定义规则...")
    new_rule = {
        "name": "test_custom",
        "display_name": "测试自定义规则",
        "pattern": r"第\d+节",
        "pattern_type": "regex",
        "example": "第1节 开始\n第2节 继续",
        "is_default": False,
        "is_active": True
    }
    response = requests.post(
        f"{BASE_URL}/admin/split-rules",
        headers=headers,
        json=new_rule
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        created = response.json()
        rule_id = created['id']
        print(f"✅ 创建成功，ID: {rule_id}")

        # 4. 更新规则
        print("\n4️⃣  更新规则...")
        update_data = {
            "display_name": "测试自定义规则（已更新）",
            "is_active": False
        }
        response = requests.put(
            f"{BASE_URL}/admin/split-rules/{rule_id}",
            headers=headers,
            json=update_data
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ 更新成功")
        else:
            print(f"❌ 失败: {response.text}")

        # 5. 删除规则
        print("\n5️⃣  删除规则...")
        response = requests.delete(
            f"{BASE_URL}/admin/split-rules/{rule_id}",
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ 删除成功")
        else:
            print(f"❌ 失败: {response.text}")
    else:
        print(f"❌ 创建失败: {response.text}")

    # 6. 测试用户端接口
    print("\n6️⃣  测试用户端获取规则...")
    response = requests.get(
        f"{BASE_URL}/projects/split-rules",
        headers=headers
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        rules = response.json()
        print(f"✅ 用户可见规则 {len(rules)} 条:")
        for rule in rules:
            print(f"  - {rule['display_name']}")
    else:
        print(f"❌ 失败: {response.text}")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_split_rules()
