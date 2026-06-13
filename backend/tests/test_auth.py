"""认证与 RBAC 权限测试"""
import pytest
from httpx import AsyncClient

from app.utils.security import hash_password, verify_password, create_access_token, decode_access_token


# ========== 密码工具测试 ==========

def test_hash_and_verify_password():
    hashed = hash_password("test123")
    assert verify_password("test123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_access_token({"sub": "user-123", "role": "admin"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"


def test_decode_invalid_token():
    payload = decode_access_token("invalid.token.here")
    assert payload is None


def test_decode_expired_token():
    from datetime import timedelta
    token = create_access_token({"sub": "user"}, expires_delta=timedelta(seconds=-1))
    payload = decode_access_token(token)
    assert payload is None


# ========== 登录 API 测试 ==========

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session):
    from app.services.auth_service import create_user, toggle_user_active
    user = await create_user(db_session, "inactive", "inactive@test.com", "pass123", "user")
    await toggle_user_active(db_session, str(user.id))
    resp = await client.post("/api/v1/auth/login", json={"username": "inactive", "password": "pass123"})
    assert resp.status_code == 401


# ========== /me 端点测试 ==========

@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, admin_headers: dict, admin_user):
    resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "super_admin"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


# ========== init-admin 测试 ==========

@pytest.mark.asyncio
async def test_init_admin_creates_default(client: AsyncClient):
    resp = await client.post("/api/v1/auth/init-admin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "super_admin"


@pytest.mark.asyncio
async def test_init_admin_idempotent(client: AsyncClient, admin_user):
    resp = await client.post("/api/v1/auth/init-admin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"


# ========== 注册（需 super_admin 权限）==========

@pytest.mark.asyncio
async def test_register_by_admin(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "newuser", "email": "new@test.com", "password": "pass123", "role": "user"
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_register_forbidden_for_normal_user(client: AsyncClient, user_headers: dict, normal_user):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "another", "email": "another@test.com", "password": "pass123", "role": "user"
    }, headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, admin_headers: dict, admin_user):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "admin", "email": "other@test.com", "password": "pass123", "role": "user"
    }, headers=admin_headers)
    assert resp.status_code == 400


# ========== 用户管理 API 权限测试 ==========

@pytest.mark.asyncio
async def test_list_users_by_admin(client: AsyncClient, admin_headers: dict, admin_user):
    resp = await client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_users_forbidden_for_normal(client: AsyncClient, user_headers: dict, normal_user):
    resp = await client.get("/api/v1/users", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_change_user_role_by_admin(client: AsyncClient, admin_headers: dict, admin_user, normal_user):
    resp = await client.put(f"/api/v1/users/{normal_user.id}/role", json={"role": "approver"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "approver"


@pytest.mark.asyncio
async def test_change_user_role_invalid(client: AsyncClient, admin_headers: dict, admin_user, normal_user):
    resp = await client.put(f"/api/v1/users/{normal_user.id}/role", json={"role": "invalid_role"}, headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_toggle_user_active_by_admin(client: AsyncClient, admin_headers: dict, admin_user, normal_user):
    resp = await client.put(f"/api/v1/users/{normal_user.id}/toggle-active", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_toggle_active_forbidden_for_normal(client: AsyncClient, user_headers: dict, normal_user):
    resp = await client.put(f"/api/v1/users/{normal_user.id}/toggle-active", headers=user_headers)
    assert resp.status_code == 403


# ========== 模板管理 RBAC 测试 ==========

@pytest.mark.asyncio
async def test_create_template_by_template_admin(client: AsyncClient, template_admin_headers: dict, template_admin_user):
    import os
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx")
    with open(sample_path, "rb") as f:
        resp = await client.post(
            "/api/v1/templates",
            data={"name": "模板管理员上传", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
            headers=template_admin_headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_template_forbidden_for_normal_user(client: AsyncClient, user_headers: dict, normal_user):
    import os
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx")
    with open(sample_path, "rb") as f:
        resp = await client.post(
            "/api/v1/templates",
            data={"name": "普通用户尝试上传", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
            headers=user_headers,
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_template_forbidden_for_normal(client: AsyncClient, user_headers: dict, normal_user, sample_template):
    tid, _ = sample_template
    resp = await client.delete(f"/api/v1/templates/{tid}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_project_forbidden_for_normal(client: AsyncClient, user_headers: dict, normal_user, admin_headers: dict):
    """普通用户不能删除项目（仅 super_admin）"""
    import os
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx")
    with open(sample_path, "rb") as f:
        tmpl_resp = await client.post(
            "/api/v1/templates",
            data={"name": "项目删除测试", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
            headers=admin_headers,
        )
    tid = tmpl_resp.json()["template"]["id"]
    proj_resp = await client.post("/api/v1/projects", json={"name": "测试项目", "template_ids": [tid]}, headers=admin_headers)
    pid = proj_resp.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{pid}", headers=user_headers)
    assert resp.status_code == 403


# ========== 无 token 访问受保护端点 ==========

@pytest.mark.asyncio
async def test_protected_endpoints_without_token(client: AsyncClient):
    """无 token 时受保护端点返回 401/403"""
    endpoints = [
        ("POST", "/api/v1/templates"),
        ("PUT", "/api/v1/templates/00000000-0000-0000-0000-000000000000"),
        ("DELETE", "/api/v1/templates/00000000-0000-0000-0000-000000000000"),
        ("POST", "/api/v1/projects"),
        ("DELETE", "/api/v1/projects/00000000-0000-0000-0000-000000000000"),
        ("POST", "/api/v1/contracts"),
        ("GET", "/api/v1/audit-logs"),
    ]
    for method, url in endpoints:
        if method == "POST":
            resp = await client.post(url, json={})
        elif method == "PUT":
            resp = await client.put(url, json={})
        else:
            resp = await client.delete(url) if method == "DELETE" else await client.get(url)
        assert resp.status_code in (401, 403, 422), f"{method} {url} expected 401/403/422, got {resp.status_code}"
