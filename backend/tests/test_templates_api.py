import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient, admin_headers: dict):
    response = await client.post("/api/v1/categories", json={"name": "IPO签字页"}, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "IPO签字页"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, admin_headers: dict):
    await client.post("/api/v1/categories", json={"name": "分类A"}, headers=admin_headers)
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_upload_template(client: AsyncClient, admin_headers: dict):
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        response = await client.post(
            "/api/v1/templates",
            data={"name": "上传测试模板", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
            headers=admin_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert "template" in data
    assert "variables" in data
    assert len(data["variables"]) > 0


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient, sample_template):
    response = await client.get("/api/v1/templates")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_template_detail(client: AsyncClient, sample_template):
    template_id, _ = sample_template
    response = await client.get(f"/api/v1/templates/{template_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_id
    assert "versions" in data


@pytest.mark.asyncio
async def test_delete_template(client: AsyncClient, admin_headers: dict, sample_template):
    template_id, _ = sample_template
    response = await client.delete(f"/api/v1/templates/{template_id}", headers=admin_headers)
    assert response.status_code == 200
    response = await client.get(f"/api/v1/templates/{template_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_template_variables(client: AsyncClient, sample_template):
    template_id, _ = sample_template
    response = await client.get(f"/api/v1/templates/{template_id}/variables")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "name" in data[0]
