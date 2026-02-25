import asyncio
from celery import shared_task
from sqlalchemy import select, func, update, delete
from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.batch import Batch
from app.utils.batch_divider import BatchDivider
import logging

logger = logging.getLogger(__name__)

@shared_task(name="create_batches_task")
def create_batches_task(project_id: str):
    """
    异步任务：执行项目章节分批
    """
    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                logger.info(f"Starting batch creation for project {project_id}")

                # 1. 获取项目信息
                result = await db.execute(select(Project).where(Project.id == project_id))
                project = result.scalar_one_or_none()
                if not project:
                    logger.error(f"Project {project_id} not found")
                    return

                # 2. 检查是否已有批次 (幂等性)
                existing = await db.execute(
                    select(func.count()).select_from(Batch).where(Batch.project_id == project_id)
                )
                if existing.scalar() > 0:
                    logger.info(f"Batches for project {project_id} already exist. Skipping.")
                    return

                # 3. 获取所有章节
                chapters_result = await db.execute(
                    select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_number)
                )
                chapters = chapters_result.scalars().all()
                if not chapters:
                    logger.warning(f"No chapters found for project {project_id}")
                    return

                # 4. 执行分批逻辑
                chapters_data = [
                    {"chapter_number": c.chapter_number, "word_count": c.word_count, "id": c.id}
                    for c in chapters
                ]

                batch_size = project.batch_size or 6
                divider = BatchDivider(batch_size=batch_size)
                batches_data = divider.divide(chapters_data)

                # 5. 创建新批次并关联章节
                for b_data in batches_data:
                    new_batch = Batch(
                        project_id=project_id,
                        batch_number=b_data['batch_number'],
                        start_chapter=b_data['start_chapter'],
                        end_chapter=b_data['end_chapter'],
                        total_chapters=b_data['total_chapters'],
                        total_words=b_data['total_words'],
                        breakdown_status='pending',
                        script_status='pending'
                    )
                    db.add(new_batch)
                    await db.flush() # 获取 batch id

                    # 更新章节的 batch_id
                    chapter_ids = [c['id'] for c in b_data['chapters']]
                    await db.execute(
                        update(Chapter).where(Chapter.id.in_(chapter_ids)).values(batch_id=new_batch.id)
                    )

                await db.commit()
                logger.info(f"Successfully created {len(batches_data)} batches for project {project_id}")

            except Exception as e:
                logger.error(f"Error creating batches for project {project_id}: {str(e)}")
                await db.rollback()

    # 运行异步代码
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(_process())