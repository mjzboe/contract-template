import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, sample_template):
    template_id, _ = sample_template
    response = await client.post(
        "/api/v1/projects",
        json={"name": "测试项目", "template_ids": [template_id]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试项目"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, sample_template):
    template_id, _ = sample_template
    await client.post(
        "/api/v1/projects",
        json={"name": "项目列表测试", "template_ids": [template_id]},
    )
    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_project_detail(client: AsyncClient, sample_template):
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "项目详情测试", "template_ids": [template_id]},
    )
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert len(data["templates"]) >= 1


@pytest.mark.asyncio
async def test_get_deduplicated_variables(client: AsyncClient, sample_template):
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "去重测试", "template_ids": [template_id]},
    )
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables")
    assert response.status_code == 200
    data = response.json()
    assert "variables" in data
    assert "variable_sources" in data
    assert data["total_variables_after_dedup"] <= data["total_variables_before_dedup"]


@pytest.mark.asyncio
async def test_dedup_with_multiple_templates(client: AsyncClient):
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
    template_ids = []
    for filename in ["签字页模板_股东会决议.docx", "签字页模板_董事会决议.docx"]:
        path = os.path.join(samples_dir, filename)
        with open(path, "rb") as f:
            resp = await client.post(
                "/api/v1/templates",
                data={"name": filename.replace(".docx", ""), "tags": "[]"},
                files={"file": (filename, f, "application/octet-stream")},
            )
        template_ids.append(resp.json()["template"]["id"])

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "多模板去重", "template_ids": template_ids},
    )
    project_id = create_resp.json()["id"]
    dedup_resp = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables")
    data = dedup_resp.json()
    shared_vars = {
        name: sources for name, sources in data["variable_sources"].items()
        if len(sources) > 1
    }
    assert data["total_variables_after_dedup"] < data["total_variables_before_dedup"] or len(shared_vars) > 0
