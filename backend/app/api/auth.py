from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, require_role
from app.models.user import User
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_token_for_user,
    create_user,
    ensure_default_admin,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = DbSession):
    user = await authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_token_for_user(user)
    return TokenResponse(access_token=token)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = DbSession,
    _admin: User = Depends(require_role("super_admin")),
):
    from app.services.auth_service import get_user_by_username

    existing = await get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )
    try:
        user = await create_user(db, data.username, data.email, data.password, data.role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(require_role("user", "template_admin", "approver", "super_admin"))):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.post("/init-admin", response_model=UserResponse)
async def init_admin(db: AsyncSession = DbSession):
    await ensure_default_admin(db)
    from app.services.auth_service import get_user_by_username

    admin = await get_user_by_username(db, "admin")
    return UserResponse(
        id=str(admin.id),
        username=admin.username,
        email=admin.email,
        role=admin.role,
        is_active=admin.is_active,
    )
