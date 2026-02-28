import json
import asyncio
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

# 解决序列化问题
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


async def export_data():
    print("Starting raw SQL data export...")
    exported_data = {}

    # 我们要导出的核心表，按依赖顺序
    tables_to_export = [
        "ai_model_providers",
        "ai_models",
        "model_configs",
        "skills",
        "agent_definitions",
        "ai_resources"
    ]

    for table_name in tables_to_export:
        print(f"Exporting table: {table_name}...")
        try:
            async with AsyncSessionLocal() as session:
                # 执行原生 SQL 查询全表
                result = await session.execute(text(f"SELECT * FROM {table_name}"))

                # 获取列名
                columns = result.keys()

                # 组装数据字典
                table_data = []
                for row in result.all():
                    row_dict = dict(zip(columns, row))
                    table_data.append(row_dict)

                exported_data[table_name] = table_data
                print(f"  -> Exported {len(table_data)} records for {table_name}")
        except Exception as e:
            # 记录找不到表等错误，但不中断
            print(f"  -> Skipping {table_name}: {str(e)}")


    # 写入 JSON 文件
    output_file = "foundation_data_export.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(exported_data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    print(f"\nExport complete! Data safely saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(export_data())