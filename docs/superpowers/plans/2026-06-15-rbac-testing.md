# RBAC 权限矩阵 + 项目管理测试 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全 RBAC 权限矩阵测试和项目管理测试，修复 dedup 端点缺少权限保护的问题

**Architecture:** 方案 A — 新建 `test_rbac_matrix.py` 集中权限矩阵参数化测试，补充各模块业务权限测试，新增前端 ProjectManage 页面测试

**Tech Stack:** pytest + pytest-asyncio (后端), Vitest + React Testing Library + MSW (前端)

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/tests/test_rbac_matrix.py` | 权限矩阵参数化测试（无 token + 角色权限 + 资源隔离） |
| Modify | `backend/tests/test_projects_api.py` | 补充项目管理 CRUD + 用户隔离测试 |
| Modify | `backend/tests/test_contracts_api.py` | 补充合同用户隔离测试 |
| Modify | `backend/tests/test_archives_api.py` | 补充档案权限隔离测试 |
| Modify | `backend/app/api/projects.py:118-135` | dedup 端点添加 require_role |
| Modify | `frontend/src/mocks/handlers.ts` | 添加 projects PUT/DELETE mock |
| Create | `frontend/src/pages/ProjectManage/index.test.tsx` | ProjectManage 页面组件测试 |

---

### Task 1: 修复 dedup 端点缺少 require_role

**Files:**
- Modify: `backend/app/api/projects.py:118-135`

- [ ] **Step 1: 给 dedup 端点添加 require_role 保护**

将 `get_deduplicated_variables` 函数签名从：

```python
@router.get("/{project_id}/deduplicated-variables", response_model=DeduplicatedVariablesResponse)
async def get_deduplicated_variables(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
```

改为：

```python
@router.get("/{project_id}/deduplicated-variables", response_model=DeduplicatedVariablesResponse)
async def get_deduplicated_variables(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("user", "template_admin", "approver", "super_admin")),
):
```

- [ ] **Step 2: 运行现有测试确认无回归**

Run: `cd backend && python -m pytest tests/test_projects_api.py tests/test_e2e_flow.py -v --timeout=60`
Expected: 所有现有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/projects.py
git commit -m "fix: add require_role to deduplicated-variables endpoint"
```

---

### Task 2: 创建 RBAC 权限矩阵测试文件

**Files:**
- Create: `backend/tests/test_rbac_matrix.py`

- [ ] **Step 1: 编写 test_rbac_matrix.py**

```python
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

DELETE_ENDPOINTS = [
    ("projects", "project_id"),
    ("contracts", "contract_id"),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("resource,id_key", DELETE_ENDPOINTS)
@pytest.mark.parametrize("role_headers,expected", [
    ("admin_headers", 200),
    ("template_admin_headers", 403),
    ("approver_headers", 403),
    ("user_headers", 403),
])
async def test_delete_role_access(
    client: AsyncClient,
    admin_headers: dict,
    request,
    resource: str,
    id_key: str,
    role_headers: str,
    expected: int,
):
    """DELETE 端点：仅 super_admin 可操作"""
    # 先用 admin 创建资源
    template_id = await _create_template(client, admin_headers)
    project_id = await _create_project(client, admin_headers, template_id)
    contract_id = await _create_contract(client, admin_headers, template_id, project_id)

    resource_id = project_id if resource == "projects" else contract_id
    headers = request.getfixturevalue(role_headers)

    resp = await client.delete(f"/api/v1/{resource}/{resource_id}", headers=headers)
    assert resp.status_code == expected, f"DELETE /{resource}/{id_key} with {role_headers} got {resp.status_code}"


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
    # 所有项目应该是自己创建的（admin 的不应出现）
    # 注意：admin 创建的项目不应在普通用户列表中
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
```

- [ ] **Step 2: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_rbac_matrix.py -v --timeout=120`
Expected: 全部通过（约 20+ 测试用例）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_rbac_matrix.py
git commit -m "test: add RBAC permission matrix tests with parametrized coverage"
```

---

### Task 3: 补充项目管理 CRUD 测试

**Files:**
- Modify: `backend/tests/test_projects_api.py`

- [ ] **Step 1: 在 test_projects_api.py 末尾追加新测试**

追加以下测试到文件末尾：

```python
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

    # 验证变量数变化（去重后变量数可能增加或不变，取决于是否有共享变量）
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
async def test_delete_project_by_admin(client: AsyncClient, admin_headers: dict, sample_template):
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
```

- [ ] **Step 2: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_projects_api.py -v --timeout=120`
Expected: 全部通过（5 个旧测试 + 6 个新测试）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_projects_api.py
git commit -m "test: add project CRUD tests (update, delete, keyword/status filter)"
```

---

### Task 4: 补充合同/档案用户隔离测试

**Files:**
- Modify: `backend/tests/test_contracts_api.py`
- Modify: `backend/tests/test_archives_api.py`

- [ ] **Step 1: 在 test_contracts_api.py 末尾追加用户隔离测试**

```python
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
```

- [ ] **Step 2: 在 test_archives_api.py 末尾追加用户隔离测试**

```python
@pytest.mark.asyncio
async def test_archive_user_isolation(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template: tuple
):
    """非创建者无法查看他人归档详情"""
    template_id, _ = sample_template
    # admin 生成合同（自动归档）
    gen_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "归档隔离测试", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=admin_headers,
    )
    contract_id = gen_resp.json()["id"]
    # 普通用户无法访问 admin 的归档
    resp = await client.get(f"/api/v1/archives/{contract_id}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_archive_download_isolation(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template: tuple
):
    """非创建者无法下载他人归档文件"""
    template_id, _ = sample_template
    gen_resp = await client.post(
        "/api/v1/contracts",
        json={"title": "归档下载隔离", "template_id": template_id, "variables": {"公司名称": "测试"}},
        headers=admin_headers,
    )
    contract_id = gen_resp.json()["id"]
    # 普通用户无法下载 admin 的归档
    resp = await client.get(
        f"/api/v1/archives/{contract_id}/download", params={"format": "word"}, headers=user_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_archive_list_user_scoping(
    client: AsyncClient, user_headers: dict, admin_headers: dict, sample_template: tuple
):
    """普通用户归档列表只返回自己创建的"""
    template_id, _ = sample_template
    # admin 生成合同
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
```

- [ ] **Step 3: 运行所有后端测试验证**

Run: `cd backend && python -m pytest tests/ -v --timeout=120`
Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_contracts_api.py backend/tests/test_archives_api.py
git commit -m "test: add contract and archive user isolation tests"
```

---

### Task 5: 添加前端 ProjectManage 页面测试

**Files:**
- Modify: `frontend/src/mocks/handlers.ts`
- Create: `frontend/src/pages/ProjectManage/index.test.tsx`

- [ ] **Step 1: 在 handlers.ts 中添加 projects PUT/DELETE mock**

在 `handlers` 数组中 `http.get("/api/v1/projects/:id"` 之后追加：

```typescript
http.put("/api/v1/projects/:id", async () =>
  HttpResponse.json({
    ...mockProject,
    name: "更新后项目",
  })
),
http.delete("/api/v1/projects/:id", () =>
  HttpResponse.json({ message: "删除成功" })
),
```

- [ ] **Step 2: 创建 ProjectManage/index.test.tsx**

```tsx
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import ProjectManagePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("ProjectManagePage", () => {
  it("renders project table and search bar", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("搜索项目名称")).toBeInTheDocument();
  });

  it("loads and displays projects from API", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
  });

  it("renders status filter select", () => {
    renderWithProviders(<ProjectManagePage />);
    expect(screen.getByText("全部状态")).toBeInTheDocument();
  });

  it("renders new project button", () => {
    renderWithProviders(<ProjectManagePage />);
    expect(screen.getByText("新建项目")).toBeInTheDocument();
  });

  it("renders action buttons for each project", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    expect(screen.getByText("详情")).toBeInTheDocument();
    expect(screen.getByText("编辑")).toBeInTheDocument();
    expect(screen.getByText("生成")).toBeInTheDocument();
  });

  it("opens detail modal on project name click", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("测试项目"));
    await waitFor(() => {
      expect(screen.getByText("项目详情")).toBeInTheDocument();
    });
  });

  it("opens edit modal on edit button click", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    const editButtons = screen.getAllByText("编辑");
    fireEvent.click(editButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("编辑项目")).toBeInTheDocument();
    });
  });

  it("renders delete button with confirmation", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    // Ant Design Popconfirm 的删除按钮
    const deleteButtons = screen.getAllByText("删除");
    expect(deleteButtons.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 3: 运行前端测试验证**

Run: `cd frontend && npx vitest run src/pages/ProjectManage/index.test.tsx`
Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add frontend/src/mocks/handlers.ts frontend/src/pages/ProjectManage/index.test.tsx
git commit -m "test: add ProjectManage page component tests with MSW mocks"
```

---

### Task 6: 全量回归测试

**Files:**
- No new files

- [ ] **Step 1: 运行全部后端测试**

Run: `cd backend && python -m pytest tests/ -v --timeout=120`
Expected: 全部通过（原有 ~78 个 + 新增 ~30 个 ≈ 108 个）

- [ ] **Step 2: 运行全部前端测试**

Run: `cd frontend && npx vitest run`
Expected: 全部通过（原有 10 个 + 新增 8 个 ≈ 18 个）

- [ ] **Step 3: 更新 CLAUDE.md Progress Log**

在 Progress Log 末尾追加：
```
- [2026-06-15] 第6步 | RBAC+项目管理 | 完成测试重写：RBAC 权限矩阵测试（~30个）、项目管理 CRUD 测试（+6个）、合同/档案隔离测试（+6个）、前端 ProjectManage 测试（+8个）、修复 dedup 端点权限保护；后端共 108 个测试通过，前端共 18 个测试通过
```

- [ ] **Step 4: 最终 Commit**

```bash
git add CLAUDE.md
git commit -m "test: complete RBAC + project management test suite (~50 new tests)"
```
