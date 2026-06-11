import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database import get_db

TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/contract",
)


@pytest_asyncio.fixture
async def client():
    """每个测试用例独立的 HTTP 客户端，使用独立数据库连接池"""
    # 为每个测试创建独立的 engine，避免跨事件循环连接泄漏
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_size=5, max_overflow=0)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def sample_template(client: AsyncClient):
    """上传一个样例模板，返回 (template_id, variables)"""
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx"
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
