#!/usr/bin/env python3
"""测试简化的 Skill 管理系统

测试内容：
1. 创建一个简单的 Skill
2. 测试执行 Skill
3. 验证结果
"""
import requests
import json
import time

# 配置
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = None  # 需要先登录获取

def login():
    """登录获取 token"""
    global TOKEN
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print("✓ 登录成功")
        return True
    else:
        print(f"✗ 登录失败: {response.text}")
        return False

def get_headers():
    """获取请求头"""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

def create_test_skill():
    """创建测试 Skill"""
    skill_data = {
        "name": "test_simple_extraction",
        "display_name": "测试提取",
        "description": "一个简单的测试 Skill，用于提取文本中的关键词",
        "category": "breakdown",
        "is_template_based": True,
        "prompt_template": """你是一个文本分析助手。请从以下文本中提取关键词：

{text}

请以 JSON 数组格式返回关键词列表：
["关键词1", "关键词2", "关键词3"]

只返回 JSON，不要其他内容。
""",
        "input_schema": {
            "text": {
                "type": "string",
                "description": "要分析的文本"
            }
        },
        "output_schema": {
            "type": "array",
            "items": {"type": "string"}
        },
        "model_config": {
            "temperature": 0.3,
            "max_tokens": 500
        },
        "example_input": {
            "text": "人工智能和机器学习正在改变世界，深度学习是其中的关键技术。"
        },
        "example_output": ["人工智能", "机器学习", "深度学习"],
        "visibility": "public"
    }

    response = requests.post(
        f"{BASE_URL}/skills",
        headers=get_headers(),
        json=skill_data
    )

    if response.status_code == 200:
        skill = response.json()
        print(f"✓ 创建 Skill 成功: {skill['id']}")
        return skill
    else:
        print(f"✗ 创建 Skill 失败: {response.text}")
        return None

def list_skills():
    """列出所有 Skills"""
    response = requests.get(
        f"{BASE_URL}/skills",
        headers=get_headers()
    )

    if response.status_code == 200:
        skills = response.json()
        print(f"✓ 获取 Skills 列表成功，共 {len(skills)} 个")
        for skill in skills[:5]:  # 只显示前5个
            print(f"  - {skill['display_name']} ({skill['name']})")
        return skills
    else:
        print(f"✗ 获取 Skills 列表失败: {response.text}")
        return []

def test_skill(skill_id):
    """测试 Skill 执行"""
    test_data = {
        "inputs": {
            "text": "Python 是一种流行的编程语言，广泛应用于数据科学、人工智能和 Web 开发领域。"
        }
    }

    print(f"\n测试 Skill: {skill_id}")
    print(f"输入: {test_data['inputs']['text']}")

    response = requests.post(
        f"{BASE_URL}/skills/{skill_id}/test",
        headers=get_headers(),
        json=test_data
    )

    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            print(f"✓ 测试成功")
            print(f"  执行时间: {result['execution_time']:.2f}s")
            print(f"  结果: {json.dumps(result['result'], ensure_ascii=False, indent=2)}")
            return True
        else:
            print(f"✗ 测试失败: {result['error']}")
            return False
    else:
        print(f"✗ 测试请求失败: {response.text}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("简化 Skill 管理系统测试")
    print("=" * 60)

    # 1. 登录
    print("\n[1] 登录...")
    if not login():
        print("登录失败，退出测试")
        return

    # 2. 列出现有 Skills
    print("\n[2] 列出现有 Skills...")
    skills = list_skills()

    # 3. 创建测试 Skill
    print("\n[3] 创建测试 Skill...")
    skill = create_test_skill()
    if not skill:
        print("创建失败，退出测试")
        return

    # 4. 测试执行
    print("\n[4] 测试 Skill 执行...")
    test_skill(skill["id"])

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
