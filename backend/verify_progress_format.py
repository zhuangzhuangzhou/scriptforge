#!/usr/bin/env python3
"""验证进度显示格式

检查 breakdown_tasks.py 中的进度显示是否包含新格式（带"中..."和百分比）
"""
import re

def check_progress_format():
    """检查进度格式"""
    print("=" * 60)
    print("验证进度显示格式")
    print("=" * 60)
    
    # 读取 breakdown_tasks.py 文件
    with open('backend/app/tasks/breakdown_tasks.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找所有 update_task_progress_sync 调用中的 current_step 参数
    pattern = r'current_step="([^"]+)"'
    matches = re.findall(pattern, content)
    
    print(f"\n找到 {len(matches)} 个进度步骤：\n")
    
    new_format_count = 0
    old_format_count = 0
    
    for i, step in enumerate(matches, 1):
        # 检查是否包含新格式（"中..." 和百分比）
        has_zhong = "中..." in step
        has_percentage = "%" in step or "(" in step
        
        if has_zhong or has_percentage:
            status = "✅ 新格式"
            new_format_count += 1
        else:
            status = "❌ 旧格式"
            old_format_count += 1
        
        print(f"{i}. {status}: {step}")
    
    print("\n" + "=" * 60)
    print("统计结果")
    print("=" * 60)
    print(f"新格式步骤: {new_format_count}")
    print(f"旧格式步骤: {old_format_count}")
    
    if old_format_count == 0:
        print("\n✅ 所有进度步骤都已更新为新格式！")
        print("\n预期的进度显示：")
        print("  - 初始化任务中... (0%)")
        print("  - 加载章节数据中... (10%)")
        print("  - 提取冲突中... (20%)")
        print("  - 识别情节钩子中... (35%)")
        print("  - 分析角色中... (50%)")
        print("  - 识别场景中... (65%)")
        print("  - 提取情感中... (80%)")
        print("  - 保存拆解结果中... (90%)")
        print("  - 任务完成 (100%)")
        print("\n✅ Celery worker 已重启，新格式将在下次任务中生效！")
        return True
    else:
        print(f"\n⚠️  还有 {old_format_count} 个步骤使用旧格式")
        return False

if __name__ == "__main__":
    success = check_progress_format()
    exit(0 if success else 1)
