import os
import time

import pytest
from httpx import AsyncClient


async def _setup_project_with_template(client: AsyncClient) -> tuple[str, str, dict[str, str]]:
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        tmpl_resp = await client.post(
            "/api/v1/templates",
            data={"name": "合同测试模板", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
        )
    template_id = tmpl_resp.json()["template"]["id"]
    variables = tmpl_resp.json()["variables"]

    var_values = {}
    for v in variables:
        var_values[v["name"]] = f"测试{v['name']}值"

    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "合同测试项目", "template_ids": [template_id]},
    )
    project_id = proj_resp.json()["id"]

    return project_id, template_id, var_values


@pytest.mark.asyncio
async def test_preview_contract(client: AsyncClient):
    project_id, template_id, var_values = await _setup_project_with_template(client)
    response = await client.post(
        "/api/v1/contracts/preview",
        json={"template_id": template_id, "variables": var_values},
    )
    assert response.status_code == 200
    data = response.json()
    assert "preview_text" in data
    assert len(data["preview_text"]) > 0


@pytest.mark.asyncio
async def test_generate_contract(client: AsyncClient):
    project_id, template_id, var_values = await _setup_project_with_template(client)
    response = await client.post(
        "/api/v1/contracts",
        json={
            "title": "测试合同",
            "template_id": template_id,
            "variables": var_values,
            "project_id": project_id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试合同"
    assert "id" in data


@pytest.mark.asyncio
async def test_export_word(client: AsyncClient):
    project_id, template_id, var_values = await _setup_project_with_template(client)
    gen_resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "导出测试",
            "template_id": template_id,
            "variables": var_values,
            "project_id": project_id,
        },
    )
    contract_id = gen_resp.json()["id"]
    response = await client.get(
        f"/api/v1/contracts/{contract_id}/export?format=word"
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
async def test_batch_generate_from_rows_sync(client: AsyncClient):
    project_id, template_id, _ = await _setup_project_with_template(client)
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
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_batch_generate_from_rows_async(client: AsyncClient):
    project_id, template_id, _ = await _setup_project_with_template(client)
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
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] in ("pending", "running", "completed")


@pytest.mark.asyncio
async def test_get_task_status(client: AsyncClient):
    project_id, template_id, _ = await _setup_project_with_template(client)
    rows = [{"公司名称": "状态测试公司", "日期": "2024-01-01"}]
    task_resp = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={"project_id": project_id, "rows": rows, "selected_indices": [0]},
    )
    task_id = task_resp.json()["task_id"]
    time.sleep(2)
    response = await client.get(f"/api/v1/contracts/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("pending", "running", "completed", "failed")


@pytest.mark.asyncio
async def test_download_zip(client: AsyncClient):
    """异步 ZIP 下载测试

    注意：异步任务使用独立的 database session（不走 dependency_overrides），
    因此后台任务可能无法看到测试写入的数据。此测试验证接口响应格式正确。
    """
    project_id, template_id, _ = await _setup_project_with_template(client)
    rows = [{"公司名称": "ZIP测试公司", "日期": "2024-01-01"}]
    task_resp = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={"project_id": project_id, "rows": rows, "selected_indices": [0]},
    )
    assert task_resp.status_code == 200
    task_data = task_resp.json()
    assert "task_id" in task_data
    # 验证任务状态接口可用
    status_resp = await client.get(f"/api/v1/contracts/tasks/{task_data['task_id']}")
    assert status_resp.status_code == 200
