"""后台数据分析 API - 分析拆解任务的模型、资源使用情况和质检成功率"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_
from datetime import datetime, timedelta
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.plot_breakdown import PlotBreakdown
from app.models.ai_task import AITask
from app.models.ai_resource import AIResource
from app.models.model_config import ModelConfig
from app.api.v1.auth import get_current_user

router = APIRouter()


def get_period_start(period: str) -> datetime:
    """根据周期获取起始时间"""
    now = datetime.utcnow()
    if period == "day":
        return now - timedelta(days=1)
    elif period == "week":
        return now - timedelta(weeks=1)
    elif period == "month":
        return now - timedelta(days=30)
    elif period == "quarter":
        return now - timedelta(days=90)
    elif period == "year":
        return now - timedelta(days=365)
    else:
        return now - timedelta(weeks=1)  # 默认一周


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


@router.get("/breakdown/overview")
async def get_breakdown_overview(
    period: str = Query(default="week", regex="^(day|week|month|quarter|year)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解任务概览统计

    返回：
    - total: 总拆解数
    - passed: 质检通过数
    - failed: 质检失败数
    - pending: 待质检数
    - pass_rate: 通过率
    - avg_score: 平均分
    - avg_retry: 平均重试次数
    """
    period_start = get_period_start(period)

    # 统计各状态数量
    result = await db.execute(
        select(
            func.count(PlotBreakdown.id).label("total"),
            func.sum(case((PlotBreakdown.qa_status == "PASS", 1), else_=0)).label("passed"),
            func.sum(case((PlotBreakdown.qa_status == "FAIL", 1), else_=0)).label("failed"),
            func.sum(case((PlotBreakdown.qa_status == "pending", 1), else_=0)).label("pending"),
            func.avg(PlotBreakdown.qa_score).label("avg_score"),
            func.avg(PlotBreakdown.qa_retry_count).label("avg_retry")
        ).where(PlotBreakdown.created_at >= period_start)
    )
    row = result.one()

    total = row.total or 0
    passed = row.passed or 0
    failed = row.failed or 0
    pending = row.pending or 0
    avg_score = round(row.avg_score, 1) if row.avg_score else 0
    avg_retry = round(row.avg_retry, 2) if row.avg_retry else 0
    pass_rate = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0

    return {
        "period": period,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
        "avg_retry": avg_retry
    }


@router.get("/breakdown/by-model")
async def get_breakdown_by_model(
    period: str = Query(default="week", regex="^(day|week|month|quarter|year)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """按模型统计质检成功率

    直接通过 PlotBreakdown.model_config_id 关联 ModelConfig 进行统计
    """
    period_start = get_period_start(period)

    # 直接通过 model_config_id 关联查询
    result = await db.execute(
        select(
            ModelConfig.provider,
            ModelConfig.model_name,
            ModelConfig.display_name,
            func.count(PlotBreakdown.id).label("total"),
            func.sum(case((PlotBreakdown.qa_status == "PASS", 1), else_=0)).label("passed"),
            func.sum(case((PlotBreakdown.qa_status == "FAIL", 1), else_=0)).label("failed"),
            func.avg(PlotBreakdown.qa_score).label("avg_score")
        ).select_from(PlotBreakdown).join(
            ModelConfig, PlotBreakdown.model_config_id == ModelConfig.id
        ).where(
            PlotBreakdown.created_at >= period_start
        ).group_by(
            ModelConfig.id, ModelConfig.provider, ModelConfig.model_name, ModelConfig.display_name
        ).order_by(func.count(PlotBreakdown.id).desc())
    )

    models = []
    for row in result:
        total = row.total or 0
        passed = row.passed or 0
        failed = row.failed or 0
        pass_rate = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0
        avg_score = round(row.avg_score, 1) if row.avg_score else 0

        models.append({
            "provider": row.provider,
            "model_name": row.model_name,
            "display_name": row.display_name or f"{row.provider}/{row.model_name}",
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "avg_score": avg_score
        })

    return {
        "period": period,
        "models": models
    }


@router.get("/breakdown/by-resource")
async def get_breakdown_by_resource(
    period: str = Query(default="week", regex="^(day|week|month|quarter|year)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """按资源（改编方法论）统计质检成功率"""
    period_start = get_period_start(period)

    # 查询每个资源的统计数据
    result = await db.execute(
        select(
            PlotBreakdown.used_adapt_method_id,
            AIResource.name,
            AIResource.display_name,
            func.count(PlotBreakdown.id).label("total"),
            func.sum(case((PlotBreakdown.qa_status == "PASS", 1), else_=0)).label("passed"),
            func.sum(case((PlotBreakdown.qa_status == "FAIL", 1), else_=0)).label("failed"),
            func.avg(PlotBreakdown.qa_score).label("avg_score")
        ).outerjoin(
            AIResource, PlotBreakdown.used_adapt_method_id == AIResource.name
        ).where(
            PlotBreakdown.created_at >= period_start
        ).group_by(
            PlotBreakdown.used_adapt_method_id,
            AIResource.name,
            AIResource.display_name
        ).order_by(func.count(PlotBreakdown.id).desc())
    )

    resources = []
    for row in result:
        total = row.total or 0
        passed = row.passed or 0
        failed = row.failed or 0
        pass_rate = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0
        avg_score = round(row.avg_score, 1) if row.avg_score else 0

        resources.append({
            "resource_id": row.used_adapt_method_id,
            "name": row.name or "未指定",
            "display_name": row.display_name or "默认方法论",
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "avg_score": avg_score
        })

    return {
        "period": period,
        "resources": resources
    }


@router.get("/breakdown/score-distribution")
async def get_score_distribution(
    period: str = Query(default="week", regex="^(day|week|month|quarter|year)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取质检分数分布"""
    period_start = get_period_start(period)

    # 按分数段统计
    result = await db.execute(
        select(
            func.sum(case((and_(PlotBreakdown.qa_score >= 90, PlotBreakdown.qa_score <= 100), 1), else_=0)).label("excellent"),
            func.sum(case((and_(PlotBreakdown.qa_score >= 80, PlotBreakdown.qa_score < 90), 1), else_=0)).label("good"),
            func.sum(case((and_(PlotBreakdown.qa_score >= 70, PlotBreakdown.qa_score < 80), 1), else_=0)).label("average"),
            func.sum(case((and_(PlotBreakdown.qa_score >= 60, PlotBreakdown.qa_score < 70), 1), else_=0)).label("passing"),
            func.sum(case((PlotBreakdown.qa_score < 60, 1), else_=0)).label("fail"),
            func.sum(case((PlotBreakdown.qa_score.is_(None), 1), else_=0)).label("no_score")
        ).where(PlotBreakdown.created_at >= period_start)
    )
    row = result.one()

    distribution = [
        {"range": "90-100", "label": "优秀", "count": row.excellent or 0, "color": "#22c55e"},
        {"range": "80-89", "label": "良好", "count": row.good or 0, "color": "#84cc16"},
        {"range": "70-79", "label": "中等", "count": row.average or 0, "color": "#eab308"},
        {"range": "60-69", "label": "及格", "count": row.passing or 0, "color": "#f97316"},
        {"range": "0-59", "label": "不及格", "count": row.fail or 0, "color": "#ef4444"},
        {"range": "无分数", "label": "未评分", "count": row.no_score or 0, "color": "#6b7280"}
    ]

    return {
        "period": period,
        "distribution": distribution
    }


@router.get("/breakdown/trend")
async def get_breakdown_trend(
    period: str = Query(default="week", regex="^(day|week|month|quarter|year)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解任务时间趋势"""
    period_start = get_period_start(period)

    # 根据周期选择时间粒度
    if period == "day":
        date_trunc = func.date_trunc('hour', PlotBreakdown.created_at)
    elif period in ["week", "month"]:
        date_trunc = func.date_trunc('day', PlotBreakdown.created_at)
    else:
        date_trunc = func.date_trunc('week', PlotBreakdown.created_at)

    result = await db.execute(
        select(
            date_trunc.label("date"),
            func.count(PlotBreakdown.id).label("total"),
            func.sum(case((PlotBreakdown.qa_status == "PASS", 1), else_=0)).label("passed"),
            func.sum(case((PlotBreakdown.qa_status == "FAIL", 1), else_=0)).label("failed"),
            func.avg(PlotBreakdown.qa_score).label("avg_score")
        ).where(
            PlotBreakdown.created_at >= period_start
        ).group_by(date_trunc).order_by(date_trunc)
    )

    trend = []
    for row in result:
        total = row.total or 0
        passed = row.passed or 0
        failed = row.failed or 0
        pass_rate = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0
        avg_score = round(row.avg_score, 1) if row.avg_score else 0

        trend.append({
            "date": row.date.isoformat() if row.date else None,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "avg_score": avg_score
        })

    return {
        "period": period,
        "trend": trend
    }


@router.get("/breakdown/retry-stats")
async def get_retry_stats(
    period: str = Query(default="week", regex="^(day|week|month|quarter|year)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取重试次数统计"""
    period_start = get_period_start(period)

    # 按重试次数统计
    result = await db.execute(
        select(
            func.sum(case((PlotBreakdown.qa_retry_count == 0, 1), else_=0)).label("retry_0"),
            func.sum(case((PlotBreakdown.qa_retry_count == 1, 1), else_=0)).label("retry_1"),
            func.sum(case((PlotBreakdown.qa_retry_count == 2, 1), else_=0)).label("retry_2"),
            func.sum(case((PlotBreakdown.qa_retry_count >= 3, 1), else_=0)).label("retry_3_plus"),
            func.avg(PlotBreakdown.qa_retry_count).label("avg_retry")
        ).where(PlotBreakdown.created_at >= period_start)
    )
    row = result.one()

    stats = [
        {"retry_count": "0次", "count": row.retry_0 or 0, "color": "#22c55e"},
        {"retry_count": "1次", "count": row.retry_1 or 0, "color": "#84cc16"},
        {"retry_count": "2次", "count": row.retry_2 or 0, "color": "#eab308"},
        {"retry_count": "3次+", "count": row.retry_3_plus or 0, "color": "#ef4444"}
    ]

    return {
        "period": period,
        "stats": stats,
        "avg_retry": round(row.avg_retry, 2) if row.avg_retry else 0
    }
