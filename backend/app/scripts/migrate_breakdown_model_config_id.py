"""迁移脚本：补齐 PlotBreakdown 的 model_config_id 字段

功能：
- 从 AITask.config 中提取 model_config_id
- 更新 PlotBreakdown 表中 model_config_id 为 NULL 的历史记录

执行方式：
    python -m app.scripts.migrate_breakdown_model_config_id

注意：此脚本可安全重复执行，已填充的记录不会重复更新。
"""
import sys
import uuid
from datetime import datetime

# 确保在应用上下文中执行
from app.core.database import SyncSessionLocal, engine
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown


def migrate_model_config_id():
    """迁移：补齐 PlotBreakdown 的 model_config_id"""
    db = SyncSessionLocal()

    try:
        updated_count = 0
        skipped_count = 0
        error_count = 0

        # 查询所有 model_config_id 为 NULL 的 PlotBreakdown 记录
        breakdowns = db.query(PlotBreakdown).filter(
            PlotBreakdown.model_config_id == None
        ).all()

        print(f"找到 {len(breakdowns)} 条需要迁移的 PlotBreakdown 记录\n")

        for breakdown in breakdowns:
            model_config_id = None
            task = None

            # 优先从关联的 AITask 获取 model_config_id
            if breakdown.task_id:
                task = db.query(AITask).filter(
                    AITask.id == breakdown.task_id
                ).first()

            if task and task.config:
                model_config_id = task.config.get("model_config_id")

            if model_config_id:
                # 确保是有效的 UUID 格式
                try:
                    uuid.UUID(model_config_id)
                    breakdown.model_config_id = model_config_id
                    updated_count += 1
                    print(f"  ✓ PlotBreakdown {breakdown.id}: "
                          f"从 Task {breakdown.task_id} 获取 model_config_id={model_config_id[:8]}...")
                except ValueError:
                    print(f"  ✗ PlotBreakdown {breakdown.id}: "
                          f"model_config_id 格式无效: {model_config_id}")
                    error_count += 1
            else:
                # 如果没有关联任务或任务没有配置，尝试从 ai_model_id 推断
                if breakdown.ai_model_id:
                    breakdown.model_config_id = breakdown.ai_model_id
                    updated_count += 1
                    print(f"  ✓ PlotBreakdown {breakdown.id}: "
                          f"从 ai_model_id 推断 model_config_id={str(breakdown.ai_model_id)[:8]}...")
                else:
                    skipped_count += 1
                    print(f"  - PlotBreakdown {breakdown.id}: "
                          f"无任务关联，跳过")

        # 提交事务
        if updated_count > 0:
            db.commit()
            print(f"\n✓ 成功更新 {updated_count} 条记录")
        else:
            print("\n无需更新的记录")

        if skipped_count > 0:
            print(f"- 跳过 {skipped_count} 条无任务关联的记录")

        if error_count > 0:
            print(f"✗ {error_count} 条记录 model_config_id 格式无效")

        return updated_count, skipped_count, error_count

    except Exception as e:
        db.rollback()
        print(f"\n✗ 迁移失败: {e}")
        raise
    finally:
        db.close()


def verify_migration():
    """验证迁移结果"""
    db = SyncSessionLocal()

    try:
        # 统计各字段的填充情况
        total = db.query(PlotBreakdown).count()
        with_model_config = db.query(PlotBreakdown).filter(
            PlotBreakdown.model_config_id != None
        ).count()
        without_model_config = total - with_model_config

        print(f"\n=== 迁移后统计 ===")
        print(f"PlotBreakdown 总数: {total}")
        print(f"  - 有 model_config_id: {with_model_config} ({with_model_config/total*100:.1f}%)")
        print(f"  - 无 model_config_id: {without_model_config} ({without_model_config/total*100:.1f}%)")

        return with_model_config, without_model_config

    finally:
        db.close()


def main():
    print("=" * 60)
    print("PlotBreakdown model_config_id 迁移脚本")
    print("=" * 60)
    print(f"执行时间: {datetime.now().isoformat()}")
    print()

    updated, skipped, error = migrate_model_config_id()
    verify_migration()

    print("\n" + "=" * 60)
    if error == 0:
        print("✓ 迁移完成")
    else:
        print(f"⚠ 迁移完成，但有 {error} 条记录格式错误")
    print("=" * 60)

    return 0 if error == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
