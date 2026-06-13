from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.security import hash_password, verify_password, create_access_token


VALID_ROLES = {"super_admin", "template_admin", "approver", "user"}


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    role: str = "user",
) -> User:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_role(db: AsyncSession, user_id: str, role: str) -> User:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User not found: {user_id}")
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user_id: str,
    email: str | None = None,
    password: str | None = None,
) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User not found: {user_id}")
    if email is not None:
        user.email = email
    if password is not None:
        user.password_hash = hash_password(password)
    await db.commit()
    await db.refresh(user)
    return user


async def toggle_user_active(db: AsyncSession, user_id: str) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User not found: {user_id}")
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    return user


def create_token_for_user(user: User) -> str:
    return create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )


async def ensure_default_admin(db: AsyncSession) -> None:
    existing = await get_user_by_username(db, "admin")
    if not existing:
        await create_user(db, "admin", "admin@example.com", "admin123", "super_admin")
