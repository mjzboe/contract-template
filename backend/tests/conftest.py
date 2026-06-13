import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base
from app.services.auth_service import create_user

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/contract",
)


@pytest_asyncio.fixture
async def db_engine():
    """每个测试独立的 engine，避免跨事件循环连接泄漏"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_size=5, max_overflow=0)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """提供独立的数据库 session，并在测试前清空所有表"""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, db_engine):
    """带认证覆盖的 HTTP 测试客户端"""

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ========== 用户和认证 fixture ==========

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """创建 super_admin 用户并返回"""
    return await create_user(db_session, "admin", "admin@test.com", "admin123", "super_admin")


@pytest_asyncio.fixture
async def normal_user(db_session: AsyncSession):
    """创建普通 user 角色用户"""
    return await create_user(db_session, "normaluser", "user@test.com", "user123", "user")


@pytest_asyncio.fixture
async def template_admin_user(db_session: AsyncSession):
    """创建 template_admin 角色用户"""
    return await create_user(db_session, "tmpladmin", "tmpl@test.com", "tmpl123", "template_admin")


@pytest_asyncio.fixture
async def approver_user(db_session: AsyncSession):
    """创建 approver 角色用户"""
    return await create_user(db_session, "approver", "approver@test.com", "appr123", "approver")


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user) -> str:
    """获取 super_admin 的 JWT token"""
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_headers(admin_token: str) -> dict:
    """super_admin 认证 headers"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def user_token(client: AsyncClient, normal_user) -> str:
    """获取普通 user 的 JWT token"""
    resp = await client.post("/api/v1/auth/login", json={"username": "normaluser", "password": "user123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_headers(user_token: str) -> dict:
    """普通 user 认证 headers"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest_asyncio.fixture
async def template_admin_token(client: AsyncClient, template_admin_user) -> str:
    """获取 template_admin 的 JWT token"""
    resp = await client.post("/api/v1/auth/login", json={"username": "tmpladmin", "password": "tmpl123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def template_admin_headers(template_admin_token: str) -> dict:
    """template_admin 认证 headers"""
    return {"Authorization": f"Bearer {template_admin_token}"}


@pytest_asyncio.fixture
async def approver_token(client: AsyncClient, approver_user) -> str:
    """获取 approver 的 JWT token"""
    resp = await client.post("/api/v1/auth/login", json={"username": "approver", "password": "appr123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def approver_headers(approver_token: str) -> dict:
    """approver 认证 headers"""
    return {"Authorization": f"Bearer {approver_token}"}


# ========== 业务 fixture ==========

@pytest_asyncio.fixture
async def sample_template(client: AsyncClient, admin_headers: dict):
    """上传一个样例模板，返回 (template_id, variables)"""
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        response = await client.post(
            "/api/v1/templates",
            data={"name": "测试模板_股东会决议", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
            headers=admin_headers,
        )
    assert response.status_code == 200
    data = response.json()
    return data["template"]["id"], data["variables"]


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
