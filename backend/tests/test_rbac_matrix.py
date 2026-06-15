"""RBAC 权限矩阵测试：参数化覆盖所有受保护端点 × 角色"""
import os
import uuid

import pytest
from httpx import AsyncClient


# ========== 辅助函数 ==========

async def _create_template(client: AsyncClient, headers: dict) -> str:
    """上传模板并返回 template_id"""
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        resp = await client.post(
            "/api/v1/templates",
            data={"name": f"RBAC测试模板_{uuid.uuid4().hex[:6]}", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
            headers=headers,
        )
    assert resp.status_code == 200
    return resp.json()["template"]["id"]


async def _create_project(client: AsyncClient, headers: dict, template_id: str) -> str:
    """创建项目并返回 project_id"""
    resp = await client.post(
        "/api/v1/projects",
        json={"name": f"RBAC测试项目_{uuid.uuid4().hex[:6]}", "template_ids": [template_id]},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_contract(client: AsyncClient, headers: dict, template_id: str, project_id: str) -> str:
    """生成合同并返回 contract_id"""
    resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": f"RBAC测试合同_{uuid.uuid4().hex[:6]}",
            "template_id": template_id,
            "variables": {"公司名称": "RBAC测试公司"},
            "project_id": project_id,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ========== 1. 无 token 保护测试 ==========

NO_TOKEN_ENDPOINTS = [
    ("POST", "/api/v1/projects", {}),
    ("GET", "/api/v1/projects", None),
    ("POST", "/api/v1/contracts", {}),
    ("GET", "/api/v1/contracts", None),
    ("GET", "/api/v1/archives", None),
    ("POST", "/api/v1/templates", {}),
    ("GET", "/api/v1/audit-logs", None),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", NO_TOKEN_ENDPOINTS)
async def test_no_token_returns_401(client: AsyncClient, method: str, url: str, body):
    """无 token 时受保护端点返回 401"""
    if method == "POST":
        resp = await client.post(url, json=body)
    else:
        resp = await client.get(url)
    assert resp.status_code in (401, 403, 422), f"{method} {url} got {resp.status_code}"


# ========== 2. 角色 delete 权限测试（DELETE 端点只需 super_admin） ==========

@pytest.mark.asyncio
async def test_delete_project_by_admin(client: AsyncClient, admin_headers: dict):
    """DELETE /projects 仅 super_admin 可操作 — admin 成功"""
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_project_by_template_admin_forbidden(client: AsyncClient, admin_headers: dict, template_admin_headers: dict):
    """DELETE /projects — template_admin 被拒绝"""
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=template_admin_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_project_by_approver_forbidden(client: AsyncClient, admin_headers: dict, approver_headers: dict):
    """DELETE /projects — approver 被拒绝"""
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=approver_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_project_by_user_forbidden(client: AsyncClient, admin_headers: dict, user_headers: dict):
    """DELETE /projects — user 被拒绝"""
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_contract_by_admin(client: AsyncClient, admin_headers: dict):
    """DELETE /contracts 仅 super_admin 可操作 — admin 成功"""
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    contract_id = await _create_contract(client, admin_headers, template_id, project_id)
    resp = await client.delete(f"/api/v1/contracts/{contract_id}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_contract_by_template_admin_forbidden(client: AsyncClient, admin_headers: dict, template_admin_headers: dict):
    """DELETE /contracts — template_admin 被拒绝"""
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    contract_id = await _create_contract(client, admin_headers, template_id, project_id)
    resp = await client.delete(f"/api/v1/contracts/{contract_id}", headers=template_admin_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_contract_by_user_forbidden(client: AsyncClient, admin_headers: dict, user_headers: dict):
    """DELETE /contracts — user 被拒绝"""
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    contract_id = await _create_contract(client, admin_headers, template_id, project_id)
    resp = await client.delete(f"/api/v1/contracts/{contract_id}", headers=user_headers)
    assert resp.status_code == 403


# ========== 3. 资源隔离测试：_can_access / _can_access_contract ==========

@pytest.mark.asyncio
async def test_project_owner_can_access(client: AsyncClient, user_headers: dict, sample_template):
    """项目创建者可以查看自己的项目"""
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "用户A的项目", "template_ids": [template_id]},
        headers=user_headers,
    )
    project_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/projects/{project_id}", headers=user_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_project_non_owner_cannot_access(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """非创建者（普通用户）无法查看他人项目"""
    template_id, _ = sample_template
    # admin 创建项目
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "管理员的项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    # 普通用户尝试访问
    resp = await client.get(f"/api/v1/projects/{project_id}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_project_admin_can_access_any(client: AsyncClient, admin_headers: dict, user_headers: dict, sample_template):
    """管理员可以访问任何用户的项目"""
    template_id, _ = sample_template
    # 普通用户创建项目
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "普通用户项目", "template_ids": [template_id]},
        headers=user_headers,
    )
    project_id = create_resp.json()["id"]
    # admin 访问
    resp = await client.get(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_contract_owner_can_access(
    client: AsyncClient, user_headers: dict, sample_template
):
    """合同创建者可以查看自己的合同"""
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "用户A合同", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=user_headers,
    )
    contract_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/contracts/{contract_id}", headers=user_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_contract_non_owner_cannot_access(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """非创建者无法查看他人合同"""
    template_id, _ = sample_template
    # admin 生成合同
    create_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "管理员合同", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=admin_headers,
    )
    contract_id = create_resp.json()["id"]
    # 普通用户尝试访问
    resp = await client.get(f"/api/v1/contracts/{contract_id}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contract_admin_can_access_any(
    client: AsyncClient, admin_headers: dict, user_headers: dict, sample_template
):
    """管理员可以访问任何用户的合同"""
    template_id, _ = sample_template
    # 普通用户生成合同
    create_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "用户合同", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=user_headers,
    )
    contract_id = create_resp.json()["id"]
    # admin 访问
    resp = await client.get(f"/api/v1/contracts/{contract_id}", headers=admin_headers)
    assert resp.status_code == 200


# ========== 4. 列表用户隔离：普通用户只看自己的 ==========

@pytest.mark.asyncio
async def test_project_list_user_scoping(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """普通用户项目列表只返回自己创建的"""
    template_id, _ = sample_template
    # admin 创建项目
    await client.post(
        "/api/v1/projects",
        json={"name": "管理员项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    # 普通用户创建项目
    await client.post(
        "/api/v1/projects",
        json={"name": "用户项目", "template_ids": [template_id]},
        headers=user_headers,
    )
    # 普通用户列表
    resp = await client.get("/api/v1/projects", headers=user_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["name"] != "管理员项目" for item in items)


@pytest.mark.asyncio
async def test_project_list_admin_sees_all(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """管理员项目列表可看到所有用户的项目"""
    template_id, _ = sample_template
    # admin 和 普通用户各创建项目
    await client.post(
        "/api/v1/projects",
        json={"name": "管理员项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/projects",
        json={"name": "用户项目", "template_ids": [template_id]},
        headers=user_headers,
    )
    # admin 列表
    resp = await client.get("/api/v1/projects", headers=admin_headers)
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()["items"]]
    assert "管理员项目" in names
    assert "用户项目" in names


@pytest.mark.asyncio
async def test_contract_list_user_scoping(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """普通用户合同列表只返回自己创建的"""
    template_id, _ = sample_template
    # admin 生成合同
    await client.post(
        "/api/v1/contracts",
        json={"title": "管理员合同", "template_id": template_id, "variables": {"公司名称": "Admin"}},
        headers=admin_headers,
    )
    # 普通用户生成合同
    await client.post(
        "/api/v1/contracts",
        json={"title": "用户合同", "template_id": template_id, "variables": {"公司名称": "User"}},
        headers=user_headers,
    )
    # 普通用户列表
    resp = await client.get("/api/v1/contracts", headers=user_headers)
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()["items"]]
    assert "管理员合同" not in titles
    assert "用户合同" in titles


@pytest.mark.asyncio
async def test_archive_list_user_scoping(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """普通用户归档列表只返回自己创建的"""
    template_id, _ = sample_template
    # admin 生成合同（自动归档）
    await client.post(
        "/api/v1/contracts",
        json={"title": "管理员归档", "template_id": template_id, "variables": {"公司名称": "Admin"}},
        headers=admin_headers,
    )
    # 普通用户生成合同
    await client.post(
        "/api/v1/contracts",
        json={"title": "用户归档", "template_id": template_id, "variables": {"公司名称": "User"}},
        headers=user_headers,
    )
    # 普通用户归档列表
    resp = await client.get("/api/v1/archives", headers=user_headers)
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()["items"]]
    assert "管理员归档" not in titles
    assert "用户归档" in titles


@pytest.mark.asyncio
async def test_archive_non_owner_cannot_access(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """非创建者无法查看他人归档详情"""
    template_id, _ = sample_template
    # admin 生成合同
    create_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "管理员归档详情", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=admin_headers,
    )
    contract_id = create_resp.json()["id"]
    # 普通用户尝试访问归档详情
    resp = await client.get(f"/api/v1/archives/{contract_id}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_archive_download_non_owner_cannot_access(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """非创建者无法下载他人归档文件"""
    template_id, _ = sample_template
    # admin 生成合同
    create_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "管理员归档下载", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=admin_headers,
    )
    contract_id = create_resp.json()["id"]
    # 普通用户尝试下载
    resp = await client.get(
        f"/api/v1/archives/{contract_id}/download", params={"format": "word"}, headers=user_headers
    )
    assert resp.status_code == 403


# ========== 5. 项目更新隔离测试 ==========

@pytest.mark.asyncio
async def test_project_non_owner_cannot_update(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """非创建者无法更新他人项目"""
    template_id, _ = sample_template
    # admin 创建项目
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "管理员项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    # 普通用户尝试更新
    resp = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "被篡改的名称"},
        headers=user_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contract_export_non_owner_cannot_access(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template
):
    """非创建者无法导出他人合同"""
    template_id, _ = sample_template
    # admin 生成合同
    create_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "管理员合同导出", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=admin_headers,
    )
    contract_id = create_resp.json()["id"]
    # 普通用户尝试导出
    resp = await client.get(
        f"/api/v1/contracts/{contract_id}/export", params={"format": "word"}, headers=user_headers
    )
    assert resp.status_code == 403
