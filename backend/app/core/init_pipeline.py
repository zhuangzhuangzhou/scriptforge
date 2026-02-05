from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pipeline import Pipeline, PipelineStage
from app.core.pipeline_defaults import SYSTEM_OWNER_ID, DEFAULT_PIPELINE_STAGES


async def init_default_pipeline(db: AsyncSession) -> None:
    """初始化默认 Pipeline（若不存在）"""
    result = await db.execute(
        select(Pipeline).where(
            Pipeline.is_default == True,
            Pipeline.is_active == True
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return

    pipeline = Pipeline(
        user_id=SYSTEM_OWNER_ID,
        name="默认Pipeline",
        description="系统内置默认流水线",
        config={},
        stages_config=DEFAULT_PIPELINE_STAGES,
        is_default=True,
        is_active=True,
        version=1
    )
    db.add(pipeline)
    await db.flush()

    for stage_data in DEFAULT_PIPELINE_STAGES:
        stage = PipelineStage(
            pipeline_id=pipeline.id,
            name=stage_data.get("name"),
            display_name=stage_data.get("display_name", stage_data.get("name")),
            description=stage_data.get("description"),
            skills=stage_data.get("skills", []),
            skills_order=stage_data.get("skills_order"),
            config=stage_data.get("config", {}),
            input_mapping=stage_data.get("input_mapping"),
            output_mapping=stage_data.get("output_mapping"),
            order=stage_data.get("order", 0)
        )
        db.add(stage)

    await db.commit()
