"""端到端流程测试：完整业务链路"""

import os
import time

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_e2e_flow(client: AsyncClient, admin_headers: dict):
    # 1. 创建分类
    cat_resp = await client.post("/api/v1/categories", json={"name": "IPO签字页"}, headers=admin_headers)
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    # 2. 上传3个模板
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
    template_ids = []
    template_names = [
        "签字页模板_股东会决议.docx",
        "签字页模板_董事会决议.docx",
        "签字页模板_律师见证函.docx",
    ]
    for filename in template_names:
        path = os.path.join(samples_dir, filename)
        with open(path, "rb") as f:
            resp = await client.post(
                "/api/v1/templates",
                data={"name": filename.replace(".docx", ""), "tags": "[]", "category_id": str(category_id)},
                files={"file": (filename, f, "application/octet-stream")},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        template_ids.append(resp.json()["template"]["id"])
        assert len(resp.json()["variables"]) > 0

    # 3. 创建项目，关联3个模板
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "E2E测试-IPO签字页", "template_ids": template_ids},
        headers=admin_headers,
    )
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["id"]

    # 4. 获取去重变量
    dedup_resp = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables", headers=admin_headers)
    assert dedup_resp.status_code == 200
    dedup_data = dedup_resp.json()
    assert dedup_data["template_count"] == 3
    assert dedup_data["total_variables_after_dedup"] <= dedup_data["total_variables_before_dedup"]

    # 5. 填充变量并生成合同
    var_values = {}
    for v in dedup_data["variables"]:
        var_values[v["name"]] = f"E2E测试{v['name']}"

    contract_resp = await client.post(
        "/api/v1/contracts",
        json={
            "title": "E2E测试合同",
            "template_id": template_ids[0],
            "variables": var_values,
            "project_id": project_id,
        },
        headers=admin_headers,
    )
    assert contract_resp.status_code == 200
    contract_id = contract_resp.json()["id"]

    # 6. 导出 Word
    export_resp = await client.get(f"/api/v1/contracts/{contract_id}/export?format=word", headers=admin_headers)
    assert export_resp.status_code == 200

    # 7. 上传 Excel → 解析
    excel_path = os.path.join(samples_dir, "批量导入样例.xlsx")
    with open(excel_path, "rb") as f:
        excel_resp = await client.post(
            "/api/v1/contracts/parse-excel",
            files={"excel_file": ("批量导入样例.xlsx", f, "application/octet-stream")},
        )
    assert excel_resp.status_code == 200
    excel_data = excel_resp.json()
    assert excel_data["total_rows"] > 0

    # 8. 批量同步生成（验证同步模式可以端到端完成）
    batch_sync_resp = await client.post(
        "/api/v1/contracts/batch-from-rows",
        json={
            "project_id": project_id,
            "rows": excel_data["rows"],
            "selected_indices": list(range(min(2, excel_data["total_rows"]))),
        },
        headers=admin_headers,
    )
    assert batch_sync_resp.status_code == 200
    batch_contracts = batch_sync_resp.json()
    assert len(batch_contracts) >= 2
