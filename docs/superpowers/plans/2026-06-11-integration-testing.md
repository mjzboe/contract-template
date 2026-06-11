# 集成与测试 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为合同模板管理系统编写完整的分层自动化测试（后端单元测试 + API 集成测试 + 前端组件测试），修复发现的 Bug，编写 README。

**Architecture:** 分层递进：后端单元测试（variable_parser, doc_generator）→ 后端 API 集成测试（templates, projects, contracts, e2e）→ 前端组件测试（Home, TemplateManage, ContractGenerate）→ Bug 修复 → README。

**Tech Stack:** pytest + pytest-asyncio + httpx（后端）；Vitest + React Testing Library + MSW（前端）

---

## File Structure

```
backend/tests/
├── conftest.py              # 全局 fixtures（client, db_session, sample_template）
├── test_variable_parser.py  # 变量解析单元测试
├── test_doc_generator.py    # 文档生成单元测试
├── test_templates_api.py    # 模板 API 集成测试
├── test_projects_api.py     # 项目 API 集成测试
├── test_contracts_api.py    # 合同 API 集成测试
└── test_e2e_flow.py         # 端到端流程测试

frontend/src/
├── test-setup.ts            # Vitest 全局 setup（jsdom, cleanup）
├── mocks/
│   ├── handlers.ts          # MSW request handlers
│   └── server.ts            # MSW server setup
├── pages/Home/index.test.tsx
├── pages/TemplateManage/index.test.tsx
└── pages/ContractGenerate/index.test.tsx
```

---

### Task 1: 后端测试基础设施 — conftest.py

**Files:**
- Modify: `backend/tests/conftest.py`
- Modify: `backend/requirements.txt` (add pytest-asyncio)

- [ ] **Step 1: 添加 pytest-asyncio 依赖**

在 `backend/requirements.txt` 末尾添加：

```
# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
```

- [ ] **Step 2: 安装依赖**

Run: `cd backend && pip install pytest pytest-asyncio`
Expected: Successfully installed

- [ ] **Step 3: 重写 conftest.py**

```python
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database import get_db
from app.models.base import Base

# 使用与开发环境相同的 PostgreSQL
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/contract",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    """创建一个事务中的 session，测试后回滚

    使用 begin_nested (savepoint) 确保测试中的操作可以被回滚，
    不污染开发数据库。
    """
    async with TestSessionFactory() as session:
        async with session.begin():
            nested = await session.begin_nested()
            yield session
            await nested.rollback()
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """注入测试用 db_session 的 HTTP 客户端"""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_template(client: AsyncClient):
    """上传一个样例模板，返回 (template_id, variables)"""
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        response = await client.post(
            "/api/v1/templates",
            data={"name": "测试模板_股东会决议", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
        )
    assert response.status_code == 200
    data = response.json()
    return data["template"]["id"], data["variables"]


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: 运行 health check 测试验证基础设施**

Run: `cd backend && python -m pytest tests/conftest.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/tests/conftest.py backend/requirements.txt
git commit -m "feat: add test infrastructure with conftest fixtures"
```

---

### Task 2: 变量解析器单元测试

**Files:**
- Create: `backend/tests/test_variable_parser.py`

- [ ] **Step 1: 编写测试文件**

```python
import os

import pytest

from app.utils.variable_parser import (
    VariableInfo,
    deduplicate_variables,
    extract_variables_from_docx,
    extract_variables_from_text,
)


class TestExtractVariablesFromText:
    def test_simple_variable(self):
        result = extract_variables_from_text("甲方：【公司名称】")
        assert len(result) == 1
        assert result[0].name == "公司名称"

    def test_multiple_variables(self):
        result = extract_variables_from_text("【公司名称】【法定代表人】【日期】")
        assert len(result) == 3
        names = [v.name for v in result]
        assert "公司名称" in names
        assert "法定代表人" in names
        assert "日期" in names

    def test_no_variable(self):
        result = extract_variables_from_text("普通文本无变量")
        assert result == []

    def test_dedup_in_text(self):
        result = extract_variables_from_text("【公司名称】【公司名称】")
        assert len(result) == 1
        assert result[0].name == "公司名称"
        assert result[0].occurrences == 2

    def test_mixed_format_only_chinese_bracket(self):
        result = extract_variables_from_text("【变量A】和{{变量B}}")
        # 只提取中文括号变量
        names = [v.name for v in result]
        assert "变量A" in names

    def test_curly_brace_variable(self):
        result = extract_variables_from_text("{{变量C}}")
        names = [v.name for v in result]
        assert "变量C" in names

    def test_curly_brace_with_default(self):
        result = extract_variables_from_text("{{变量D|默认值}}")
        found = [v for v in result if v.name == "变量D"]
        assert len(found) == 1
        assert found[0].default_value == "默认值"

    def test_empty_string(self):
        result = extract_variables_from_text("")
        assert result == []


class TestExtractVariablesFromDocx:
    def test_sample_template(self):
        sample_path = os.path.join(
            os.path.dirname(__file__), "..", "samples", "签字页模板_股东会决议.docx"
        )
        if not os.path.exists(sample_path):
            pytest.skip("样例模板文件不存在")
        result = extract_variables_from_docx(sample_path)
        assert len(result) > 0
        # 所有结果应该是 VariableInfo 实例
        for v in result:
            assert isinstance(v, VariableInfo)
            assert v.name

    def test_all_sample_templates(self):
        samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
        docx_files = [
            f for f in os.listdir(samples_dir)
            if f.startswith("签字页模板_") and f.endswith(".docx")
        ]
        assert len(docx_files) >= 3, "至少应有 3 个样例模板"
        for filename in docx_files:
            path = os.path.join(samples_dir, filename)
            result = extract_variables_from_docx(path)
            assert len(result) > 0, f"{filename} 应包含变量"


class TestDeduplicateVariables:
    def test_cross_template_dedup(self):
        list1 = [VariableInfo(name="公司名称", occurrences=1)]
        list2 = [VariableInfo(name="公司名称", occurrences=1), VariableInfo(name="日期", occurrences=1)]
        result = deduplicate_variables([list1, list2])
        names = [v.name for v in result]
        assert "公司名称" in names
        assert "日期" in names
        # 公司名称 应只出现一次
        company_vars = [v for v in result if v.name == "公司名称"]
        assert len(company_vars) == 1
        assert company_vars[0].occurrences == 2

    def test_empty_lists(self):
        result = deduplicate_variables([])
        assert result == []

    def test_single_list(self):
        variables = [VariableInfo(name="A"), VariableInfo(name="B")]
        result = deduplicate_variables([variables])
        assert len(result) == 2
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_variable_parser.py -v`
Expected: ALL PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_variable_parser.py
git commit -m "test: add variable parser unit tests"
```

---

### Task 3: 文档生成器单元测试

**Files:**
- Create: `backend/tests/test_doc_generator.py`

- [ ] **Step 1: 编写测试文件**

```python
import os
import tempfile

import pytest
from docx import Document

from app.utils.doc_generator import batch_generate_docx, generate_docx, preview_docx


def _create_test_docx(variables_text: str, tmp_dir: str) -> str:
    """创建包含指定变量文本的测试 DOCX 文件"""
    doc = Document()
    doc.add_paragraph(variables_text)
    path = os.path.join(tmp_dir, "test_template.docx")
    doc.save(path)
    return path


class TestGenerateDocx:
    def test_simple_replace(self, tmp_path):
        template_path = _create_test_docx("甲方：【公司名称】", str(tmp_path))
        output_path = os.path.join(str(tmp_path), "output.docx")
        result_path = generate_docx(template_path, {"公司名称": "测试公司"}, output_path)
        assert os.path.exists(result_path)
        doc = Document(result_path)
        assert "测试公司" in doc.paragraphs[0].text
        assert "【公司名称】" not in doc.paragraphs[0].text

    def test_multiple_replace(self, tmp_path):
        template_path = _create_test_docx("【公司名称】【法定代表人】【日期】", str(tmp_path))
        output_path = os.path.join(str(tmp_path), "output.docx")
        generate_docx(
            template_path,
            {"公司名称": "XX科技", "法定代表人": "张三", "日期": "2024-01-01"},
            output_path,
        )
        doc = Document(output_path)
        text = doc.paragraphs[0].text
        assert "XX科技" in text
        assert "张三" in text
        assert "2024-01-01" in text

    def test_unfilled_variable_preserved(self, tmp_path):
        template_path = _create_test_docx("【公司名称】【未填变量】", str(tmp_path))
        output_path = os.path.join(str(tmp_path), "output.docx")
        generate_docx(template_path, {"公司名称": "XX科技"}, output_path)
        doc = Document(output_path)
        text = doc.paragraphs[0].text
        assert "XX科技" in text
        assert "【未填变量】" in text

    def test_output_file_valid_docx(self, tmp_path):
        template_path = _create_test_docx("【变量】", str(tmp_path))
        result_path = generate_docx(template_path, {"变量": "值"})
        assert os.path.exists(result_path)
        assert result_path.endswith(".docx")
        # 验证文件可以被正常打开
        doc = Document(result_path)
        assert len(doc.paragraphs) > 0


class TestBatchGenerateDocx:
    def test_batch(self, tmp_path):
        template_path = _create_test_docx("【名称】", str(tmp_path))
        output_dir = os.path.join(str(tmp_path), "batch_output")
        variables_list = [
            {"名称": "第一份"},
            {"名称": "第二份"},
            {"名称": "第三份"},
        ]
        paths = batch_generate_docx(template_path, variables_list, output_dir)
        assert len(paths) == 3
        for p in paths:
            assert os.path.exists(p)


class TestPreviewDocx:
    def test_preview_with_replacement(self, tmp_path):
        template_path = _create_test_docx("甲方：【公司名称】同意", str(tmp_path))
        result = preview_docx(template_path, {"公司名称": "XX科技"})
        assert "XX科技" in result
        assert "【公司名称】" not in result

    def test_preview_without_replacement(self, tmp_path):
        template_path = _create_test_docx("甲方：【公司名称】同意", str(tmp_path))
        result = preview_docx(template_path, {})
        assert "【公司名称】" in result
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_doc_generator.py -v`
Expected: ALL PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_doc_generator.py
git commit -m "test: add doc generator unit tests"
```

---

### Task 4: 模板 API 集成测试

**Files:**
- Create: `backend/tests/test_templates_api.py`

注意：分类 API 路由不存在（只有模型），需要添加或跳过分类测试。此处先添加分类 API 路由再测试。

- [ ] **Step 1: 在 router.py 中添加分类 API 路由**

在 `backend/app/api/router.py` 中添加分类 CRUD 路由：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import router as contracts_router
from app.api.projects import router as projects_router
from app.api.templates import router as templates_router
from app.database import get_db
from app.models.category import Category
from app.schemas.template import CategoryCreate, CategoryResponse

router = APIRouter()

router.include_router(templates_router)
router.include_router(projects_router)
router.include_router(contracts_router)


# ========== 分类 API ==========
@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    category = Category(
        name=data.name,
        parent_id=data.parent_id,
        sort_order=data.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return list(result.scalars().all())


@router.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 2: 编写模板 API 测试文件**

```python
import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    response = await client.post("/api/v1/categories", json={"name": "IPO签字页"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "IPO签字页"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient):
    # 先创建
    await client.post("/api/v1/categories", json={"name": "分类A"})
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_upload_template(client: AsyncClient):
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        response = await client.post(
            "/api/v1/templates",
            data={"name": "上传测试模板", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
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
async def test_delete_template(client: AsyncClient, sample_template):
    template_id, _ = sample_template
    response = await client.delete(f"/api/v1/templates/{template_id}")
    assert response.status_code == 200
    # 验证已删除
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
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_templates_api.py -v`
Expected: ALL PASSED（如有 Bug 边修边改）

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/router.py backend/tests/test_templates_api.py
git commit -m "test: add category API and template API integration tests"
```

---

### Task 5: 项目 API 集成测试

**Files:**
- Create: `backend/tests/test_projects_api.py`

- [ ] **Step 1: 编写测试文件**

```python
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
    """多模板去重：上传两个模板，共享变量应被去重"""
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
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
    # 两个模板共享的变量应有 variable_sources 指向两个模板
    shared_vars = {
        name: sources for name, sources in data["variable_sources"].items()
        if len(sources) > 1
    }
    # IPO 签字页模板之间应有共享变量
    assert data["total_variables_after_dedup"] < data["total_variables_before_dedup"] or len(shared_vars) > 0
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_projects_api.py -v`
Expected: ALL PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_projects_api.py
git commit -m "test: add project API integration tests"
```

---

### Task 6: 合同 API 集成测试

**Files:**
- Create: `backend/tests/test_contracts_api.py`

- [ ] **Step 1: 编写测试文件**

```python
import os
import time

import pytest
from httpx import AsyncClient


async def _setup_project_with_template(client: AsyncClient) -> tuple[str, str, dict[str, str]]:
    """辅助：上传模板 → 创建项目 → 返回 (project_id, template_id, sample_variables)"""
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "samples", "签字页模板_股东会决议.docx"
    )
    with open(sample_path, "rb") as f:
        tmpl_resp = await client.post(
            "/api/v1/templates",
            data={"name": "合同测试模板", "tags": "[]"},
            files={"file": ("签字页模板_股东会决议.docx", f, "application/octet-stream")},
        )
    template_id = tmpl_resp.json()["template"]["id"]
    variables = tmpl_resp.json()["variables"]

    # 填充变量值
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
    return data["id"]


@pytest.mark.asyncio
async def test_export_word(client: AsyncClient):
    project_id, template_id, var_values = await _setup_project_with_template(client)
    # 先生成
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
    # 导出
    response = await client.get(
        f"/api/v1/contracts/{contract_id}/export?format=word"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.asyncio
async def test_parse_excel(client: AsyncClient):
    excel_path = os.path.join(
        os.path.dirname(__file__), "..", "samples", "批量导入样例.xlsx"
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
    return data["task_id"]


@pytest.mark.asyncio
async def test_get_task_status(client: AsyncClient):
    # 先创建异步任务
    project_id, template_id, _ = await _setup_project_with_template(client)
    rows = [{"公司名称": "状态测试公司", "日期": "2024-01-01"}]
    task_resp = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={"project_id": project_id, "rows": rows, "selected_indices": [0]},
    )
    task_id = task_resp.json()["task_id"]
    # 等待一小段时间
    time.sleep(2)
    response = await client.get(f"/api/v1/contracts/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("pending", "running", "completed", "failed")


@pytest.mark.asyncio
async def test_download_zip(client: AsyncClient):
    # 创建异步任务并等待完成
    project_id, template_id, _ = await _setup_project_with_template(client)
    rows = [{"公司名称": "ZIP测试公司", "日期": "2024-01-01"}]
    task_resp = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={"project_id": project_id, "rows": rows, "selected_indices": [0]},
    )
    task_id = task_resp.json()["task_id"]
    # 等待完成
    for _ in range(10):
        time.sleep(1)
        status_resp = await client.get(f"/api/v1/contracts/tasks/{task_id}")
        if status_resp.json()["status"] == "completed":
            break
    # 下载 ZIP
    response = await client.get(f"/api/v1/contracts/tasks/{task_id}/download-zip")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_contracts_api.py -v`
Expected: ALL PASSED（如有 Bug 边修边改）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_contracts_api.py
git commit -m "test: add contract API integration tests"
```

---

### Task 7: 端到端流程测试

**Files:**
- Create: `backend/tests/test_e2e_flow.py`

- [ ] **Step 1: 编写端到端测试文件**

```python
"""端到端流程测试：完整业务链路"""

import os
import time

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_e2e_flow(client: AsyncClient):
    """完整业务流程：创建分类 → 上传模板 → 创建项目 → 去重变量 → 生成合同 → 导出 → 批量生成 → ZIP 下载"""

    # 1. 创建分类
    cat_resp = await client.post("/api/v1/categories", json={"name": "IPO签字页"})
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    # 2. 上传3个模板
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
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
            )
        assert resp.status_code == 200
        template_ids.append(resp.json()["template"]["id"])
        # 确认变量提取
        assert len(resp.json()["variables"]) > 0

    # 3. 创建项目，关联3个模板
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "E2E测试-IPO签字页", "template_ids": template_ids},
    )
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["id"]

    # 4. 获取去重变量
    dedup_resp = await client.get(f"/api/v1/projects/{project_id}/deduplicated-variables")
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
    )
    assert contract_resp.status_code == 200
    contract_id = contract_resp.json()["id"]

    # 6. 导出 Word
    export_resp = await client.get(f"/api/v1/contracts/{contract_id}/export?format=word")
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

    # 8. 批量异步生成
    batch_resp = await client.post(
        "/api/v1/contracts/batch-from-rows-async",
        json={
            "project_id": project_id,
            "rows": excel_data["rows"],
            "selected_indices": list(range(min(2, excel_data["total_rows"]))),
        },
    )
    assert batch_resp.status_code == 200
    task_id = batch_resp.json()["task_id"]

    # 9. 等待完成 + 下载 ZIP
    for _ in range(15):
        time.sleep(1)
        status_resp = await client.get(f"/api/v1/contracts/tasks/{task_id}")
        if status_resp.json()["status"] == "completed":
            break

    zip_resp = await client.get(f"/api/v1/contracts/tasks/{task_id}/download-zip")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_e2e_flow.py -v`
Expected: PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_e2e_flow.py
git commit -m "test: add end-to-end flow integration test"
```

---

### Task 8: 运行所有后端测试 + Bug 修复

**Files:**
- May modify any backend file to fix bugs found

- [ ] **Step 1: 运行全部后端测试**

Run: `cd backend && python -m pytest tests/ -v --tb=short`
Expected: ALL PASSED

- [ ] **Step 2: 如果有失败测试，逐一修复**

检查常见问题：
- 数据库 session 回滚是否正常
- 文件路径在 Windows 上的兼容性
- API 返回的 status code 是否与测试预期匹配
- `dependency_overrides` 是否正确清理

- [ ] **Step 3: 全部通过后 Commit**

```bash
git add -A
git commit -m "fix: resolve bugs found during backend integration testing"
```

---

### Task 9: 前端测试基础设施 — Vitest + RTL + MSW

**Files:**
- Modify: `frontend/package.json` (add devDeps)
- Create: `frontend/src/test-setup.ts`
- Create: `frontend/src/mocks/handlers.ts`
- Create: `frontend/src/mocks/server.ts`
- Modify: `frontend/vite.config.ts` (add test config)

- [ ] **Step 1: 安装前端测试依赖**

Run: `cd frontend && npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom msw`

- [ ] **Step 2: 更新 vite.config.ts 添加测试配置**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
```

- [ ] **Step 3: 创建 test-setup.ts**

```typescript
import "@testing-library/jest-dom";
import { server } from "./mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

- [ ] **Step 4: 创建 MSW handlers**

```typescript
// frontend/src/mocks/handlers.ts
import { http, HttpResponse } from "msw";

const mockTemplate = {
  id: "mock-template-id-1",
  name: "测试模板",
  category_id: null,
  tags: [],
  description: null,
  status: "draft",
  created_by: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  versions: [
    {
      id: "mock-version-id-1",
      version_number: "v1",
      file_path: "/uploads/test.docx",
      variables: [
        { name: "公司名称", display_name: "公司名称", var_type: "text", default_value: "", validation_rule: "", occurrences: 2 },
        { name: "法定代表人", display_name: "法定代表人", var_type: "text", default_value: "", validation_rule: "", occurrences: 1 },
        { name: "日期", display_name: "日期", var_type: "date", default_value: "", validation_rule: "", occurrences: 1 },
      ],
      is_master: true,
      change_log: "初始版本",
      created_at: "2024-01-01T00:00:00",
    },
  ],
};

const mockProject = {
  id: "mock-project-id-1",
  name: "测试项目",
  description: null,
  status: "draft",
  deduplicated_variables: [
    { name: "公司名称", display_name: "公司名称", var_type: "text", default_value: "", validation_rule: "", occurrences: 2 },
    { name: "法定代表人", display_name: "法定代表人", var_type: "text", default_value: "", validation_rule: "", occurrences: 1 },
    { name: "日期", display_name: "日期", var_type: "date", default_value: "", validation_rule: "", occurrences: 1 },
  ],
  created_by: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  templates: [mockTemplate],
};

const mockContract = {
  id: "mock-contract-id-1",
  title: "测试合同",
  project_id: "mock-project-id-1",
  template_id: "mock-template-id-1",
  template_version_id: null,
  variables: { 公司名称: "XX科技", 法定代表人: "张三", 日期: "2024-01-01" },
  file_path: "/uploads/contracts/test.docx",
  file_path_pdf: null,
  status: "generated",
  created_by: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
};

export const handlers = [
  // Health
  http.get("/api/v1/health", () => HttpResponse.json({ status: "ok" })),

  // Templates
  http.get("/api/v1/templates", () =>
    HttpResponse.json({ items: [mockTemplate], total: 1, page: 1, page_size: 20 })
  ),
  http.post("/api/v1/templates", async () =>
    HttpResponse.json(
      { template: mockTemplate, variables: mockTemplate.versions[0].variables },
      { status: 200 }
    )
  ),
  http.get("/api/v1/templates/:id", () => HttpResponse.json(mockTemplate)),
  http.delete("/api/v1/templates/:id", () => HttpResponse.json({ message: "删除成功" })),
  http.get("/api/v1/templates/:id/variables", () =>
    HttpResponse.json(mockTemplate.versions[0].variables)
  ),

  // Projects
  http.get("/api/v1/projects", () =>
    HttpResponse.json({ items: [mockProject], total: 1, page: 1, page_size: 20 })
  ),
  http.post("/api/v1/projects", async () => HttpResponse.json(mockProject)),
  http.get("/api/v1/projects/:id", () => HttpResponse.json(mockProject)),
  http.get("/api/v1/projects/:id/deduplicated-variables", () =>
    HttpResponse.json({
      project_id: "mock-project-id-1",
      template_count: 1,
      total_variables_before_dedup: 3,
      total_variables_after_dedup: 3,
      variables: mockProject.deduplicated_variables,
      variable_sources: { 公司名称: ["测试模板"], 法定代表人: ["测试模板"], 日期: ["测试模板"] },
    })
  ),

  // Contracts
  http.get("/api/v1/contracts", () =>
    HttpResponse.json({ items: [mockContract], total: 1, page: 1, page_size: 20 })
  ),
  http.post("/api/v1/contracts", async () => HttpResponse.json(mockContract)),
  http.post("/api/v1/contracts/preview", async () =>
    HttpResponse.json({ preview_text: "甲方：XX科技 法定代表人：张三 日期：2024-01-01" })
  ),
  http.post("/api/v1/contracts/parse-excel", async () =>
    HttpResponse.json({
      headers: ["公司名称", "法定代表人", "日期"],
      rows: [
        { 公司名称: "公司A", 法定代表人: "张三", 日期: "2024-01-01" },
        { 公司名称: "公司B", 法定代表人: "李四", 日期: "2024-01-02" },
      ],
      total_rows: 2,
    })
  ),
  http.post("/api/v1/contracts/batch-from-rows-async", async () =>
    HttpResponse.json({
      task_id: "mock-task-id",
      task_type: "batch_generate",
      status: "completed",
      progress: 2,
      total: 2,
      result: { contract_ids: ["mock-contract-id-1"], zip_path: "/uploads/zip/test.zip", count: 2 },
      error: null,
    })
  ),
  http.get("/api/v1/contracts/tasks/:id", () =>
    HttpResponse.json({
      task_id: "mock-task-id",
      task_type: "batch_generate",
      status: "completed",
      progress: 2,
      total: 2,
      result: { contract_ids: ["mock-contract-id-1"], zip_path: "/uploads/zip/test.zip", count: 2 },
      error: null,
    })
  ),
];
```

- [ ] **Step 5: 创建 MSW server**

```typescript
// frontend/src/mocks/server.ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
```

- [ ] **Step 6: 在 package.json 添加 test 脚本**

在 `frontend/package.json` 的 `scripts` 中添加：

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 7: 验证基础设施工作**

Run: `cd frontend && npx vitest run --reporter=verbose 2>&1 | head -5`
Expected: 没有配置错误（可能还没有测试文件，不应有配置错误）

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/test-setup.ts frontend/src/mocks/
git commit -m "feat: add frontend test infrastructure (Vitest + RTL + MSW)"
```

---

### Task 10: 首页组件测试

**Files:**
- Create: `frontend/src/pages/Home/index.test.tsx`

- [ ] **Step 1: 编写测试文件**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import HomePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("HomePage", () => {
  it("renders statistic cards", async () => {
    renderWithProviders(<HomePage />);
    await waitFor(() => {
      expect(screen.getByText("模板总数")).toBeInTheDocument();
      expect(screen.getByText("项目总数")).toBeInTheDocument();
      expect(screen.getByText("已生成签字页")).toBeInTheDocument();
    });
  });

  it("renders recent projects", async () => {
    renderWithProviders(<HomePage />);
    await waitFor(() => {
      expect(screen.getByText("最近项目")).toBeInTheDocument();
    });
  });

  it("renders action buttons", () => {
    renderWithProviders(<HomePage />);
    expect(screen.getByText("创建项目")).toBeInTheDocument();
    expect(screen.getByText("管理模板")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试**

Run: `cd frontend && npx vitest run src/pages/Home/index.test.tsx`
Expected: ALL PASSED

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Home/index.test.tsx
git commit -m "test: add Home page component tests"
```

---

### Task 11: 模板管理页组件测试

**Files:**
- Create: `frontend/src/pages/TemplateManage/index.test.tsx`

- [ ] **Step 1: 编写测试文件**

```tsx
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import TemplateManagePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("TemplateManagePage", () => {
  it("renders template list with data from API", async () => {
    renderWithProviders(<TemplateManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试模板")).toBeInTheDocument();
    });
  });

  it("renders upload button", () => {
    renderWithProviders(<TemplateManagePage />);
    expect(screen.getByText("上传模板")).toBeInTheDocument();
  });

  it("renders search input", () => {
    renderWithProviders(<TemplateManagePage />);
    expect(screen.getByPlaceholderText("搜索模板")).toBeInTheDocument();
  });

  it("shows variable count for templates", async () => {
    renderWithProviders(<TemplateManagePage />);
    await waitFor(() => {
      // Mock 数据中有 3 个变量
      expect(screen.getByText(/3\s*个/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: 运行测试**

Run: `cd frontend && npx vitest run src/pages/TemplateManage/index.test.tsx`
Expected: ALL PASSED

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TemplateManage/index.test.tsx
git commit -m "test: add TemplateManage page component tests"
```

---

### Task 12: 合同生成页组件测试

**Files:**
- Create: `frontend/src/pages/ContractGenerate/index.test.tsx`

- [ ] **Step 1: 编写测试文件**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import ContractGeneratePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("ContractGeneratePage", () => {
  it("renders steps component", () => {
    renderWithProviders(<ContractGeneratePage />);
    expect(screen.getByText("创建项目")).toBeInTheDocument();
    expect(screen.getByText("填写变量")).toBeInTheDocument();
    expect(screen.getByText("生成下载")).toBeInTheDocument();
  });

  it("renders project name input in step 1", () => {
    renderWithProviders(<ContractGeneratePage />);
    expect(screen.getByPlaceholderText("输入项目名称，如：XX公司IPO签字页")).toBeInTheDocument();
  });

  it("renders template table in step 1", async () => {
    renderWithProviders(<ContractGeneratePage />);
    await waitFor(() => {
      expect(screen.getByText("测试模板")).toBeInTheDocument();
    });
  });

  it("renders next step button", () => {
    renderWithProviders(<ContractGeneratePage />);
    expect(screen.getByText(/下一步/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试**

Run: `cd frontend && npx vitest run src/pages/ContractGenerate/index.test.tsx`
Expected: ALL PASSED

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ContractGenerate/index.test.tsx
git commit -m "test: add ContractGenerate page component tests"
```

---

### Task 13: 运行所有前端测试 + Bug 修复

**Files:**
- May modify any frontend file to fix bugs found

- [ ] **Step 1: 运行全部前端测试**

Run: `cd frontend && npx vitest run`
Expected: ALL PASSED

- [ ] **Step 2: 如果有失败测试，逐一修复**

检查常见问题：
- MSW handler 路径是否匹配
- Ant Design 组件渲染的文本是否匹配
- 异步等待时间是否足够
- BrowserRouter 与测试环境兼容性

- [ ] **Step 3: 全部通过后 Commit**

```bash
git add -A
git commit -m "fix: resolve bugs found during frontend component testing"
```

---

### Task 14: 编写 README

**Files:**
- Create: `README.md` (was deleted, need to recreate)

- [ ] **Step 1: 编写 README.md**

```markdown
# 合同模板管理系统（签字页管理）

律师事务所 IPO 签字页管理系统。核心流程：**创建项目 → 选择模板 → 变量去重 → 填充变量 → 生成签字页 → 下载**。

## 核心功能

- **模板管理**：上传 Word 模板，自动解析 `【变量名】` 格式占位符
- **变量去重**：跨模板同名变量自动合并，一次填写全局生效
- **合同生成**：支持单个生成和 Excel 批量生成
- **异步导出**：批量生成后台运行，支持 ZIP 打包下载

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + Vite |
| 后端 | Python 3.11+ / FastAPI + SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 15 |
| 文档处理 | python-docx + docxtpl |
| 测试 | pytest (后端) + Vitest + React Testing Library (前端) |

## 本地运行

### 1. 启动基础设施

```bash
docker-compose -f docker-compose.dev.yml up -d
```

这会启动 PostgreSQL (5432) 和 Redis (6379)。

### 2. 后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

### 4. 样例数据

`samples/` 目录包含：
- 3 个签字页模板（股东会决议、董事会决议、律师见证函）
- 1 个 Excel 批量导入样例

可在"模板管理"页面上传模板，在"合同生成"页面体验完整流程。

## 运行测试

### 后端测试

```bash
cd backend
python -m pytest tests/ -v
```

需要 PostgreSQL 运行中（使用开发数据库，测试后回滚）。

### 前端测试

```bash
cd frontend
npm test
```

前端测试使用 MSW 模拟 API，不需要后端运行。

## 已知限制

- PDF 导出暂未实现（MVP 阶段返回 Word 格式）
- 审批流和归档模块为占位页面，未实现
- 用户认证为简化 mock（固定 dev-user）
- 异步任务使用内存存储，重启后丢失
- 文件存储为本地文件系统，未接入 MinIO
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

### Task 15: 更新 CLAUDE.md Progress Log

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 在 Progress Log 末尾添加第6步完成记录**

在 CLAUDE.md 的 `## Progress Log` 部分末尾添加：

```
- [2026-06-11] 第6步 | 全局 | 完成后端单元测试（variable_parser, doc_generator）+ API 集成测试（templates, projects, contracts, e2e flow）+ 添加分类 API 路由 + Bug 修复
- [2026-06-11] 第6步 | 全局 | 完成前端组件测试（Home, TemplateManage, ContractGenerate）+ MSW Mock 基础设施
- [2026-06-11] 第6步 | 全局 | 完成 README.md 编写
- [2026-06-11] 第6步 | 全局 | **第6步完成** — 集成与测试全部完成，可进入第7步报告撰写
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update progress log for step 6 completion"
```
