import time
import json
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import StreamingResponse
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
    "/ws/",  # WebSocket 连接
]

# 敏感字段,需要脱敏
SENSITIVE_FIELDS = ["password", "token", "secret", "api_key", "access_token"]


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

        # 读取请求体
        request_body = await self._get_request_body(request)

        # 执行请求并捕获响应
        error_message: Optional[str] = None
        response_body: Optional[str] = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code

            # 读取响应体 - 需要重新构造响应
            response_body_bytes = b""
            async for chunk in response.body_iterator:
                response_body_bytes += chunk

            # 尝试解析响应体
            if response_body_bytes:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        body_json = json.loads(response_body_bytes)
                        sanitized = self._sanitize_data(body_json)
                        response_body = json.dumps(sanitized, ensure_ascii=False)[:10000]
                    except json.JSONDecodeError:
                        response_body = response_body_bytes.decode('utf-8', errors='ignore')[:10000]

            # 重新构造响应
            from starlette.responses import Response as StarletteResponse
            response = StarletteResponse(
                content=response_body_bytes,
                status_code=status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

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
                    request_body=request_body,
                    user_id=user_id,
                    user_ip=user_ip,
                    user_agent=user_agent,
                    status_code=status_code,
                    response_body=response_body,
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

    async def _get_request_body(self, request: Request) -> Optional[str]:
        """获取请求体（脱敏处理）"""
        try:
            # 只记录 POST, PUT, PATCH 请求的 body
            if request.method not in ["POST", "PUT", "PATCH"]:
                return None

            # 读取请求体
            body = await request.body()
            if not body:
                return None

            # 尝试解析 JSON
            try:
                body_json = json.loads(body)
                # 脱敏处理
                sanitized = self._sanitize_data(body_json)
                return json.dumps(sanitized, ensure_ascii=False)[:10000]  # 限制长度
            except json.JSONDecodeError:
                # 非 JSON 数据，直接返回文本
                return body.decode('utf-8', errors='ignore')[:10000]

        except Exception as e:
            logger.warning(f"读取请求体失败: {e}")
            return None

    def _sanitize_data(self, data):
        """脱敏处理敏感字段"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # 检查是否是敏感字段
                if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data

    async def _save_log(
        self,
        method: str,
        path: str,
        query_params: Optional[str],
        request_body: Optional[str],
        user_id: Optional[str],
        user_ip: str,
        user_agent: str,
        status_code: int,
        response_body: Optional[str],
        response_time: int,
        error_message: Optional[str]
    ):
        """保存日志到数据库"""
        async with AsyncSessionLocal() as db:
            log = APILog(
                method=method,
                path=path,
                query_params=query_params,
                request_body=request_body,
                user_id=user_id,
                user_ip=user_ip,
                user_agent=user_agent,
                status_code=status_code,
                response_body=response_body,
                response_time=response_time,
                error_message=error_message
            )
            db.add(log)
            await db.commit()
