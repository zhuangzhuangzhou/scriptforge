#!/usr/bin/env python3
"""
验证管理端 API 修复 - 语法和导入检查
不需要数据库连接,只检查代码是否正确
"""

import ast
import sys
from pathlib import Path

def check_file_syntax(file_path: str) -> tuple[bool, str]:
    """检查文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, "语法正确"
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    except Exception as e:
        return False, f"检查失败: {e}"

def check_imports(file_path: str, required_imports: list[str]) -> tuple[bool, str]:
    """检查文件是否包含必需的导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        missing = []
        for imp in required_imports:
            if imp not in code:
                missing.append(imp)

        if missing:
            return False, f"缺少导入: {', '.join(missing)}"
        return True, "导入完整"
    except Exception as e:
        return False, f"检查失败: {e}"

def check_code_pattern(file_path: str, pattern: str, should_exist: bool = True) -> tuple[bool, str]:
    """检查代码中是否存在/不存在某个模式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        exists = pattern in code

        if should_exist and not exists:
            return False, f"未找到预期代码: {pattern}"
        elif not should_exist and exists:
            return False, f"仍存在错误代码: {pattern}"

        return True, "代码模式正确"
    except Exception as e:
        return False, f"检查失败: {e}"

def main():
    print("=" * 60)
    print("管理端 API 修复验证")
    print("=" * 60)

    tests = []

    # 测试 1: admin_core.py 语法检查
    print("\n[1/6] 检查 admin_core.py 语法...")
    result, msg = check_file_syntax("backend/app/api/v1/admin_core.py")
    tests.append(("admin_core.py 语法", result, msg))
    print(f"  {'✅' if result else '❌'} {msg}")

    # 测试 2: admin_core.py timezone 导入
    print("\n[2/6] 检查 admin_core.py timezone 导入...")
    result, msg = check_imports(
        "backend/app/api/v1/admin_core.py",
        ["from datetime import datetime, timedelta, timezone"]
    )
    tests.append(("admin_core.py timezone 导入", result, msg))
    print(f"  {'✅' if result else '❌'} {msg}")

    # 测试 3: admin_core.py 不应包含 selectinload(AITask.user)
    print("\n[3/6] 检查 admin_core.py 是否移除了错误的 user 关系...")
    result, msg = check_code_pattern(
        "backend/app/api/v1/admin_core.py",
        "selectinload(AITask.user)",
        should_exist=False
    )
    tests.append(("移除 AITask.user 关系", result, msg))
    print(f"  {'✅' if result else '❌'} {msg}")

    # 测试 4: admin_analytics.py 语法检查
    print("\n[4/6] 检查 admin_analytics.py 语法...")
    result, msg = check_file_syntax("backend/app/api/v1/admin_analytics.py")
    tests.append(("admin_analytics.py 语法", result, msg))
    print(f"  {'✅' if result else '❌'} {msg}")

    # 测试 5: admin_analytics.py timezone 导入
    print("\n[5/6] 检查 admin_analytics.py timezone 导入...")
    result, msg = check_imports(
        "backend/app/api/v1/admin_analytics.py",
        ["timezone"]
    )
    tests.append(("admin_analytics.py timezone 导入", result, msg))
    print(f"  {'✅' if result else '❌'} {msg}")

    # 测试 6: admin_core.py 不应包含 request_body/response_body 访问
    print("\n[6/6] 检查 admin_core.py 是否移除了不存在的字段访问...")
    result, msg = check_code_pattern(
        "backend/app/api/v1/admin_core.py",
        "getattr(log, 'request_body'",
        should_exist=False
    )
    tests.append(("移除 request_body 访问", result, msg))
    print(f"  {'✅' if result else '❌'} {msg}")

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result, _ in tests if result)
    total = len(tests)

    for name, result, msg in tests:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
        if not result:
            print(f"       {msg}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有检查通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个检查失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
