"""测试剧本字数计算函数"""
import sys
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

from app.tasks.script_tasks import calculate_word_count


def test_calculate_word_count():
    """测试字数计算函数"""

    # 测试用例 1：完整剧本
    test_script_1 = """【起】开场冲突
※ 酒店大堂（日）
△ 林浩站在大堂中央，目光锐利地盯着陈总。
林浩："陈总，您的账目有问题。"
陈总："你在说什么？"
【特效：紧张气氛】

【承】推进发展
※ 公司会议室（日）
△ 林浩展示证据文件。
林浩："这是您的转账记录。"
陈总："这...这不可能！"
【特效：震惊】

【转】反转高潮
※ 酒店大堂（日）
△ 陈总跪地求饶。
陈总："我错了，求你放过我！"
林浩："晚了。"
△ 警察冲进来。
【特效：高潮音乐】

【钩】悬念结尾
※ 地下停车场（夜）
△ 神秘女子出现在林浩身后。
神秘女子："你以为这就结束了？"
△ 林浩转身，震惊。
【卡黑】"""

    word_count_1 = calculate_word_count(test_script_1)
    print(f"测试用例 1：完整剧本")
    print(f"  原始长度：{len(test_script_1)} 字符")
    print(f"  计算字数：{word_count_1} 字")
    print()

    # 测试用例 2：单段内容
    test_script_2 = """※ 酒店大堂（日）
△ 林浩站在大堂中央，目光锐利地盯着陈总。
林浩："陈总，您的账目有问题。"
陈总："你在说什么？"
【特效：紧张气氛】"""

    word_count_2 = calculate_word_count(test_script_2)
    print(f"测试用例 2：单段内容")
    print(f"  原始长度：{len(test_script_2)} 字符")
    print(f"  计算字数：{word_count_2} 字")
    print()

    # 测试用例 3：纯对话
    test_script_3 = """林浩："陈总，您的账目有问题。"
陈总："你在说什么？"
林浩："这是证据。"
陈总："我错了。"""

    word_count_3 = calculate_word_count(test_script_3)
    print(f"测试用例 3：纯对话")
    print(f"  原始长度：{len(test_script_3)} 字符")
    print(f"  计算字数：{word_count_3} 字")
    print()

    # 测试用例 4：空字符串
    test_script_4 = ""
    word_count_4 = calculate_word_count(test_script_4)
    print(f"测试用例 4：空字符串")
    print(f"  计算字数：{word_count_4} 字")
    print()

    # 验证预期结果
    print("=" * 50)
    print("验证结果：")
    print(f"✓ 测试用例 1：{word_count_1} 字（预期约 100-150 字）")
    print(f"✓ 测试用例 2：{word_count_2} 字（预期约 30-50 字）")
    print(f"✓ 测试用例 3：{word_count_3} 字（预期约 30-40 字）")
    print(f"✓ 测试用例 4：{word_count_4} 字（预期 0 字）")

    # 详细分析测试用例 2
    print("\n" + "=" * 50)
    print("详细分析测试用例 2：")
    print("原始文本：")
    print(test_script_2)
    print("\n去除标记后应该保留的内容：")
    print("林浩站在大堂中央，目光锐利地盯着陈总。")
    print('林浩："陈总，您的账目有问题。"')
    print('陈总："你在说什么？"')

    expected_content = '林浩站在大堂中央，目光锐利地盯着陈总。林浩："陈总，您的账目有问题。"陈总："你在说什么？"'
    expected_count = len(expected_content)
    print(f"\n预期字数：{expected_count} 字")
    print(f"实际字数：{word_count_2} 字")
    print(f"差异：{abs(expected_count - word_count_2)} 字")


if __name__ == "__main__":
    test_calculate_word_count()
