"""档案归档 API 测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_archives_empty(client: AsyncClient, admin_headers: dict):
    """归档列表 — 无归档记录时返回空列表"""
    resp = await client.get("/api/v1/archives", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_archives_with_data(
    client: AsyncClient, admin_headers: dict, sample_template: tuple
):
    """归档列表 — 生成合同后自动归档，列表可查"""
    template_id, _ = sample_template

    resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "归档测试合同",
            "template_id": template_id,
            "variables": {"公司名称": "测试公司", "法定代表人": "张三"},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    contract = resp.json()
    assert contract["status"] == "archived"

    resp = await client.get("/api/v1/archives", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(item["title"] == "归档测试合同" for item in data["items"])


@pytest.mark.asyncio
async def test_list_archives_keyword_filter(
    client: AsyncClient, admin_headers: dict, sample_template: tuple
):
    """归档列表 — 关键词过滤"""
    template_id, _ = sample_template

    await client.post(
        "/api/v1/contracts",
        json={
            "title": "关键词测试_Alpha",
            "template_id": template_id,
            "variables": {"公司名称": "Alpha公司"},
        },
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/contracts",
        json={
            "title": "关键词测试_Beta",
            "template_id": template_id,
            "variables": {"公司名称": "Beta公司"},
        },
        headers=admin_headers,
    )

    resp = await client.get(
        "/api/v1/archives", params={"keyword": "Alpha"}, headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all("Alpha" in item["title"] for item in data["items"])


@pytest.mark.asyncio
async def test_list_archives_template_filter(
    client: AsyncClient, admin_headers: dict, sample_template: tuple
):
    """归档列表 — 模板过滤"""
    template_id, _ = sample_template

    await client.post(
        "/api/v1/contracts",
        json={
            "title": "模板过滤测试",
            "template_id": template_id,
            "variables": {"公司名称": "测试公司"},
        },
        headers=admin_headers,
    )

    resp = await client.get(
        "/api/v1/archives", params={"template_id": template_id}, headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["template_id"] == template_id for item in data["items"])


@pytest.mark.asyncio
async def test_get_archive_detail(
    client: AsyncClient, admin_headers: dict, sample_template: tuple
):
    """归档详情 — 包含 status_history 时间线"""
    template_id, _ = sample_template

    resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "详情测试合同",
            "template_id": template_id,
            "variables": {"公司名称": "详情公司", "法定代表人": "李四"},
        },
        headers=admin_headers,
    )
    contract = resp.json()
    contract_id = contract["id"]

    resp = await client.get(f"/api/v1/archives/{contract_id}", headers=admin_headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["title"] == "详情测试合同"
    assert detail["status"] == "archived"
    assert detail["archived_at"] is not None
    assert len(detail["status_history"]) >= 2
    assert detail["variables"]["公司名称"] == "详情公司"
    assert detail["template_name"] is not None


@pytest.mark.asyncio
async def test_get_archive_detail_not_found(client: AsyncClient, admin_headers: dict):
    """归档详情 — 不存在的 ID 返回 404"""
    resp = await client.get("/api/v1/archives/00000000-0000-0000-0000-000000000000", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_archive(
    client: AsyncClient, admin_headers: dict, sample_template: tuple
):
    """下载归档文件"""
    template_id, _ = sample_template

    resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "下载测试合同",
            "template_id": template_id,
            "variables": {"公司名称": "下载公司"},
        },
        headers=admin_headers,
    )
    contract = resp.json()
    contract_id = contract["id"]

    resp = await client.get(
        f"/api/v1/archives/{contract_id}/download", params={"format": "word"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_archives_require_auth(client: AsyncClient):
    """归档 API 需要认证"""
    resp = await client.get("/api/v1/archives")
    assert resp.status_code in (401, 403)
