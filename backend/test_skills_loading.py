#!/usr/bin/env python3
"""测试 Skills 加载"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ai.skills.skill_loader import SkillLoader

def test_skills_loading():
    """测试 Skills 是否正确加载"""
    print("=" * 60)
    print("测试 Skills 加载")
    print("=" * 60)

    # 创建 SkillLoader 实例
    loader = SkillLoader()

    # 获取所有 Skill 名称
    skill_names = loader.list_skill_names()

    print(f"\n已加载的 Skills 数量: {len(skill_names)}")
    print("\nSkills 列表:")
    for name in sorted(skill_names):
        skill = loader.get_skill(name)
        print(f"  - {name}: {skill.description}")

    # 检查关键 Skills
    print("\n" + "=" * 60)
    print("检查关键 Skills")
    print("=" * 60)

    key_skills = ["breakdown_aligner", "webtoon_aligner"]

    for skill_name in key_skills:
        skill = loader.get_skill(skill_name)
        if skill:
            print(f"\n✅ {skill_name} 已加载")
            print(f"   描述: {skill.description}")
        else:
            print(f"\n❌ {skill_name} 未加载")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_skills_loading()
