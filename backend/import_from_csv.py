"""
从 CSV 导入 skills 和 ai_resources 数据
"""
import csv
import json
import asyncio
from datetime import datetime
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

user_id = '550e8400-e29b-41d4-a716-446655440000'  # zhuangzhuang's ID

def parse_bool(s):
    if not s:
        return False
    return s.strip().lower() in ('t', 'true', '1', 'yes')

def parse_timestamp(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.strip())
    except:
        return None

async def import_skills():
    print("导入 skills...")
    count = 0
    with open('/tmp/skills.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        async with AsyncSessionLocal() as session:
            for row in reader:
                if not row or not row[0]:
                    continue
                # CSV 列顺序需要根据实际调整
                # id, name, display_name, description, category, module_path, class_name, parameters, is_active, is_builtin, version, author, created_at, updated_at, visibility, owner_id, allowed_users, is_template_based, prompt_template, output_schema, input_schema, model_config, example_input, example_output
                try:
                    sql = text("""
                        INSERT INTO skills (id, name, display_name, description, category, module_path, class_name, parameters, is_active, is_builtin, version, author, created_at, updated_at, visibility, owner_id, allowed_users, is_template_based, prompt_template, output_schema, input_schema, model_config, example_input, example_output)
                        VALUES (:id, :name, :display_name, :description, :category, :module_path, :class_name, :parameters, :is_active, :is_builtin, :version, :author, :created_at, :updated_at, :visibility, :owner_id, :allowed_users, :is_template_based, :prompt_template, :output_schema, :input_schema, :model_config, :example_input, :example_output)
                        ON CONFLICT (id) DO NOTHING
                    """)
                    await session.execute(sql, {
                        'id': row[0],
                        'name': row[1],
                        'display_name': row[2],
                        'description': row[3] if len(row) > 3 else '',
                        'category': row[4] if len(row) > 4 else '',
                        'module_path': row[5] if len(row) > 5 else '',
                        'class_name': row[6] if len(row) > 6 else '',
                        'parameters': None,
                        'is_active': parse_bool(row[8]) if len(row) > 8 else True,
                        'is_builtin': parse_bool(row[9]) if len(row) > 9 else True,
                        'version': row[10] if len(row) > 10 else '1.0',
                        'author': row[11] if len(row) > 11 else '',
                        'created_at': parse_timestamp(row[12]) if len(row) > 12 else None,
                        'updated_at': parse_timestamp(row[13]) if len(row) > 13 else None,
                        'visibility': row[14] if len(row) > 14 else 'public',
                        'owner_id': user_id,
                        'allowed_users': None,
                        'is_template_based': parse_bool(row[17]) if len(row) > 17 else False,
                        'prompt_template': row[18] if len(row) > 18 and row[18] else None,
                        'output_schema': None,
                        'input_schema': None,
                        'model_config': None,
                        'example_input': None,
                        'example_output': None,
                    })
                    count += 1
                except Exception as e:
                    print(f"  Error: {row[0]} - {str(e)[:50]}")
            await session.commit()
    print(f"  导入 {count} 条")
    return count

async def main():
    await import_skills()
    
    # 验证
    async with AsyncSessionLocal() as session:
        result = await session.execute(text('SELECT count(*) FROM skills'))
        print(f"Total skills in DB: {result.scalar()}")

if __name__ == '__main__':
    asyncio.run(main())