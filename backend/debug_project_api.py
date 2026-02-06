#!/usr/bin/env python3
"""测试 Project 相关的所有 API 接口"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 测试用的 token（需要先登录获取）
TOKEN = None


def login():
    """登录获取 token"""
    global TOKEN
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "zhuangzhuang", "password": "zhuangzhuang"}
    )
    if response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print("✅ 登录成功")
        return True
    else:
        print(f"❌ 登录失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return False


def get_headers():
    """获取请求头"""
    return {"Authorization": f"Bearer {TOKEN}"}


def test_create_project():
    """测试创建项目"""
    print("\n[1/7] 测试 POST /projects (创建项目)")
    payload = {
        "name": "测试项目",
        "novel_type": "fantasy",
        "description": "这是一个测试项目",
        "batch_size": 10
    }
    response = requests.post(
        f"{BASE_URL}/projects",
        headers=get_headers(),
        json=payload
    )
    if response.status_code == 201:
        data = response.json()
        print(f"✅ 创建成功: {data['name']} (ID: {data['id']})")
        return data['id']
    else:
        print(f"❌ 创建失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return None


def test_get_projects():
    """测试获取项目列表"""
    print("\n[2/7] 测试 GET /projects (项目列表)")
    response = requests.get(
        f"{BASE_URL}/projects",
        headers=get_headers()
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功: 共 {len(data)} 个项目")
        return True
    else:
        print(f"❌ 获取失败: {response.status_code}")
        return False


def test_get_project(project_id):
    """测试获取项目详情"""
    print(f"\n[3/7] 测试 GET /projects/{project_id} (项目详情)")
    response = requests.get(
        f"{BASE_URL}/projects/{project_id}",
        headers=get_headers()
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功: {data['name']}")
        print(f"   类型: {data['novel_type']}, 状态: {data['status']}")
        return True
    else:
        print(f"❌ 获取失败: {response.status_code}")
        return False


def test_update_project(project_id):
    """测试更新项目"""
    print(f"\n[4/7] 测试 PUT /projects/{project_id} (更新项目)")
    payload = {
        "name": "测试项目（已更新）",
        "description": "更新后的描述"
    }
    response = requests.put(
        f"{BASE_URL}/projects/{project_id}",
        headers=get_headers(),
        json=payload
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 更新成功: {data['name']}")
        return True
    else:
        print(f"❌ 更新失败: {response.status_code}")
        return False


def test_get_batches(project_id):
    """测试获取批次列表"""
    print(f"\n[5/7] 测试 GET /projects/{project_id}/batches (批次列表)")
    response = requests.get(
        f"{BASE_URL}/projects/{project_id}/batches",
        headers=get_headers()
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功: 共 {len(data)} 个批次")
        return True
    else:
        print(f"❌ 获取失败: {response.status_code}")
        return False


def test_get_logs(project_id):
    """测试获取项目日志"""
    print(f"\n[6/7] 测试 GET /projects/{project_id}/logs (项目日志)")
    response = requests.get(
        f"{BASE_URL}/projects/{project_id}/logs",
        headers=get_headers()
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功: 共 {len(data)} 条日志")
        return True
    else:
        print(f"❌ 获取失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return False


def test_delete_project(project_id):
    """测试删除项目"""
    print(f"\n[7/7] 测试 DELETE /projects/{project_id} (删除项目)")
    response = requests.delete(
        f"{BASE_URL}/projects/{project_id}",
        headers=get_headers()
    )
    if response.status_code == 200:
        print("✅ 删除成功")
        return True
    else:
        print(f"❌ 删除失败: {response.status_code}")
        return False


def main():
    """主测试流程"""
    print("=" * 60)
    print("开始测试 Project API 接口")
    print("=" * 60)

    # 登录
    if not login():
        print("\n⚠️  需要先启动后端服务并确保有测试用户")
        return

    # 创建项目
    project_id = test_create_project()
    if not project_id:
        print("\n⚠️  后续测试依赖项目创建，已跳过")
        return

    # 测试其他接口
    test_get_projects()
    test_get_project(project_id)
    test_update_project(project_id)
    test_get_batches(project_id)
    test_get_logs(project_id)
    test_delete_project(project_id)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
