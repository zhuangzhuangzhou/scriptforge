#!/usr/bin/env python3
"""测试同步数据库连接"""
from app.core.database import SyncSessionLocal
from app.models.user import User
from app.models.ai_task import AITask

def test_sync_connection():
    """测试同步数据库连接"""
    print("🔌 测试同步数据库连接...")
    
    db = SyncSessionLocal()
    try:
        # 测试查询用户
        user = db.query(User).first()
        if user:
            print(f"✅ 成功连接数据库")
            print(f"   用户: {user.username} ({user.email})")
        else:
            print("⚠️  数据库连接成功，但没有用户")
        
        # 测试查询任务
        task_count = db.query(AITask).count()
        print(f"   任务数量: {task_count}")
        
        # 测试查询 queued 任务
        queued_count = db.query(AITask).filter(AITask.status == "queued").count()
        print(f"   排队中的任务: {queued_count}")
        
        print("\n✅ 同步数据库连接测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 同步数据库连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    test_sync_connection()
