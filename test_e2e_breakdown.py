#!/usr/bin/env python3
"""端到端测试：简化系统集成到拆解流程

测试内容：
1. 系统初始化（内置 Skills 和 Agents）
2. 创建测试项目和批次
3. 执行拆解任务
4. 验证结果
"""
import requests
import json
import time
import sys

# 配置
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = None

def login():
    """登录获取 token"""
    global TOKEN
    print("=" * 60)
    print("1. 登录系统")
    print("=" * 60)

    # 使用表单数据格式登录
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin",
        "password": "admin"
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

def check_builtin_skills():
    """检查内置 Skills 是否存在"""
    print("\n" + "=" * 60)
    print("2. 检查内置 Skills")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/skills", headers=get_headers())

    if response.status_code == 200:
        skills = response.json()
        builtin_skills = [s for s in skills if s['is_builtin']]

        print(f"✓ 找到 {len(builtin_skills)} 个内置 Skills:")
        for skill in builtin_skills:
            print(f"  - {skill['display_name']} ({skill['name']})")

        # 检查必需的 Skills
        required_skills = [
            'conflict_extraction',
            'plot_hook_identification',
            'character_analysis',
            'scene_identification',
            'emotion_extraction',
            'episode_planning'
        ]

        skill_names = [s['name'] for s in builtin_skills]
        missing = [s for s in required_skills if s not in skill_names]

        if missing:
            print(f"\n⚠ 缺少必需的 Skills: {missing}")
            return False

        print("\n✓ 所有必需的 Skills 都已就绪")
        return True
    else:
        print(f"✗ 获取 Skills 失败: {response.text}")
        return False

def check_builtin_agents():
    """检查内置 Agents 是否存在"""
    print("\n" + "=" * 60)
    print("3. 检查内置 Agents")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/simple-agents", headers=get_headers())

    if response.status_code == 200:
        agents = response.json()
        builtin_agents = [a for a in agents if a['is_builtin']]

        print(f"✓ 找到 {len(builtin_agents)} 个内置 Agents:")
        for agent in builtin_agents:
            print(f"  - {agent['display_name']} ({agent['name']})")
            print(f"    步骤数: {len(agent['workflow']['steps'])}")

        # 检查 breakdown_agent
        breakdown_agent = next((a for a in builtin_agents if a['name'] == 'breakdown_agent'), None)

        if not breakdown_agent:
            print("\n✗ 缺少 breakdown_agent")
            return False

        print("\n✓ breakdown_agent 已就绪")
        return True
    else:
        print(f"✗ 获取 Agents 失败: {response.text}")
        return False

def create_test_project():
    """创建测试项目"""
    print("\n" + "=" * 60)
    print("4. 创建测试项目")
    print("=" * 60)

    # 检查是否已存在测试项目
    response = requests.get(f"{BASE_URL}/projects", headers=get_headers())
    if response.status_code == 200:
        projects = response.json()
        test_project = next((p for p in projects if p['name'] == 'E2E测试项目'), None)
        if test_project:
            print(f"✓ 测试项目已存在: {test_project['id']}")
            return test_project['id']

    # 创建新项目
    project_data = {
        "name": "E2E测试项目",
        "description": "端到端测试用项目",
        "novel_type": "玄幻"
    }

    response = requests.post(
        f"{BASE_URL}/projects",
        headers=get_headers(),
        json=project_data
    )

    if response.status_code == 200:
        project = response.json()
        print(f"✓ 创建项目成功: {project['id']}")
        return project['id']
    else:
        print(f"✗ 创建项目失败: {response.text}")
        return None

def create_test_batch(project_id):
    """创建测试批次"""
    print("\n" + "=" * 60)
    print("5. 创建测试批次")
    print("=" * 60)

    # 创建批次
    batch_data = {
        "project_id": project_id,
        "start_chapter": 1,
        "end_chapter": 3,
        "chapters": [
            {
                "chapter_number": 1,
                "title": "重生",
                "content": "张三睁开眼睛，发现自己回到了十年前。他激动不已，这是上天给他的第二次机会。"
            },
            {
                "chapter_number": 2,
                "title": "决心",
                "content": "张三决定改变命运。他要利用前世的记忆，避免所有的错误，走向人生巅峰。"
            },
            {
                "chapter_number": 3,
                "title": "行动",
                "content": "张三开始行动。他首先要做的，就是阻止那场即将发生的悲剧。"
            }
        ]
    }

    response = requests.post(
        f"{BASE_URL}/projects/{project_id}/create-batches",
        headers=get_headers(),
        json=batch_data
    )

    if response.status_code == 200:
        batch = response.json()
        print(f"✓ 创建批次成功: {batch['id']}")
        return batch['id']
    else:
        print(f"✗ 创建批次失败: {response.text}")
        return None

def start_breakdown(batch_id):
    """开始拆解任务"""
    print("\n" + "=" * 60)
    print("6. 开始拆解任务")
    print("=" * 60)

    breakdown_data = {
        "batch_id": batch_id,
        "model_config_id": None,  # 使用默认模型
        "enable_qa": False  # 暂时禁用质检
    }

    response = requests.post(
        f"{BASE_URL}/breakdown/start",
        headers=get_headers(),
        json=breakdown_data
    )

    if response.status_code == 200:
        task = response.json()
        task_id = task['task_id']
        print(f"✓ 拆解任务已启动: {task_id}")
        return task_id
    else:
        print(f"✗ 启动拆解失败: {response.text}")
        return None

def wait_for_task(task_id, timeout=300):
    """等待任务完成"""
    print("\n等待任务完成...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(
            f"{BASE_URL}/breakdown/tasks/{task_id}",
            headers=get_headers()
        )

        if response.status_code == 200:
            task = response.json()
            status = task['status']
            progress = task.get('progress', 0)

            print(f"  状态: {status}, 进度: {progress}%", end='\r')

            if status == 'completed':
                print("\n✓ 任务完成！")
                return True
            elif status == 'failed':
                print(f"\n✗ 任务失败: {task.get('error_message')}")
                return False

        time.sleep(2)

    print("\n✗ 任务超时")
    return False

def verify_results(batch_id):
    """验证拆解结果"""
    print("\n" + "=" * 60)
    print("7. 验证拆解结果")
    print("=" * 60)

    response = requests.get(
        f"{BASE_URL}/breakdown/batches/{batch_id}/result",
        headers=get_headers()
    )

    if response.status_code == 200:
        result = response.json()

        print("✓ 拆解结果:")
        print(f"  - 冲突数: {len(result.get('conflicts', []))}")
        print(f"  - 剧情钩子数: {len(result.get('plot_hooks', []))}")
        print(f"  - 角色数: {len(result.get('characters', []))}")
        print(f"  - 场景数: {len(result.get('scenes', []))}")
        print(f"  - 情感数: {len(result.get('emotions', []))}")
        print(f"  - 剧集数: {len(result.get('episodes', []))}")

        # 检查是否有数据
        if all([
            result.get('conflicts'),
            result.get('plot_hooks'),
            result.get('characters'),
            result.get('scenes'),
            result.get('emotions'),
            result.get('episodes')
        ]):
            print("\n✓ 所有数据都已生成")
            return True
        else:
            print("\n⚠ 部分数据缺失")
            return False
    else:
        print(f"✗ 获取结果失败: {response.text}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("简化系统端到端测试")
    print("=" * 60)

    # 1. 登录
    if not login():
        sys.exit(1)

    # 2. 检查内置 Skills
    if not check_builtin_skills():
        print("\n⚠ 内置 Skills 未就绪，请先启动后端服务")
        sys.exit(1)

    # 3. 检查内置 Agents
    if not check_builtin_agents():
        print("\n⚠ 内置 Agents 未就绪，请先启动后端服务")
        sys.exit(1)

    # 4. 创建测试项目
    project_id = create_test_project()
    if not project_id:
        sys.exit(1)

    # 5. 创建测试批次
    batch_id = create_test_batch(project_id)
    if not batch_id:
        sys.exit(1)

    # 6. 开始拆解
    task_id = start_breakdown(batch_id)
    if not task_id:
        sys.exit(1)

    # 7. 等待完成
    if not wait_for_task(task_id):
        sys.exit(1)

    # 8. 验证结果
    if not verify_results(batch_id):
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ 端到端测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    main()
