"""验证项目模型配置迁移是否成功"""
import asyncio
from sqlalchemy import text
from app.core.database import engine


async def verify_migration():
    """验证迁移结果"""
    async with engine.connect() as conn:
        # 1. 检查列是否存在
        print("=" * 60)
        print("1. 检查 projects 表结构")
        print("=" * 60)
        
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'projects' 
                AND column_name IN ('breakdown_model_id', 'script_model_id')
            ORDER BY column_name;
        """))
        
        columns = result.fetchall()
        if columns:
            print("✅ 字段已成功添加：")
            for col in columns:
                print(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
        else:
            print("❌ 字段未找到")
            return False
        
        # 2. 检查外键约束
        print("\n" + "=" * 60)
        print("2. 检查外键约束")
        print("=" * 60)
        
        result = await conn.execute(text("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'projects'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND (tc.constraint_name LIKE '%breakdown_model%' 
                     OR tc.constraint_name LIKE '%script_model%')
            ORDER BY tc.constraint_name;
        """))
        
        constraints = result.fetchall()
        if constraints:
            print("✅ 外键约束已成功创建：")
            for constraint in constraints:
                print(f"   - {constraint[0]}: {constraint[1]} -> {constraint[2]}.{constraint[3]}")
        else:
            print("❌ 外键约束未找到")
            return False
        
        # 3. 统计项目数据
        print("\n" + "=" * 60)
        print("3. 项目数据统计")
        print("=" * 60)
        
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as total_projects,
                COUNT(breakdown_model_id) as projects_with_breakdown_model,
                COUNT(script_model_id) as projects_with_script_model
            FROM projects;
        """))
        
        stats = result.fetchone()
        print(f"   总项目数: {stats[0]}")
        print(f"   已配置拆解模型: {stats[1]}")
        print(f"   已配置剧本模型: {stats[2]}")
        
        if stats[0] > 0 and stats[1] == 0:
            print("\n⚠️  提示: 现有项目尚未配置模型，用户需要在项目设置中选择模型")
        
        # 4. 检查可用模型
        print("\n" + "=" * 60)
        print("4. 可用 AI 模型")
        print("=" * 60)
        
        result = await conn.execute(text("""
            SELECT id, display_name, model_key, is_enabled, is_default
            FROM ai_models
            WHERE is_enabled = true
            ORDER BY is_default DESC, display_name;
        """))
        
        models = result.fetchall()
        if models:
            print(f"✅ 找到 {len(models)} 个可用模型：")
            for model in models:
                default_tag = " [默认]" if model[4] else ""
                print(f"   - {model[1]} ({model[2]}){default_tag}")
                print(f"     ID: {model[0]}")
        else:
            print("⚠️  未找到可用的 AI 模型")
        
        print("\n" + "=" * 60)
        print("✅ 迁移验证完成！")
        print("=" * 60)
        
        return True


if __name__ == "__main__":
    asyncio.run(verify_migration())
