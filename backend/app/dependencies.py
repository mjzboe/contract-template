from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def get_db_session() -> AsyncSession:
    async with get_db() as session:
        yield session


# Placeholder: will be replaced with real auth in Step 4
def get_current_user():
    return {"user_id": "dev-user", "username": "developer", "role": "admin"}


DbSession = Depends(get_db_session)
CurrentUser = Depends(get_current_user)
