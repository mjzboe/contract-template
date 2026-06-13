import functools
from typing import Callable

from app.services.audit_service import log_audit


def audit_action(action: str, resource_type: str):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            db = kwargs.get("db") or kwargs.get("DbSession")
            current_user = kwargs.get("current_user")

            user_id = str(current_user.id) if current_user else None
            resource_id = None
            detail = None

            if isinstance(result, dict):
                resource_id = str(result.get("id", ""))
                detail = result.get("_audit_detail")

            if db:
                try:
                    await log_audit(
                        db=db,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        user_id=user_id,
                        detail=detail,
                    )
                except Exception:
                    pass

            return result

        return wrapper

    return decorator
