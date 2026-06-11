import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database import get_db

# 使用与开发环境相同的 PostgreSQL
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/contract",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    """创建一个事务中的 session，测试后回滚

    使用 begin_nested (savepoint) 确保测试中的操作可以被回滚，
    不污染开发数据库。
    """
    async with TestSessionFactory() as session:
        async with session.begin():
            nested = await session.begin_nested()
            yield session
            await nested.rollback()
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """注入测试用 db_session 的 HTTP 客户端"""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_template(client: AsyncClient):
    """上传一个样例模板，返回 (template_id, variables)"""
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        response = await client.post(
            "/api/v1/templates",
            data={"name": "测试模板_股东会决议", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
        )
    assert response.status_code == 200
    data = response.json()
    return data["template"]["id"], data["variables"]


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
