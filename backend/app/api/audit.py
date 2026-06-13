from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, require_role
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.services.audit_service import query_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["审计日志"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    resource_type: str | None = None,
    user_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    items, total = await query_audit_logs(
        db, page=page, page_size=page_size,
        action=action, resource_type=resource_type,
        user_id=user_id, start_date=start_date, end_date=end_date,
    )
    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                id=str(item.id),
                user_id=str(item.user_id) if item.user_id else None,
                action=item.action,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                detail=item.detail,
                ip_address=item.ip_address,
                user_agent=item.user_agent,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_id: str,
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    result = await db.execute(select(AuditLog).where(AuditLog.id == audit_id))
    item = result.scalar_one_or_none()
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="审计日志不存在")
    return AuditLogResponse(
        id=str(item.id),
        user_id=str(item.user_id) if item.user_id else None,
        action=item.action,
        resource_type=item.resource_type,
        resource_id=item.resource_id,
        detail=item.detail,
        ip_address=item.ip_address,
        user_agent=item.user_agent,
        created_at=item.created_at,
    )
