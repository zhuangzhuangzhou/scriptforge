import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def list_tables():
    print("Connecting to database to list tables...")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text(
                "SELECT tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema'"
            ))
            tables = [row[0] for row in result.all()]
            if not tables:
                print("No tables found in the database.")
            else:
                print("Found tables:")
                for table in sorted(tables):
                    print(f"  - {table}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_tables())
