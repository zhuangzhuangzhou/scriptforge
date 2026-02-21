import time
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.database import AsyncSessionLocal
from app.models.api_log import APILog

logger = logging.getLogger(__name__)

# 不记录日志的路径前缀
EXCLUDED_PATHS = [
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
]


class APILoggingMiddleware(BaseHTTPMiddleware):
    """API 请求日志中间件"""

    def __init__(self, app: ASGIApp, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否启用
        if not self.enabled:
            return await call_next(request)

        # 排除不需要记录的路径
        path = request.url.path
        if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
            return await call_next(request)

        # 记录开始时间
        start_time = time.time()

        # 获取用户信息
        user_id = await self._get_user_id(request)
        user_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")[:500]

        # 执行请求
        error_message: Optional[str] = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            error_message = str(e)
            status_code = 500
            raise
        finally:
            # 计算响应时间
            response_time = int((time.time() - start_time) * 1000)

            # 异步保存日志（不阻塞响应）
            try:
                await self._save_log(
                    method=request.method,
                    path=path,
                    query_params=str(request.query_params) if request.query_params else None,
                    user_id=user_id,
                    user_ip=user_ip,
                    user_agent=user_agent,
                    status_code=status_code,
                    response_time=response_time,
                    error_message=error_message
                )
            except Exception as e:
                logger.error(f"保存 API 日志失败: {e}")

        return response

    async def _get_user_id(self, request: Request) -> Optional[str]:
        """从请求中提取用户 ID"""
        # 尝试从 request.state 获取（如果 auth 中间件已设置）
        if hasattr(request.state, "user") and request.state.user:
            return str(request.state.user.id)

        # 尝试从 Authorization header 解析 JWT
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                from app.core.config import settings
                token = auth_header[7:]
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                return payload.get("sub")
            except Exception:
                pass

        return None

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        # 优先从代理头获取
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 直接连接的客户端
        if request.client:
            return request.client.host

        return "unknown"

    async def _save_log(
        self,
        method: str,
        path: str,
        query_params: Optional[str],
        user_id: Optional[str],
        user_ip: str,
        user_agent: str,
        status_code: int,
        response_time: int,
        error_message: Optional[str]
    ):
        """保存日志到数据库"""
        async with AsyncSessionLocal() as db:
            log = APILog(
                method=method,
                path=path,
                query_params=query_params,
                user_id=user_id,
                user_ip=user_ip,
                user_agent=user_agent,
                status_code=status_code,
                response_time=response_time,
                error_message=error_message
            )
            db.add(log)
            await db.commit()
