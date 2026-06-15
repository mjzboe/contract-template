import os
import time

import pytest
from httpx import AsyncClient


async def _setup_project_with_template(client: AsyncClient, admin_headers: dict) -> tuple[str, str, dict[str, str]]:
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        tmpl_resp = await client.post(
            "/api/v1/templates",
            data={"name": "合同测试模板", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
            headers=admin_headers,
        )
    template_id = tmpl_resp.json()["template"]["id"]
    variables = tmpl_resp.json()["variables"]

    var_values = {}
    for v in variables:
        var_values[v["name"]] = f"测试{v['name']}值"

    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "合同测试项目", "template_ids": [template_id]},
        headers=admin_headers,
    )
    project_id = proj_resp.json()["id"]

    return project_id, template_id, var_values


@pytest.mark.asyncio
async def test_preview_contract(client: AsyncClient, admin_headers: dict):
    project_id, template_id, var_values = await _setup_project_with_template(client, admin_headers)
    response = await client.post(
        "/api/v1/contracts/preview",
        json={"template_id": template_id, "variables": var_values},
    )
    assert response.status_code == 200
    data = response.json()
    assert "preview_text" in data
    assert len(data["preview_text"]) > 0


@pytest.mark.asyncio
async def test_generate_contract(client: AsyncClient, admin_headers: dict):
    project_id, template_id, var_values = await _setup_project_with_template(client, admin_headers)
    response = await client.post(
        "/api/v1/contracts",
        json={
            "title": "测试合同",
            "template_id": template_id,
            "variables": var_values,
            "project_id": project_id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试合同"
    assert "id" in data


@pytest.mark.asyncio
async def test_export_word(client: AsyncClient, admin_headers: dict):
    project_id, template_id, var_values = await _setup_project_with_template(client, admin_headers)
    gen_resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "导出测试",
            "template_id": template_id,
            "variables": var_values,
            "project_id": project_id,
        },
        headers=admin_headers,
    )
    contract_id = gen_resp.json()["id"]
    response = await client.get(
        f"/api/v1/contracts/{contract_id}/export?format=word",
        headers=admin_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_parse_excel(client: AsyncClient):
    excel_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "批量导入样例.xlsx"
    )
    with open(excel_path, "rb") as f:
        response = await client.post(
            "/api/v1/contracts/parse-excel",
            files={"excel_file": ("批量导入样例.xlsx", f, "application/octet-stream")},
        )
    assert response.status_code == 200
    data = response.json()
    assert "headers" in data
    assert "rows" in data
    assert data["total_rows"] > 0


@pytest.mark.asyncio
async def test_batch_generate_from_rows_sync(client: AsyncClient, admin_headers: dict):
    project_id, template_id, _ = await _setup_project_with_template(client, admin_headers)
    rows = [
        {"公司名称": "公司A", "日期": "2024-01-01"},
        {"公司名称": "公司B", "日期": "2024-01-02"},
    ]
    response = await client.post(
        "/api/v1/contracts/batch-from-rows",
        json={
            "project_id": project_id,
            "rows": rows,
            "selected_indices": [0, 1],
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_batch_generate_from_rows_async(client: AsyncClient, admin_headers: dict):
    project_id, template_id, _ = await _setup_project_with_template(client, admin_headers)
    rows = [
        {"公司名称": "异步公司A", "日期": "2024-01-01"},
        {"公司名称": "异步公司B", "日期": "2024-01-02"},
    ]
    response = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={
            "project_id": project_id,
            "rows": rows,
            "selected_indices": [0, 1],
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] in ("pending", "running", "completed")


@pytest.mark.asyncio
async def test_get_task_status(client: AsyncClient, admin_headers: dict):
    project_id, template_id, _ = await _setup_project_with_template(client, admin_headers)
    rows = [{"公司名称": "状态测试公司", "日期": "2024-01-01"}]
    task_resp = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={"project_id": project_id, "rows": rows, "selected_indices": [0]},
        headers=admin_headers,
    )
    task_id = task_resp.json()["task_id"]
    time.sleep(2)
    response = await client.get(f"/api/v1/contracts/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("pending", "running", "completed", "failed")


@pytest.mark.asyncio
async def test_download_zip(client: AsyncClient, admin_headers: dict):
    project_id, template_id, _ = await _setup_project_with_template(client, admin_headers)
    rows = [{"公司名称": "ZIP测试公司", "日期": "2024-01-01"}]
    task_resp = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={"project_id": project_id, "rows": rows, "selected_indices": [0]},
        headers=admin_headers,
    )
    assert task_resp.status_code == 200
    task_data = task_resp.json()
    assert "task_id" in task_data
    status_resp = await client.get(f"/api/v1/contracts/tasks/{task_data['task_id']}")
    assert status_resp.status_code == 200


@pytest.mark.asyncio
async def test_contract_user_isolation(
    client: AsyncClient, user_headers: dict, admin_headers: dict
):
    """用户 A 生成的合同，用户 B 无法查看详情"""
    project_id, template_id, _ = await _setup_project_with_template(client, admin_headers)
    gen_resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "隔离测试合同",
            "template_id": template_id,
            "variables": {"公司名称": "隔离公司"},
            "project_id": project_id,
        },
        headers=admin_headers,
    )
    contract_id = gen_resp.json()["id"]
    # 普通用户无法访问 admin 的合同
    resp = await client.get(f"/api/v1/contracts/{contract_id}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contract_export_isolation(
    client: AsyncClient, user_headers: dict, admin_headers: dict
):
    """用户 B 无法导出用户 A 的合同"""
    project_id, template_id, _ = await _setup_project_with_template(client, admin_headers)
    gen_resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "导出隔离测试",
            "template_id": template_id,
            "variables": {"公司名称": "隔离公司"},
            "project_id": project_id,
        },
        headers=admin_headers,
    )
    contract_id = gen_resp.json()["id"]
    # 普通用户无法导出 admin 的合同
    resp = await client.get(
        f"/api/v1/contracts/{contract_id}/export", params={"format": "word"}, headers=user_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contract_list_user_scoping(
    client: AsyncClient, user_headers: dict, admin_headers: dict
):
    """普通用户合同列表只返回自己的"""
    project_id, template_id, _ = await _setup_project_with_template(client, admin_headers)
    # admin 生成合同
    await client.post(
        "/api/v1/contracts",
        json={
            "title": "管理员合同",
            "template_id": template_id,
            "variables": {"公司名称": "Admin"},
            "project_id": project_id,
        },
        headers=admin_headers,
    )
    # 普通用户生成合同
    await client.post(
        "/api/v1/contracts",
        json={
            "title": "用户合同",
            "template_id": template_id,
            "variables": {"公司名称": "User"},
        },
        headers=user_headers,
    )
    # 普通用户列表
    resp = await client.get("/api/v1/contracts", headers=user_headers)
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()["items"]]
    assert "管理员合同" not in titles
    assert "用户合同" in titles
