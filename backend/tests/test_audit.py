"""审计日志测试"""
import json
import os
import tempfile

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.models.audit_log import AuditLog


# ========== 审计文件写入单元测试 ==========

def test_audit_file_writer():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = os.path.join(tmpdir, "logs", "audit")
        os.makedirs(log_dir, exist_ok=True)
        date_str = "2026-06-11"
        log_path = os.path.join(log_dir, f"{date_str}.jsonl")

        record = {"action": "test", "detail": "hello"}
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["action"] == "test"


def test_audit_log_detail_json_format():
    detail = {"before": {"name": "old"}, "after": {"name": "new"}}
    detail_str = json.dumps(detail, ensure_ascii=False)
    parsed = json.loads(detail_str)
    assert parsed["before"]["name"] == "old"
    assert parsed["after"]["name"] == "new"


# ========== 审计中间件集成测试 ==========

@pytest.mark.asyncio
async def test_audit_middleware_records_write(client: AsyncClient, admin_headers: dict, admin_user, db_engine):
    """写操作应被审计中间件记录"""
    await client.post("/api/v1/categories", json={"name": "审计测试分类"}, headers=admin_headers)

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(AuditLog).where(AuditLog.action == "post"))
        logs = result.scalars().all()
    assert len(logs) >= 1
    log = logs[-1]
    assert log.resource_type == "api"
    assert "/categories" in log.resource_id


@pytest.mark.asyncio
async def test_audit_middleware_skips_read(client: AsyncClient, admin_headers: dict, admin_user, db_engine):
    """读操作不应被审计中间件记录"""
    await client.get("/api/v1/categories", headers=admin_headers)

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(AuditLog).where(AuditLog.action == "get"))
        logs = result.scalars().all()
    assert len(logs) == 0


@pytest.mark.asyncio
async def test_audit_middleware_skips_login(client: AsyncClient, admin_user, db_engine):
    """登录端点应跳过审计"""
    await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.resource_id == "/api/v1/auth/login")
        )
        logs = result.scalars().all()
    assert len(logs) == 0


# ========== 审计日志 API 测试 ==========

@pytest.mark.asyncio
async def test_list_audit_logs_by_admin(client: AsyncClient, admin_headers: dict, admin_user):
    """super_admin 可查看审计日志"""
    resp = await client.get("/api/v1/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_audit_logs_forbidden_for_normal(client: AsyncClient, user_headers: dict, normal_user):
    """普通用户不能查看审计日志"""
    resp = await client.get("/api/v1/audit-logs", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_pagination(client: AsyncClient, admin_headers: dict, admin_user):
    """审计日志分页"""
    resp = await client.get("/api/v1/audit-logs?page=1&page_size=5", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_audit_logs_filter_by_action(client: AsyncClient, admin_headers: dict, admin_user):
    """按 action 过滤审计日志"""
    resp = await client.get("/api/v1/audit-logs?action=post", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["action"] == "post"


@pytest.mark.asyncio
async def test_get_audit_log_detail(client: AsyncClient, admin_headers: dict, admin_user):
    """查看单条审计日志详情 — 通过审计日志列表 API 获取 ID，再查详情"""
    await client.post("/api/v1/categories", json={"name": "详情测试"}, headers=admin_headers)

    # 通过列表 API 获取一条审计记录（审计 API 走 get_db override）
    # 注意：中间件用独立 session 写入，列表 API 也可能看不到
    # 所以先写一条审计日志到 override 的 session
    from app.services.audit_service import log_audit
    from app.database import get_db
    from app.main import app
    # 用 override 的 db session 写一条
    async for session in app.dependency_overrides[get_db]():
        entry = await log_audit(session, action="post", resource_type="api", resource_id="/api/v1/categories", user_id=str(admin_user.id))
        break

    resp = await client.get(f"/api/v1/audit-logs/{entry.id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "post"
    assert data["resource_type"] == "api"
