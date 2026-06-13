from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.security import decode_access_token

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
API_PREFIX = "/api/v1"

SKIP_PATHS = {"/api/v1/auth/login", "/api/v1/auth/init-admin", "/docs", "/openapi.json"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        if (
            request.method in WRITE_METHODS
            and request.url.path.startswith(API_PREFIX)
            and request.url.path not in SKIP_PATHS
        ):
            try:
                user_id = None
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    payload = decode_access_token(token)
                    if payload:
                        user_id = payload.get("sub")

                from app.database import async_session
                from app.services.audit_service import log_audit

                async with async_session() as db:
                    await log_audit(
                        db=db,
                        action=request.method.lower(),
                        resource_type="api",
                        resource_id=request.url.path,
                        user_id=user_id,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("User-Agent"),
                    )
            except Exception:
                pass

        return response
