"""
数据迁移脚本：将 ai_models 数据迁移到 model_configs 表

问题背景：
- plot_breakdowns.model_config_id 字段外键指向 model_configs 表
- 但当前实际存储的是 ai_models 表的 ID
- 需要创建对应的 model_config 记录并更新外键

使用方法：
    python -m app.scripts.migrate_model_configs_to_db

执行前提：
    1. 数据库迁移已应用（新增了 model_config_id 字段）
    2. 数据库连接配置正确
"""
import sys
import uuid
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import engine, SyncSessionLocal
from app.models.ai_model import AIModel
from app.models.model_config import ModelConfig
from app.models.plot_breakdown import PlotBreakdown


def get_provider_name(provider_id: str, db: Session) -> str:
    """获取提供商名称"""
    from app.models.ai_model_provider import AIModelProvider
    provider = db.query(AIModelProvider).filter(AIModelProvider.id == provider_id).first()
    return provider.display_name if provider else "unknown"


def migrate_ai_models_to_model_configs():
    """将 ai_models 数据迁移到 model_configs 表"""

    db = SyncSessionLocal()
    try:
        print("=" * 60)
        print("开始迁移 ai_models 到 model_configs")
        print("=" * 60)

        # 1. 获取所有 ai_models
        ai_models = db.query(AIModel).all()
        print(f"\n找到 {len(ai_models)} 个 AI 模型")

        # 2. 获取已有的 model_configs
        existing_configs = db.query(ModelConfig).all()
        existing_map = {row.id: row for row in existing_configs}
        print(f"已有 {len(existing_configs)} 个 model_config 记录")

        # 3. 创建映射：ai_model_id -> model_config_id
        id_mapping = {}

        for ai_model in ai_models:
            # 检查是否已存在对应的 model_config
            if ai_model.id in existing_map:
                print(f"  跳过 {ai_model.model_key}（已存在）")
                id_mapping[ai_model.id] = ai_model.id
                continue

            # 获取提供商名称
            provider_name = get_provider_name(ai_model.provider_id, db)

            # 根据提供商确定 config_type
            if "breakdown" in ai_model.model_key.lower():
                config_type = "breakdown"
            elif "script" in ai_model.model_key.lower():
                config_type = "script"
            else:
                config_type = "general"

            # 创建新的 model_config
            model_config = ModelConfig(
                id=ai_model.id,  # 使用相同的 ID
                user_id=None,  # 系统级别的配置
                project_id=None,  # 系统级别的配置
                config_type=config_type,
                model_provider=provider_name,
                model_name=ai_model.display_name,
                parameters={
                    "max_tokens": ai_model.max_tokens,
                    "temperature": float(ai_model.temperature_default) if ai_model.temperature_default else 0.7,
                    "supports_streaming": ai_model.supports_streaming,
                    "supports_function_calling": ai_model.supports_function_calling,
                },
                is_default=ai_model.is_default,
                is_active=ai_model.is_enabled,
            )

            db.add(model_config)
            id_mapping[ai_model.id] = ai_model.id
            print(f"  创建 {ai_model.model_key} -> model_config")

        # 4. 提交第一阶段：创建 model_configs
        print("\n提交 model_configs 创建...")
        db.commit()
        print("  完成！")

        # 5. 更新 plot_breakdowns 表中的 model_config_id
        print("\n更新 plot_breakdowns 表...")

        # 统计需要更新的记录
        breakdowns = db.query(PlotBreakdown).filter(
            PlotBreakdown.ai_model_id.isnot(None)
        ).all()

        updated_count = 0
        for bd in breakdowns:
            if bd.ai_model_id and bd.ai_model_id in id_mapping:
                # ai_model_id 已存在，直接使用
                # model_config_id 应该指向同一个 ID（因为 model_configs 已创建）
                if bd.model_config_id is None:
                    bd.model_config_id = id_mapping[bd.ai_model_id]
                    updated_count += 1

        print(f"  更新了 {updated_count} 条记录")
        db.commit()
        print("  完成！")

        print("\n" + "=" * 60)
        print("迁移完成！")
        print(f"  - 创建了 {len(ai_models)} 个 model_config 记录")
        print(f"  - 更新了 {updated_count} 条 plot_breakdowns 记录")
        print("=" * 60)

        return True

    except Exception as e:
        db.rollback()
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def verify_migration():
    """验证迁移结果"""

    db = SyncSessionLocal()
    try:
        print("\n" + "=" * 60)
        print("验证迁移结果")
        print("=" * 60)

        # 检查 model_configs 数量
        model_config_count = db.query(ModelConfig).count()
        print(f"\nmodel_configs 数量: {model_config_count}")

        # 检查 ai_models 数量
        ai_model_count = db.query(AIModel).count()
        print(f"ai_models 数量: {ai_model_count}")

        # 检查 plot_breakdowns 中 ai_model_id 和 model_config_id 的对应关系
        from sqlalchemy import and_

        # 查找不匹配的记录
        mismatched = db.query(PlotBreakdown).filter(
            and_(
                PlotBreakdown.ai_model_id.isnot(None),
                PlotBreakdown.model_config_id.is_(None)
            )
        ).count()

        if mismatched > 0:
            print(f"\n⚠️  警告: 有 {mismatched} 条记录的 model_config_id 为空")
        else:
            print("\n✅ 所有记录的 model_config_id 都已正确填充")

        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    # 执行迁移
    success = migrate_ai_models_to_model_configs()

    if success:
        # 验证结果
        verify_migration()

        print("\n✅ 迁移脚本执行成功！")
        print("\n下一步：")
        print("  1. 确保数据库迁移已应用")
        print("  2. 重启 Celery worker")
        print("  3. 验证新任务能正常保存数据")
    else:
        print("\n❌ 迁移失败，请检查错误信息")
        sys.exit(1)
