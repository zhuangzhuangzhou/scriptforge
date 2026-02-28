"""
基础数据导入脚本

将测试环境导出的 JSON 数据导入到生产环境数据库。

使用方法:
1. 先在测试环境运行 export_foundation_data.py 生成 JSON 文件
2. 将 JSON 文件复制到生产环境服务器
3. 在生产环境运行此脚本: python import_foundation_data.py foundation_data_export.json

注意事项:
- 导入前请确保已备份数据库
- 脚本会检查重复记录，避免重复导入
- 对于已存在的记录，可选择更新或跳过
"""
import json
import asyncio
import sys
from datetime import datetime
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


def serialize_value(value):
    """将 dict/list 类型自动序列化为 JSON 字符串，供 asyncpg 使用"""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


class DateTimeDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self._object_hook, *args, **kwargs)

    def _object_hook(self, obj):
        for key, value in obj.items():
            if isinstance(value, str):
                try:
                    obj[key] = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
        return obj


async def import_data(input_file: str, update_existing: bool = False, dry_run: bool = False):
    print(f"开始导入数据: {input_file}")
    print(f"更新已存在记录: {update_existing}")
    print(f"试运行模式: {dry_run}")
    print("-" * 50)

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f, cls=DateTimeDecoder)

    stats = {"imported": 0, "updated": 0, "skipped": 0, "errors": 0}

    async with AsyncSessionLocal() as session:
        for table_name, records in data.items():
            if not records:
                print(f"表 {table_name}: 无数据，跳过")
                continue

            print(f"\n处理表: {table_name} ({len(records)} 条记录)")

            for record in records:
                try:
                    result = await import_record(session, table_name, record, update_existing, dry_run)
                    if result == "imported":
                        stats["imported"] += 1
                    elif result == "updated":
                        stats["updated"] += 1
                    elif result == "skipped":
                        stats["skipped"] += 1
                except Exception as e:
                    print(f"  错误: {record.get('id', 'unknown')} - {str(e)}")
                    stats["errors"] += 1

        if not dry_run:
            await session.commit()
            print("\n事务已提交")
        else:
            print("\n试运行模式，未提交任何更改")

    print("\n" + "=" * 50)
    print("导入统计:")
    print(f"  新增: {stats['imported']}")
    print(f"  更新: {stats['updated']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['errors']}")


async def import_record(session, table_name: str, record: dict, update_existing: bool, dry_run: bool) -> str:
    """导入单条记录，返回: imported/updated/skipped"""

    record_id = record.get("id")
    if not record_id:
        return "skipped"

    check_sql = text(f"SELECT id FROM {table_name} WHERE id = :id")
    result = await session.execute(check_sql, {"id": record_id})
    exists = result.first() is not None

    # 将 dict/list 序列化为 JSON 字符串，将引用不存在用户的 owner_id 置为 NULL
    serialized = {}
    for k, v in record.items():
        serialized[k] = serialize_value(v)

    columns = list(serialized.keys())
    placeholders = ", ".join([f":{col}" for col in columns])
    col_names = ", ".join(columns)

    if exists:
        if not update_existing:
            return "skipped"

        set_clause = ", ".join([f"{col} = :{col}" for col in columns if col != "id"])
        update_sql = text(f"UPDATE {table_name} SET {set_clause} WHERE id = :id")
        if not dry_run:
            await session.execute(update_sql, serialized)
        print(f"  更新: {record_id}")
        return "updated"
    else:
        insert_sql = text(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})")
        if not dry_run:
            await session.execute(insert_sql, serialized)
        print(f"  新增: {record_id}")
        return "imported"


async def verify_dependencies(data: dict):
    """验证外键依赖是否满足"""
    print("\n验证外键依赖...")

    async with AsyncSessionLocal() as session:
        for table_name, records in data.items():
            if table_name == "ai_models":
                for record in records:
                    provider_id = record.get("provider_id")
                    if provider_id:
                        result = await session.execute(
                            text("SELECT id FROM ai_model_providers WHERE id = :id"),
                            {"id": provider_id}
                        )
                        if not result.first():
                            print(f"  警告: ai_model {record.get('id')} 引用了不存在的 provider {provider_id}")

            elif table_name == "model_configs":
                for record in records:
                    user_id = record.get("user_id")
                    project_id = record.get("project_id")
                    if user_id:
                        result = await session.execute(
                            text("SELECT id FROM users WHERE id = :id"),
                            {"id": user_id}
                        )
                        if not result.first():
                            print(f"  警告: model_config {record.get('id')} 引用了不存在的 user {user_id}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="导入基础数据到数据库")
    parser.add_argument("input_file", help="JSON 数据文件路径")
    parser.add_argument("--update", "-u", action="store_true", help="更新已存在的记录")
    parser.add_argument("--dry-run", "-n", action="store_true", help="试运行，不实际写入数据库")
    parser.add_argument("--verify", "-v", action="store_true", help="仅验证外键依赖")

    args = parser.parse_args()

    if args.verify:
        with open(args.input_file, "r", encoding="utf-8") as f:
            data = json.load(f, cls=DateTimeDecoder)
        asyncio.run(verify_dependencies(data))
    else:
        asyncio.run(import_data(args.input_file, args.update, args.dry_run))


if __name__ == "__main__":
    main()
