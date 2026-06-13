from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, require_role
from app.models.user import User
from app.schemas.role import RoleUpdate, UserRoleResponse
from app.schemas.user import UserUpdateRequest, UserResponse
from app.services.auth_service import (
    create_user,
    get_user_by_username,
    toggle_user_active,
    update_user,
    update_user_role,
    VALID_ROLES,
)

router = APIRouter(prefix="/users", tags=["用户管理"])


def _to_response(u: User) -> UserRoleResponse:
    return UserRoleResponse(
        id=str(u.id), username=u.username, email=u.email,
        role=u.role, is_active=u.is_active,
    )


@router.get("", response_model=list[UserRoleResponse])
async def list_users(
    keyword: str | None = Query(None, description="搜索用户名或邮箱"),
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    query = select(User).order_by(User.created_at.desc())
    if keyword:
        query = query.where(
            or_(
                User.username.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%"),
            )
        )
    result = await db.execute(query)
    users = result.scalars().all()
    return [_to_response(u) for u in users]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user_endpoint(
    data: dict,
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")
    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="用户名、邮箱、密码不能为空")
    existing = await get_user_by_username(db, username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    try:
        user = await create_user(db, username, email, password, role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse(
        id=str(user.id), username=user.username, email=user.email,
        role=user.role, is_active=user.is_active,
    )


@router.put("/{user_id}", response_model=UserRoleResponse)
async def update_user_endpoint(
    user_id: str,
    data: UserUpdateRequest,
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    try:
        user = await update_user(db, user_id, email=data.email, password=data.password)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(user)


@router.put("/{user_id}/role", response_model=UserRoleResponse)
async def change_user_role(
    user_id: str,
    data: RoleUpdate,
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    if data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"无效角色，可选值: {VALID_ROLES}")
    try:
        user = await update_user_role(db, user_id, data.role)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(user)


@router.put("/{user_id}/toggle-active", response_model=UserRoleResponse)
async def toggle_active(
    user_id: str,
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    try:
        user = await toggle_user_active(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(user)
