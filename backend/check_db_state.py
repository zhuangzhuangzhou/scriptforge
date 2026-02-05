
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check_db():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        # Check tables
        result = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';"))
        tables = [row[0] for row in result]
        print(f"Tables in DB: {tables}")
        
        # Check alembic_version
        try:
            result = await conn.execute(text("SELECT version_num FROM alembic_version;"))
            versions = [row[0] for row in result]
            print(f"Alembic versions: {versions}")
        except Exception as e:
            print(f"Error checking alembic_version: {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_db())
