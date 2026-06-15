import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, admin_headers: dict, sample_template):
    template_id, _ = sample_template
    response = await client.post(
        "/api/v1/projects",
        json={"name": "测试项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试项目"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, admin_headers: dict, sample_template):
    template_id, _ = sample_template
    await client.post(
        "/api/v1/projects",
        json={"name": "项目列表测试", "template_ids": [template_id]},
        headers=admin_headers,
    )
    response = await client.get("/api/v1/projects", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_project_detail(client: AsyncClient, admin_headers: dict, sample_template):
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "项目详情测试", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert len(data["templates"]) >= 1


@pytest.mark.asyncio
async def test_get_deduplicated_variables(client: AsyncClient, admin_headers: dict, sample_template):
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "去重测试", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "variables" in data
    assert "variable_sources" in data
    assert data["total_variables_after_dedup"] <= data["total_variables_before_dedup"]


@pytest.mark.asyncio
async def test_dedup_with_multiple_templates(client: AsyncClient, admin_headers: dict):
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
    template_ids = []
    for filename in ["签字页模板_股东会决议.docx", "签字页模板_董事会决议.docx"]:
        path = os.path.join(samples_dir, filename)
        with open(path, "rb") as f:
            resp = await client.post(
                "/api/v1/templates",
                data={"name": filename.replace(".docx", ""), "tags": "[]"},
                files={"file": (filename, f, "application/octet-stream")},
                headers=admin_headers,
            )
        template_ids.append(resp.json()["template"]["id"])

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "多模板去重", "template_ids": template_ids},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    dedup_resp = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables", headers=admin_headers)
    data = dedup_resp.json()
    shared_vars = {
        name: sources for name, sources in data["variable_sources"].items()
        if len(sources) > 1
    }
    assert data["total_variables_after_dedup"] < data["total_variables_before_dedup"] or len(shared_vars) > 0


@pytest.mark.asyncio
async def test_update_project_name(client: AsyncClient, admin_headers: dict, sample_template):
    """更新项目名称"""
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "原始名称", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "更新后名称"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新后名称"


@pytest.mark.asyncio
async def test_update_project_templates_re_dedup(client: AsyncClient, admin_headers: dict):
    """更新关联模板后变量自动重新去重"""
    import os
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
    # 上传两个模板
    template_ids = []
    for filename in ["签字页模板_股东会决议.docx", "签字页模板_董事会决议.docx"]:
        path = os.path.join(samples_dir, filename)
        with open(path, "rb") as f:
            resp = await client.post(
                "/api/v1/templates",
                data={"name": filename.replace(".docx", ""), "tags": "[]"},
                files={"file": (filename, f, "application/octet-stream")},
                headers=admin_headers,
            )
        template_ids.append(resp.json()["template"]["id"])

    # 只关联第一个模板创建项目
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "去重更新测试", "template_ids": [template_ids[0]]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]

    # 获取初始变量数
    dedup_resp = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables", headers=admin_headers)
    initial_count = dedup_resp.json()["total_variables_after_dedup"]

    # 更新关联模板为两个
    resp = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"template_ids": template_ids},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # 验证变量数变化
    dedup_resp2 = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables", headers=admin_headers)
    data = dedup_resp2.json()
    assert data["template_count"] == 2
    # 跨模板共享变量应在 variable_sources 中出现
    shared_vars = {k: v for k, v in data["variable_sources"].items() if len(v) > 1}
    assert len(shared_vars) > 0, "多模板关联后应有共享变量"


@pytest.mark.asyncio
async def test_update_project_status(client: AsyncClient, admin_headers: dict, sample_template):
    """更新项目状态"""
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "状态测试", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"status": "active"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_delete_project_by_admin_crud(client: AsyncClient, admin_headers: dict, sample_template):
    """super_admin 删除项目成功"""
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "待删除项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert resp.status_code == 200
    # 确认已删除
    get_resp = await client.get(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_projects_keyword_filter(client: AsyncClient, admin_headers: dict, sample_template):
    """关键词搜索过滤项目"""
    template_id, _ = sample_template
    await client.post(
        "/api/v1/projects",
        json={"name": "Alpha项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/projects",
        json={"name": "Beta项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    resp = await client.get("/api/v1/projects", params={"keyword": "Alpha"}, headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all("Alpha" in item["name"] for item in items)


@pytest.mark.asyncio
async def test_list_projects_status_filter(client: AsyncClient, admin_headers: dict, sample_template):
    """状态过滤项目"""
    template_id, _ = sample_template
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "状态过滤测试", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    # 更新状态为 active
    await client.put(f"/api/v1/projects/{project_id}", json={"status": "active"}, headers=admin_headers)
    # 过滤 active 状态
    resp = await client.get("/api/v1/projects", params={"status": "active"}, headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["status"] == "active" for item in items)
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
    template_ids = []
    for filename in ["签字页模板_股东会决议.docx", "签字页模板_董事会决议.docx"]:
        path = os.path.join(samples_dir, filename)
        with open(path, "rb") as f:
            resp = await client.post(
                "/api/v1/templates",
                data={"name": filename.replace(".docx", ""), "tags": "[]"},
                files={"file": (filename, f, "application/octet-stream")},
                headers=admin_headers,
            )
        template_ids.append(resp.json()["template"]["id"])

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "多模板去重", "template_ids": template_ids},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    dedup_resp = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables", headers=admin_headers)
    data = dedup_resp.json()
    shared_vars = {
        name: sources for name, sources in data["variable_sources"].items()
        if len(sources) > 1
    }
    assert data["total_variables_after_dedup"] < data["total_variables_before_dedup"] or len(shared_vars) > 0
