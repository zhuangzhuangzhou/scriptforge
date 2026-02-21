#!/usr/bin/env python3
"""
Agent 拆解流程完整测试脚本

测试范围：
1. skill_only 模式 - 纯 Skill 模式
2. agent_single 模式 - Agent 单轮 + Skill 修正
3. agent_loop 模式 - Agent 内部循环
4. 资源加载测试
5. 异常流程测试
"""
import asyncio
import aiohttp
import json
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

BASE_URL = "http://localhost:8000"


class BreakdownQATester:
    """拆解流程 QA 测试类"""

    def __init__(self):
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.batch_id: Optional[str] = None
        self.task_id: Optional[str] = None
        self.auth_headers: Dict[str, str] = {}

    async def setup(self):
        """初始化：登录并获取必要信息"""
        print("=" * 60)
        print("0. 测试环境准备")
        print("=" * 60)

        async with aiohttp.ClientSession() as session:
            # 登录
            login_data = "username=apitestuser&password=testpass123"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            async with session.post(f"{BASE_URL}/api/v1/auth/login", data=login_data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    self.token = result.get("access_token")
                    print(f"[✓] 登录成功")
                else:
                    # 注册
                    register_data = {
                        "email": "qa_test@example.com",
                        "username": "qa_test_user",
                        "password": "testpass123",
                        "full_name": "QA Test User"
                    }
                    async with session.post(f"{BASE_URL}/api/v1/auth/register", json=register_data) as resp:
                        if resp.status in [200, 201]:
                            async with session.post(f"{BASE_URL}/api/v1/auth/login", data=login_data, headers=headers) as resp:
                                result = await resp.json()
                                self.token = result.get("access_token")
                                print(f"[✓] 注册并登录成功")
                        else:
                            print(f"[✗] 登录失败")
                            return False

            self.auth_headers = {"Authorization": f"Bearer {self.token}"}

            # 获取用户信息
            async with session.get(f"{BASE_URL}/api/v1/user/me", headers=self.auth_headers) as resp:
                if resp.status == 200:
                    user = await resp.json()
                    self.user_id = user.get("id")
                    print(f"[✓] 用户 ID: {self.user_id}")

            # 获取项目列表
            async with session.get(f"{BASE_URL}/api/v1/projects", headers=self.auth_headers) as resp:
                if resp.status == 200:
                    projects = await resp.json()
                    if projects:
                        self.project_id = projects[0].get("id")
                        print(f"[✓] 项目 ID: {self.project_id}")
                    else:
                        print(f"[!] 没有项目，需要先创建项目")
                        # 创建测试项目
                        project_data = {
                            "name": "QA 测试项目",
                            "description": "自动化 QA 测试创建的项目",
                            "novel_type": "webnovel"
                        }
                        async with session.post(f"{BASE_URL}/api/v1/projects", json=project_data, headers=self.auth_headers) as resp:
                            if resp.status in [200, 201]:
                                project = await resp.json()
                                self.project_id = project.get("id")
                                print(f"[✓] 创建测试项目成功: {self.project_id}")

            # 获取可用模型
            async with session.get(f"{BASE_URL}/api/v1/admin/models", headers=self.auth_headers) as resp:
                if resp.status == 200:
                    models = await resp.json()
                    print(f"[✓] 可用模型数: {len(models)}")
                    for m in models[:3]:
                        print(f"    - {m.get('provider')}/{m.get('model_name')}")

            # 获取批次列表
            if self.project_id:
                async with session.get(f"{BASE_URL}/api/v1/projects/{self.project_id}", headers=self.auth_headers) as resp:
                    if resp.status == 200:
                        project = await resp.json()
                        batches = project.get("batches", [])
                        if batches:
                            self.batch_id = batches[0].get("id")
                            print(f"[✓] 批次 ID: {self.batch_id}")
                            print(f"[✓] 批次状态: {batches[0].get('breakdown_status')}")

            # 获取可用的拆解资源
            async with session.get(f"{BASE_URL}/api/v1/breakdown/available-configs", headers=self.auth_headers) as resp:
                if resp.status == 200:
                    configs = await resp.json()
                    print(f"[✓] 改编方法: {len(configs.get('adapt_methods', []))}")
                    print(f"[✓] 质检规则: {len(configs.get('quality_rules', []))}")
                    print(f"[✓] 输出风格: {len(configs.get('output_styles', []))}")

        return True

    async def test_skill_only_mode(self) -> Dict[str, Any]:
        """测试场景1：skill_only 模式"""
        print("\n" + "=" * 60)
        print("测试场景1：skill_only 模式")
        print("=" * 60)

        if not self.batch_id:
            return {"status": "skip", "reason": "没有可用的批次"}

        result = {
            "mode": "skill_only",
            "input": {
                "batch_id": self.batch_id,
                "execution_mode": "skill_only"
            },
            "expected": {
                "流程": "Skill → QA质检 → 结果保存",
                "qa_status": "应有值 (PASS/FAIL)",
                "qa_score": "应有值 (0-100)",
                "plot_points": "应有剧情点数据"
            },
            "actual": {},
            "status": "pending"
        }

        async with aiohttp.ClientSession() as session:
            # 启动 skill_only 模式拆解
            start_data = {
                "batch_id": self.batch_id,
                "execution_mode": "skill_only"
            }

            async with session.post(f"{BASE_URL}/api/v1/breakdown/start", json=start_data, headers=self.auth_headers) as resp:
                if resp.status == 200:
                    start_result = await resp.json()
                    self.task_id = start_result.get("task_id")
                    result["actual"]["start_response"] = start_result
                    print(f"[✓] 任务启动成功: task_id={self.task_id}")
                else:
                    error = await resp.text()
                    result["actual"]["error"] = error
                    result["status"] = "fail"
                    result["fail_reason"] = f"启动失败: {error}"
                    return result

            # 轮询任务状态
            max_wait = 300  # 最多等待5分钟
            check_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                async with session.get(f"{BASE_URL}/api/v1/breakdown/tasks/{self.task_id}", headers=self.auth_headers) as resp:
                    if resp.status == 200:
                        task_status = await resp.json()
                        status = task_status.get("status")
                        progress = task_status.get("progress", 0)
                        current_step = task_status.get("current_step", "")
                        print(f"[{'✓' if status in ['completed', 'failed', 'cancelled'] else '-'}] 任务状态: {status}, 进度: {progress}%, 步骤: {current_step[:30]}")

                        if status == "completed":
                            result["actual"]["task_status"] = task_status

                            # 获取拆解结果
                            async with session.get(f"{BASE_URL}/api/v1/breakdown/results/{self.batch_id}", headers=self.auth_headers) as resp:
                                if resp.status == 200:
                                    breakdown_result = await resp.json()
                                    result["actual"]["breakdown_result"] = {
                                        "qa_status": breakdown_result.get("qa_status"),
                                        "qa_score": breakdown_result.get("qa_score"),
                                        "plot_points_count": len(breakdown_result.get("plot_points", [])) if breakdown_result.get("plot_points") else 0,
                                        "format_version": breakdown_result.get("format_version")
                                    }
                                    print(f"[✓] 拆解结果: qa_status={breakdown_result.get('qa_status')}, qa_score={breakdown_result.get('qa_score')}, plot_points={result['actual']['breakdown_result']['plot_points_count']}")
                            break

                        elif status in ["failed", "cancelled"]:
                            result["actual"]["task_status"] = task_status
                            result["fail_reason"] = f"任务{status}: {task_status.get('error_message', '未知错误')}"
                            break

            # 验证结果
            if result["actual"].get("breakdown_result"):
                br = result["actual"]["breakdown_result"]
                if br.get("qa_status") and br.get("qa_status") != "pending":
                    result["status"] = "pass"
                    print(f"[PASS] qa_status 有值: {br.get('qa_status')}")
                if br.get("qa_score") is not None:
                    result["status"] = "pass"
                    print(f"[PASS] qa_score 有值: {br.get('qa_score')}")
                if br.get("plot_points_count", 0) > 0:
                    result["status"] = "pass"
                    print(f"[PASS] plot_points 有数据: {br.get('plot_points_count')} 个")
            elif result["status"] != "fail":
                result["status"] = "timeout"
                result["fail_reason"] = "任务超时"

        return result

    async def test_agent_single_mode(self) -> Dict[str, Any]:
        """测试场景2：agent_single 模式"""
        print("\n" + "=" * 60)
        print("测试场景2：agent_single 模式")
        print("=" * 60)

        if not self.batch_id:
            return {"status": "skip", "reason": "没有可用的批次"}

        result = {
            "mode": "agent_single",
            "input": {
                "batch_id": self.batch_id,
                "execution_mode": "agent_single"
            },
            "expected": {
                "流程": "Agent单轮 → QA质检 → 自动修正（如需要）",
                "只执行一轮": "Agent只跑1轮",
                "外部修正": "质检不通过时触发自动修正"
            },
            "actual": {},
            "status": "pending"
        }

        async with aiohttp.ClientSession() as session:
            start_data = {
                "batch_id": self.batch_id,
                "execution_mode": "agent_single"
            }

            async with session.post(f"{BASE_URL}/api/v1/breakdown/start", json=start_data, headers=self.auth_headers) as resp:
                if resp.status == 200:
                    start_result = await resp.json()
                    self.task_id = start_result.get("task_id")
                    result["actual"]["start_response"] = start_result
                    print(f"[✓] 任务启动成功: task_id={self.task_id}")
                else:
                    error = await resp.text()
                    result["actual"]["error"] = error
                    result["status"] = "fail"
                    result["fail_reason"] = f"启动失败: {error}"
                    return result

            # 轮询任务状态
            max_wait = 300
            check_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                async with session.get(f"{BASE_URL}/api/v1/breakdown/tasks/{self.task_id}", headers=self.auth_headers) as resp:
                    if resp.status == 200:
                        task_status = await resp.json()
                        status = task_status.get("status")
                        progress = task_status.get("progress", 0)
                        current_step = task_status.get("current_step", "")
                        print(f"[{'✓' if status in ['completed', 'failed', 'cancelled'] else '-'}] 任务状态: {status}, 进度: {progress}%, 步骤: {current_step[:30]}")

                        if status == "completed":
                            result["actual"]["task_status"] = task_status

                            async with session.get(f"{BASE_URL}/api/v1/breakdown/results/{self.batch_id}", headers=self.auth_headers) as resp:
                                if resp.status == 200:
                                    breakdown_result = await resp.json()
                                    result["actual"]["breakdown_result"] = {
                                        "qa_status": breakdown_result.get("qa_status"),
                                        "qa_score": breakdown_result.get("qa_score"),
                                        "plot_points_count": len(breakdown_result.get("plot_points", [])) if breakdown_result.get("plot_points") else 0,
                                        "qa_report": breakdown_result.get("qa_report")
                                    }
                                    print(f"[✓] 拆解结果: qa_status={breakdown_result.get('qa_status')}, qa_score={breakdown_result.get('qa_score')}, plot_points={result['actual']['breakdown_result']['plot_points_count']}")
                            break

                        elif status in ["failed", "cancelled"]:
                            result["actual"]["task_status"] = task_status
                            result["fail_reason"] = f"任务{status}: {task_status.get('error_message', '未知错误')}"
                            break

            if result["actual"].get("breakdown_result"):
                result["status"] = "pass"

        return result

    async def test_agent_loop_mode(self) -> Dict[str, Any]:
        """测试场景3：agent_loop 模式"""
        print("\n" + "=" * 60)
        print("测试场景3：agent_loop 模式")
        print("=" * 60)

        if not self.batch_id:
            return {"status": "skip", "reason": "没有可用的批次"}

        result = {
            "mode": "agent_loop",
            "input": {
                "batch_id": self.batch_id,
                "execution_mode": "agent_loop"
            },
            "expected": {
                "流程": "Agent内部循环（breakdown → qa → 修正，最多3轮）",
                "质检通过退出": "质检通过后退出循环",
                "最大3轮": "不超过3轮循环"
            },
            "actual": {},
            "status": "pending"
        }

        async with aiohttp.ClientSession() as session:
            start_data = {
                "batch_id": self.batch_id,
                "execution_mode": "agent_loop"
            }

            async with session.post(f"{BASE_URL}/api/v1/breakdown/start", json=start_data, headers=self.auth_headers) as resp:
                if resp.status == 200:
                    start_result = await resp.json()
                    self.task_id = start_result.get("task_id")
                    result["actual"]["start_response"] = start_result
                    print(f"[✓] 任务启动成功: task_id={self.task_id}")
                else:
                    error = await resp.text()
                    result["actual"]["error"] = error
                    result["status"] = "fail"
                    result["fail_reason"] = f"启动失败: {error}"
                    return result

            # 轮询任务状态
            max_wait = 600  # agent_loop 可能需要更长时间
            check_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                async with session.get(f"{BASE_URL}/api/v1/breakdown/tasks/{self.task_id}", headers=self.auth_headers) as resp:
                    if resp.status == 200:
                        task_status = await resp.json()
                        status = task_status.get("status")
                        progress = task_status.get("progress", 0)
                        current_step = task_status.get("current_step", "")
                        print(f"[{'✓' if status in ['completed', 'failed', 'cancelled'] else '-'}] 任务状态: {status}, 进度: {progress}%, 步骤: {current_step[:30]}")

                        if status == "completed":
                            result["actual"]["task_status"] = task_status

                            async with session.get(f"{BASE_URL}/api/v1/breakdown/results/{self.batch_id}", headers=self.auth_headers) as resp:
                                if resp.status == 200:
                                    breakdown_result = await resp.json()
                                    qa_report = breakdown_result.get("qa_report", {})
                                    result["actual"]["breakdown_result"] = {
                                        "qa_status": breakdown_result.get("qa_status"),
                                        "qa_score": breakdown_result.get("qa_score"),
                                        "plot_points_count": len(breakdown_result.get("plot_points", [])) if breakdown_result.get("plot_points") else 0,
                                        "auto_fix_attempts": qa_report.get("auto_fix_attempts") if qa_report else 0
                                    }
                                    print(f"[✓] 拆解结果: qa_status={breakdown_result.get('qa_status')}, qa_score={breakdown_result.get('qa_score')}")
                            break

                        elif status in ["failed", "cancelled"]:
                            result["actual"]["task_status"] = task_status
                            result["fail_reason"] = f"任务{status}: {task_status.get('error_message', '未知错误')}"
                            break

            if result["actual"].get("breakdown_result"):
                result["status"] = "pass"

        return result

    async def test_resource_loading(self) -> Dict[str, Any]:
        """测试场景4：资源加载测试"""
        print("\n" + "=" * 60)
        print("测试场景4：资源加载测试")
        print("=" * 60)

        if not self.batch_id:
            return {"status": "skip", "reason": "没有可用的批次"}

        result = {
            "mode": "resource_loading",
            "input": {
                "batch_id": self.batch_id,
                "resource_ids": []  # 测试不选择资源时加载默认
            },
            "expected": {
                "无resource_ids": "应加载系统默认资源",
                "有resource_ids": "应加载指定资源"
            },
            "actual": {},
            "status": "pending"
        }

        # 测试无资源ID情况
        async with aiohttp.ClientSession() as session:
            start_data = {
                "batch_id": self.batch_id,
                "execution_mode": "agent_single"
                # 不设置 resource_ids
            }

            async with session.post(f"{BASE_URL}/api/v1/breakdown/start", json=start_data, headers=self.auth_headers) as resp:
                if resp.status == 200:
                    start_result = await resp.json()
                    self.task_id = start_result.get("task_id")
                    result["actual"]["start_response"] = start_result
                    print(f"[✓] 任务启动成功（无resource_ids）: task_id={self.task_id}")
                    result["actual"]["without_resource_ids"] = "任务启动成功"
                else:
                    error = await resp.text()
                    result["actual"]["without_resource_ids_error"] = error
                    print(f"[!] 无resource_ids启动: {error}")

            # 轮询等待完成
            max_wait = 300
            check_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                async with session.get(f"{BASE_URL}/api/v1/breakdown/tasks/{self.task_id}", headers=self.auth_headers) as resp:
                    if resp.status == 200:
                        task_status = await resp.json()
                        status = task_status.get("status")
                        if status == "completed":
                            result["actual"]["without_resource_ids"] = "任务完成"
                            print(f"[✓] 无resource_ids任务完成")
                            break
                        elif status in ["failed", "cancelled"]:
                            result["actual"]["without_resource_ids"] = f"任务{status}"
                            break

        result["status"] = "pass"
        return result

    async def test_cancel_task(self) -> Dict[str, Any]:
        """测试场景5：取消任务"""
        print("\n" + "=" * 60)
        print("测试场景5：取消任务测试")
        print("=" * 60)

        if not self.batch_id:
            return {"status": "skip", "reason": "没有可用的批次"}

        result = {
            "mode": "cancel_task",
            "input": {
                "batch_id": self.batch_id,
                "execution_mode": "agent_single"
            },
            "expected": {
                "取消成功": "任务状态变为 cancelled",
                "配额返还": "应返还配额"
            },
            "actual": {},
            "status": "pending"
        }

        async with aiohttp.ClientSession() as session:
            # 启动任务
            start_data = {
                "batch_id": self.batch_id,
                "execution_mode": "agent_single"
            }

            async with session.post(f"{BASE_URL}/api/v1/breakdown/start", json=start_data, headers=self.auth_headers) as resp:
                if resp.status == 200:
                    start_result = await resp.json()
                    self.task_id = start_result.get("task_id")
                    print(f"[✓] 任务启动成功: task_id={self.task_id}")
                else:
                    error = await resp.text()
                    result["fail_reason"] = f"启动失败: {error}"
                    return result

            # 等待一小段时间让任务开始执行
            await asyncio.sleep(10)

            # 取消任务
            async with session.post(f"{BASE_URL}/api/v1/breakdown/tasks/{self.task_id}/stop", headers=self.auth_headers) as resp:
                if resp.status == 200:
                    cancel_result = await resp.json()
                    result["actual"]["cancel_response"] = cancel_result
                    print(f"[✓] 取消任务响应: {cancel_result}")
                else:
                    error = await resp.text()
                    result["actual"]["cancel_error"] = error
                    print(f"[!] 取消任务失败: {error}")

            # 检查任务状态
            await asyncio.sleep(5)

            async with session.get(f"{BASE_URL}/api/v1/breakdown/tasks/{self.task_id}", headers=self.auth_headers) as resp:
                if resp.status == 200:
                    task_status = await resp.json()
                    result["actual"]["task_status"] = task_status
                    print(f"[✓] 任务状态: {task_status.get('status')}")

                    if task_status.get("status") in ["cancelled", "cancelling"]:
                        result["status"] = "pass"
                        print(f"[PASS] 任务成功取消")

        return result

    async def test_task_progress(self) -> Dict[str, Any]:
        """测试场景6：进度报告测试"""
        print("\n" + "=" * 60)
        print("测试场景6：进度报告测试")
        print("=" * 60)

        if not self.batch_id:
            return {"status": "skip", "reason": "没有可用的批次"}

        result = {
            "mode": "progress_report",
            "input": {
                "batch_id": self.batch_id,
                "execution_mode": "agent_single"
            },
            "expected": {
                "实时更新": "进度应实时更新",
                "步骤信息": "current_step 应有具体步骤描述"
            },
            "actual": {"progress_updates": []},
            "status": "pending"
        }

        async with aiohttp.ClientSession() as session:
            start_data = {
                "batch_id": self.batch_id,
                "execution_mode": "agent_single"
            }

            async with session.post(f"{BASE_URL}/api/v1/breakdown/start", json=start_data, headers=self.auth_headers) as resp:
                if resp.status == 200:
                    start_result = await resp.json()
                    self.task_id = start_result.get("task_id")
                    print(f"[✓] 任务启动成功: task_id={self.task_id}")
                else:
                    error = await resp.text()
                    result["fail_reason"] = f"启动失败: {error}"
                    return result

            # 监控进度变化
            max_wait = 120
            check_interval = 3
            elapsed = 0
            last_progress = -1

            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                async with session.get(f"{BASE_URL}/api/v1/breakdown/tasks/{self.task_id}", headers=self.auth_headers) as resp:
                    if resp.status == 200:
                        task_status = await resp.json()
                        status = task_status.get("status")
                        progress = task_status.get("progress", 0)
                        current_step = task_status.get("current_step", "")

                        # 记录进度变化
                        if progress != last_progress:
                            result["actual"]["progress_updates"].append({
                                "time": elapsed,
                                "progress": progress,
                                "step": current_step
                            })
                            print(f"[+] 进度更新: {progress}%, 步骤: {current_step[:30]}")
                            last_progress = progress

                        if status == "completed":
                            print(f"[✓] 任务完成")
                            break
                        elif status in ["failed", "cancelled"]:
                            print(f"[!] 任务{status}")
                            break

            # 验证进度更新
            if len(result["actual"]["progress_updates"]) > 1:
                result["status"] = "pass"
                print(f"[PASS] 进度实时更新，共 {len(result['actual']['progress_updates'])} 次更新")

        return result


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Agent 拆解流程完整测试")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标地址: {BASE_URL}")

    tester = BreakdownQATester()

    # 初始化
    if not await tester.setup():
        print("[✗] 测试环境准备失败")
        return False

    # 测试结果收集
    test_results = []

    # 测试场景1：skill_only 模式
    test_results.append(await tester.test_skill_only_mode())

    # 测试场景2：agent_single 模式
    test_results.append(await tester.test_agent_single_mode())

    # 测试场景3：agent_loop 模式
    test_results.append(await tester.test_agent_loop_mode())

    # 测试场景4：资源加载
    test_results.append(await tester.test_resource_loading())

    # 测试场景5：取消任务
    test_results.append(await tester.test_cancel_task())

    # 测试场景6：进度报告
    test_results.append(await tester.test_task_progress())

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0
    pending = 0

    for result in test_results:
        status = result.get("status", "pending")
        mode = result.get("mode", "unknown")

        if status == "pass":
            passed += 1
            icon = "✓"
        elif status == "fail":
            failed += 1
            icon = "✗"
        elif status == "skip":
            skipped += 1
            icon = "-"
        else:
            pending += 1
            icon = "?"

        reason = result.get("fail_reason", "")
        print(f"[{icon}] {mode}: {status} {reason}")

    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过, {pending} 待定")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
