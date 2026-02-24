"""测试剧本格式验证逻辑"""
import sys
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

from app.tasks.script_tasks import calculate_word_count


def test_structure_validation():
    """测试 structure 完整性验证"""
    print("=" * 60)
    print("测试 1: structure 完整性验证")
    print("=" * 60)

    # 完整的 structure
    valid_structure = {
        "opening": {"content": "...", "word_count": 120},
        "development": {"content": "...", "word_count": 180},
        "climax": {"content": "...", "word_count": 220},
        "hook": {"content": "...", "word_count": 130}
    }

    required_sections = ["opening", "development", "climax", "hook"]
    missing_sections = [s for s in required_sections if s not in valid_structure]

    if not missing_sections:
        print("✅ 完整的 structure 验证通过")
    else:
        print(f"❌ 缺少段落: {missing_sections}")

    # 不完整的 structure
    invalid_structure = {
        "opening": {"content": "...", "word_count": 120},
        "development": {"content": "...", "word_count": 180}
    }

    missing_sections = [s for s in required_sections if s not in invalid_structure]

    if missing_sections:
        print(f"✅ 不完整的 structure 正确检测到缺少: {missing_sections}")
    else:
        print("❌ 未能检测到不完整的 structure")

    print()


def test_word_count_calculation():
    """测试字数计算"""
    print("=" * 60)
    print("测试 2: 字数计算")
    print("=" * 60)

    test_cases = [
        {
            "name": "完整剧本",
            "script": """【起】开场冲突
※ 酒店大堂（日）
△ 林浩站在大堂中央。
林浩："陈总，您的账目有问题。"
【特效：紧张气氛】

【承】推进发展
※ 公司会议室（日）
△ 林浩展示证据。
林浩："这是证据。"

【转】反转高潮
※ 酒店大堂（日）
△ 陈总跪地求饶。
陈总："我错了！"

【钩】悬念结尾
※ 地下停车场（夜）
△ 神秘女子出现。
神秘女子："你以为结束了？"
【卡黑】""",
            "expected_range": (80, 120)
        },
        {
            "name": "只有对话",
            "script": '林浩："你好。"\n陈总："你好。"\n林浩："再见。"\n陈总："再见。"',
            "expected_range": (16, 20)
        },
        {
            "name": "空字符串",
            "script": "",
            "expected_range": (0, 0)
        }
    ]

    for case in test_cases:
        word_count = calculate_word_count(case["script"])
        min_expected, max_expected = case["expected_range"]

        if min_expected <= word_count <= max_expected:
            print(f"✅ {case['name']}: {word_count} 字 (预期 {min_expected}-{max_expected})")
        else:
            print(f"❌ {case['name']}: {word_count} 字 (预期 {min_expected}-{max_expected})")

    print()


def test_scenes_and_characters():
    """测试场景和角色提取"""
    print("=" * 60)
    print("测试 3: 场景和角色提取")
    print("=" * 60)

    # 模拟 LLM 输出
    script_result = {
        "scenes": ["酒店大堂", "公司会议室", "地下停车场"],
        "characters": ["林浩", "陈总", "神秘女子"]
    }

    scenes = script_result.get("scenes", [])
    characters = script_result.get("characters", [])

    if scenes:
        print(f"✅ 场景列表: {scenes} ({len(scenes)} 个)")
    else:
        print("⚠️  场景列表为空")

    if characters:
        print(f"✅ 角色列表: {characters} ({len(characters)} 个)")
    else:
        print("⚠️  角色列表为空")

    print()


def test_ending_marker():
    """测试结尾标记验证"""
    print("=" * 60)
    print("测试 4: 结尾标记验证")
    print("=" * 60)

    test_cases = [
        {
            "name": "有【卡黑】标记",
            "script": "剧本内容...\n【卡黑】",
            "has_marker": True
        },
        {
            "name": "无【卡黑】标记",
            "script": "剧本内容...",
            "has_marker": False
        }
    ]

    for case in test_cases:
        has_marker = "【卡黑】" in case["script"]

        if has_marker == case["has_marker"]:
            status = "✅" if has_marker else "⚠️ "
            print(f"{status} {case['name']}: {'有' if has_marker else '无'}【卡黑】标记")
        else:
            print(f"❌ {case['name']}: 检测错误")

    print()


def test_json_format():
    """测试 JSON 格式"""
    print("=" * 60)
    print("测试 5: JSON 格式验证")
    print("=" * 60)

    # 模拟 LLM 输出的 JSON
    script_result = {
        "episode_number": 1,
        "title": "第1集：真相揭露",
        "word_count": 650,
        "structure": {
            "opening": {
                "content": "※ 酒店大堂（日）\n△ 林浩站在大堂中央。\n林浩：\"陈总，您的账目有问题。\"",
                "word_count": 120
            },
            "development": {
                "content": "※ 公司会议室（日）\n△ 林浩展示证据。",
                "word_count": 180
            },
            "climax": {
                "content": "※ 酒店大堂（日）\n△ 陈总跪地求饶。",
                "word_count": 220
            },
            "hook": {
                "content": "※ 地下停车场（夜）\n△ 神秘女子出现。\n【卡黑】",
                "word_count": 130
            }
        },
        "full_script": "【起】开场冲突\n※ 酒店大堂（日）\n...\n【卡黑】",
        "scenes": ["酒店大堂", "公司会议室", "地下停车场"],
        "characters": ["林浩", "陈总", "神秘女子"],
        "hook_type": "悬念开场"
    }

    # 验证必需字段
    required_fields = ["episode_number", "title", "word_count", "structure",
                      "full_script", "scenes", "characters", "hook_type"]

    missing_fields = [f for f in required_fields if f not in script_result]

    if not missing_fields:
        print("✅ 所有必需字段都存在")
    else:
        print(f"❌ 缺少字段: {missing_fields}")

    # 验证 structure 字段
    structure = script_result.get("structure", {})
    required_sections = ["opening", "development", "climax", "hook"]
    missing_sections = [s for s in required_sections if s not in structure]

    if not missing_sections:
        print("✅ structure 包含所有必需段落")
    else:
        print(f"❌ structure 缺少段落: {missing_sections}")

    # 验证每个段落的字段
    all_sections_valid = True
    for section in required_sections:
        if section in structure:
            section_data = structure[section]
            if "content" not in section_data or "word_count" not in section_data:
                print(f"❌ {section} 段落缺少 content 或 word_count 字段")
                all_sections_valid = False

    if all_sections_valid:
        print("✅ 所有段落都包含 content 和 word_count 字段")

    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("剧本格式验证测试套件")
    print("=" * 60)
    print()

    test_structure_validation()
    test_word_count_calculation()
    test_scenes_and_characters()
    test_ending_marker()
    test_json_format()

    print("=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
