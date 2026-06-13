# 档案归档与检索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的档案归档与检索功能——合同生成后自动归档，支持关键词/时间/模板/项目过滤检索，详情页含操作时间线和文件下载。

**Architecture:** 扩展现有 Contract 模型，添加 `archived_at` 和 `status_history` 字段。新增 `archive_service.py` 和 `archives.py` API 路由。前端重写 `ArchiveSearchPage`，复用现有 API 层模式。

**Tech Stack:** SQLAlchemy 2.0 (async) + FastAPI + Alembic (后端), React 18 + Ant Design 5 + TypeScript (前端)

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `backend/app/models/contract.py` | 添加 `archived_at`、`status_history` 字段 |
| Create | `backend/app/services/archive_service.py` | 归档列表查询、详情、下载业务逻辑 |
| Create | `backend/app/api/archives.py` | 归档 API 路由（列表/详情/下载） |
| Modify | `backend/app/api/router.py` | 注册 archives_router |
| Modify | `backend/app/schemas/contract.py` | 添加归档相关 schema |
| Modify | `backend/app/services/contract_service.py` | 生成合同时自动归档 + 追加 status_history |
| Create | `backend/alembic/versions/xxxx_add_archive_fields.py` | 数据库迁移 |
| Create | `backend/tests/test_archives_api.py` | 归档 API 测试 |
| Create | `frontend/src/api/archives.ts` | 前端归档 API 调用 |
| Modify | `frontend/src/types/index.ts` | 添加归档相关类型 |
| Rewrite | `frontend/src/pages/ArchiveSearch/index.tsx` | 档案检索页面 |
| Modify | `CLAUDE.md` | 更新 Progress Log |

---

### Task 1: 数据模型变更 — 添加归档字段

**Files:**
- Modify: `backend/app/models/contract.py`
- Create: `backend/alembic/versions/xxxx_add_archive_fields.py` (通过 alembic 命令生成)

- [ ] **Step 1: 修改 Contract 模型，添加 archived_at 和 status_history 字段**

在 `backend/app/models/contract.py` 的 Contract 类中，在 `created_by` 字段之后添加：

```python
from datetime import datetime
from sqlalchemy import DateTime

# 在 Contract 类内，created_by 之后添加：
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status_history: Mapped[list] = mapped_column(JSONB, default=list)
```

同时确保文件顶部已有 `from datetime import datetime` 导入（Base 那个已经有了，但 Contract 自己可能没有），以及确认 `JSONB` 已导入。

- [ ] **Step 2: 生成 Alembic 迁移**

Run: `cd backend && alembic revision --autogenerate -m "add archive fields to contracts"`

- [ ] **Step 3: 执行迁移**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 4: 验证迁移成功**

Run: `cd backend && python -c "from app.models.contract import Contract; print('archived_at:', Contract.archived_at); print('status_history:', Contract.status_history)"`

Expected: 无报错，打印字段信息

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/contract.py backend/alembic/versions/
git commit -m "feat: add archived_at and status_history fields to Contract model"
```

---

### Task 2: Schema 扩展 — 归档响应类型

**Files:**
- Modify: `backend/app/schemas/contract.py`

- [ ] **Step 1: 在 contract.py schema 文件中添加归档相关 schema**

在 `backend/app/schemas/contract.py` 文件末尾添加：

```python
class ArchiveListItem(BaseModel):
    """归档列表项（含关联名称）"""
    id: uuid.UUID
    title: str
    status: str = "archived"
    archived_at: datetime | None = None
    template_id: uuid.UUID
    template_name: str | None = None
    project_id: uuid.UUID | None = None
    project_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArchiveListResponse(BaseModel):
    items: list[ArchiveListItem]
    total: int
    page: int
    page_size: int


class StatusHistoryEntry(BaseModel):
    """状态变更记录"""
    status: str
    at: str


class ArchiveDetail(BaseModel):
    """归档详情（含时间线和变量）"""
    id: uuid.UUID
    title: str
    status: str = "archived"
    archived_at: datetime | None = None
    template_id: uuid.UUID
    template_name: str | None = None
    project_id: uuid.UUID | None = None
    project_name: str | None = None
    variables: dict = {}
    status_history: list[StatusHistoryEntry] = []
    file_path: str | None = None
    file_path_pdf: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

同时在 `ContractResponse` 中添加新字段：

```python
# 在 ContractResponse 的 status 字段后添加：
    archived_at: datetime | None = None
    status_history: list = []
```

- [ ] **Step 2: 验证 schema 无语法错误**

Run: `cd backend && python -c "from app.schemas.contract import ArchiveListItem, ArchiveListResponse, ArchiveDetail; print('OK')"`

Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/contract.py
git commit -m "feat: add archive-related Pydantic schemas"
```

---

### Task 3: 后端服务层 — archive_service.py

**Files:**
- Create: `backend/app/services/archive_service.py`

- [ ] **Step 1: 编写 archive_service.py**

创建 `backend/app/services/archive_service.py`：

```python
"""档案归档服务层：检索、详情、下载"""

import os
import uuid
from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contract import Contract
from app.models.project import Project
from app.models.template import Template


async def list_archives(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    template_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[dict], int]:
    """归档列表（带关联名称）"""
    query = (
        select(Contract, Template.name.label("template_name"), Project.name.label("project_name"))
        .outerjoin(Template, Contract.template_id == Template.id)
        .outerjoin(Project, Contract.project_id == Project.id)
        .where(Contract.archived_at.isnot(None))
    )

    if keyword:
        query = query.where(Contract.title.ilike(f"%{keyword}%"))
    if template_id:
        query = query.where(Contract.template_id == template_id)
    if project_id:
        query = query.where(Contract.project_id == project_id)
    if date_from:
        query = query.where(Contract.archived_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(Contract.archived_at <= datetime.combine(date_to, datetime.max.time()))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Contract.archived_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    items = []
    for row in result:
        contract = row[0]
        template_name = row[1]
        project_name = row[2]
        items.append({
            "id": contract.id,
            "title": contract.title,
            "status": contract.status,
            "archived_at": contract.archived_at,
            "template_id": contract.template_id,
            "template_name": template_name,
            "project_id": contract.project_id,
            "project_name": project_name,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
        })

    return items, total


async def get_archive_detail(
    db: AsyncSession,
    contract_id: uuid.UUID,
) -> dict | None:
    """归档详情（含模板名、项目名、时间线）"""
    query = (
        select(Contract, Template.name.label("template_name"), Project.name.label("project_name"))
        .outerjoin(Template, Contract.template_id == Template.id)
        .outerjoin(Project, Contract.project_id == Project.id)
        .where(Contract.id == contract_id, Contract.archived_at.isnot(None))
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        return None

    contract = row[0]
    return {
        "id": contract.id,
        "title": contract.title,
        "status": contract.status,
        "archived_at": contract.archived_at,
        "template_id": contract.template_id,
        "template_name": row[1],
        "project_id": contract.project_id,
        "project_name": row[2],
        "variables": contract.variables,
        "status_history": contract.status_history or [],
        "file_path": contract.file_path,
        "file_path_pdf": contract.file_path_pdf,
        "created_by": contract.created_by,
        "created_at": contract.created_at,
        "updated_at": contract.updated_at,
    }


async def get_archive_file_path(
    db: AsyncSession,
    contract_id: uuid.UUID,
    format: str = "word",
) -> str | None:
    """获取归档文件路径"""
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.archived_at.isnot(None))
    )
    contract = result.scalar_one_or_none()
    if not contract:
        return None

    if format == "pdf":
        if contract.file_path_pdf and os.path.exists(contract.file_path_pdf):
            return contract.file_path_pdf
        return contract.file_path
    return contract.file_path
```

- [ ] **Step 2: 验证模块导入无错**

Run: `cd backend && python -c "from app.services.archive_service import list_archives, get_archive_detail, get_archive_file_path; print('OK')"`

Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/archive_service.py
git commit -m "feat: add archive service with list, detail, and file download"
```

---

### Task 4: 后端 API 路由 — archives.py

**Files:**
- Create: `backend/app/api/archives.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: 创建 archives.py API 路由**

创建 `backend/app/api/archives.py`：

```python
"""档案归档 API 路由"""

import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.schemas.contract import ArchiveDetail, ArchiveListResponse, ArchiveListItem
from app.services import archive_service

router = APIRouter(prefix="/archives", tags=["档案归档"])


@router.get("", response_model=ArchiveListResponse)
async def list_archives(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    template_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("super_admin", "template_admin", "approver", "user")),
):
    """归档列表（支持关键词、模板、项目、时间范围过滤）"""
    items, total = await archive_service.list_archives(
        db, page, page_size, keyword, template_id, project_id, date_from, date_to
    )
    return ArchiveListResponse(
        items=[ArchiveListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{contract_id}", response_model=ArchiveDetail)
async def get_archive_detail(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("super_admin", "template_admin", "approver", "user")),
):
    """归档详情（含操作时间线和变量）"""
    detail = await archive_service.get_archive_detail(db, contract_id)
    if not detail:
        raise HTTPException(status_code=404, detail="归档记录不存在")
    return ArchiveDetail(**detail)


@router.get("/{contract_id}/download")
async def download_archive(
    contract_id: uuid.UUID,
    format: str = Query("word", regex="^(word|docx|pdf)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("super_admin", "template_admin", "approver", "user")),
):
    """下载归档文件"""
    file_path = await archive_service.get_archive_file_path(db, contract_id, format)
    if not file_path:
        raise HTTPException(status_code=404, detail="归档记录或文件不存在")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    filename = os.path.basename(file_path)
    media_type = (
        "application/pdf" if format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )
```

- [ ] **Step 2: 在 router.py 注册 archives_router**

在 `backend/app/api/router.py` 中添加导入和注册：

在文件顶部导入区域添加：
```python
from app.api.archives import router as archives_router
```

在 `router.include_router(contracts_router)` 之后添加：
```python
router.include_router(archives_router)
```

- [ ] **Step 3: 验证路由注册成功**

Run: `cd backend && python -c "from app.api.router import router; routes = [r.path for r in router.routes]; print([r for r in routes if 'archive' in r])"`

Expected: 包含 `/archives`, `/archives/{contract_id}`, `/archives/{contract_id}/download`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/archives.py backend/app/api/router.py
git commit -m "feat: add archives API routes (list, detail, download)"
```

---

### Task 5: 自动归档 — 修改 contract_service.py

**Files:**
- Modify: `backend/app/services/contract_service.py`

- [ ] **Step 1: 修改 generate_contract 函数，生成后自动归档**

在 `backend/app/services/contract_service.py` 的 `generate_contract` 函数中，将 `status="generated"` 改为归档逻辑。找到创建 Contract 对象的位置（约第59-68行），修改为：

```python
    from datetime import datetime, timezone

    # 创建 Contract 记录（自动归档）
    now = datetime.now(timezone.utc).isoformat()
    contract = Contract(
        title=title,
        project_id=project_id,
        template_id=template_id,
        template_version_id=template_version.id,
        variables=variables,
        file_path=output_path,
        status="archived",
        archived_at=datetime.now(timezone.utc),
        status_history=[
            {"status": "draft", "at": now},
            {"status": "archived", "at": now},
        ],
        created_by=user_id,
    )
```

- [ ] **Step 2: 修改 batch_generate_from_rows 函数，批量生成后自动归档**

在同一个文件中，找到 `batch_generate_from_rows` 函数创建 Contract 的位置（约第232-241行），修改为：

```python
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat()
            contract = Contract(
                title=title,
                project_id=project_id,
                template_id=tmpl.id,
                template_version_id=template_version.id,
                variables=variables,
                file_path=output_path,
                status="archived",
                archived_at=datetime.now(timezone.utc),
                status_history=[
                    {"status": "draft", "at": now},
                    {"status": "archived", "at": now},
                ],
                created_by=user_id,
            )
```

- [ ] **Step 3: 修改 batch_generate_from_excel 函数，同样自动归档**

在同一个文件中，找到 `batch_generate_from_excel` 函数创建 Contract 的位置（约第331-340行），修改为：

```python
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat()
            contract = Contract(
                title=title,
                project_id=project_id,
                template_id=template_id,
                template_version_id=template_version.id,
                variables=variables,
                file_path=output_path,
                status="archived",
                archived_at=datetime.now(timezone.utc),
                status_history=[
                    {"status": "draft", "at": now},
                    {"status": "archived", "at": now},
                ],
                created_by=user_id,
            )
```

注意：`from datetime import datetime, timezone` 只需在文件顶部导入一次即可，不需要在每个函数内重复导入。将文件顶部的 `import` 区域添加：

```python
from datetime import datetime, timezone
```

然后删除各函数内的局部导入。

- [ ] **Step 4: 验证修改无语法错误**

Run: `cd backend && python -c "from app.services.contract_service import generate_contract; print('OK')"`

Expected: OK

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/contract_service.py
git commit -m "feat: auto-archive contracts on generation with status history"
```

---

### Task 6: 后端测试 — archives API

**Files:**
- Create: `backend/tests/test_archives_api.py`

- [ ] **Step 1: 编写归档 API 测试**

创建 `backend/tests/test_archives_api.py`：

```python
"""档案归档 API 测试"""

import os
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

    # 生成一份合同
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

    # 查询归档列表
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

    # 搜索 Alpha
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

    # 查询详情
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

    # 下载 Word
    resp = await client.get(
        f"/api/v1/archives/{contract_id}/download", params={"format": "word"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.asyncio
async def test_archives_require_auth(client: AsyncClient):
    """归档 API 需要认证"""
    resp = await client.get("/api/v1/archives")
    assert resp.status_code == 403
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest tests/test_archives_api.py -v`

Expected: 8 个测试全部通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_archives_api.py
git commit -m "test: add archive API tests (8 cases)"
```

---

### Task 7: 前端类型定义和 API 层

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/archives.ts`

- [ ] **Step 1: 在 types/index.ts 添加归档相关类型**

在 `frontend/src/types/index.ts` 文件的 `// ========== 合同 ==========` 区域之前添加：

```typescript
// ========== 归档 ==========
export interface StatusHistoryEntry {
  status: string;
  at: string;
}

export interface ArchiveListItem {
  id: string;
  title: string;
  status: string;
  archived_at: string | null;
  template_id: string;
  template_name: string | null;
  project_id: string | null;
  project_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ArchiveDetail {
  id: string;
  title: string;
  status: string;
  archived_at: string | null;
  template_id: string;
  template_name: string | null;
  project_id: string | null;
  project_name: string | null;
  variables: Record<string, string>;
  status_history: StatusHistoryEntry[];
  file_path: string | null;
  file_path_pdf: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}
```

同时在 `ContractResponse` 中添加 `archived_at` 和 `status_history` 字段：

```typescript
// 在 ContractResponse 中 status 之后添加：
  archived_at: string | null;
  status_history: StatusHistoryEntry[];
```

- [ ] **Step 2: 创建 archives.ts API 调用文件**

创建 `frontend/src/api/archives.ts`：

```typescript
import api from "./index";
import type {
  ArchiveListItem,
  ArchiveDetail,
  PaginatedResponse,
} from "../types";

// 归档列表
export async function listArchives(params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
  template_id?: string;
  project_id?: string;
  date_from?: string;
  date_to?: string;
}) {
  const res = await api.get<PaginatedResponse<ArchiveListItem>>("/archives", { params });
  return res.data;
}

// 归档详情
export async function getArchiveDetail(id: string) {
  const res = await api.get<ArchiveDetail>(`/archives/${id}`);
  return res.data;
}

// 获取归档文件下载 URL
export function getArchiveDownloadUrl(id: string, format: string = "word") {
  return `/api/v1/archives/${id}/download?format=${format}`;
}
```

- [ ] **Step 3: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit`

Expected: 无类型错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/archives.ts
git commit -m "feat: add archive types and API client"
```

---

### Task 8: 前端页面 — ArchiveSearchPage 重写

**Files:**
- Rewrite: `frontend/src/pages/ArchiveSearch/index.tsx`

- [ ] **Step 1: 重写 ArchiveSearchPage**

将 `frontend/src/pages/ArchiveSearch/index.tsx` 完全重写为：

```tsx
import { useState, useEffect, useCallback } from "react";
import {
  Table,
  Button,
  Space,
  Input,
  Tag,
  message,
  DatePicker,
  Select,
  Modal,
  Timeline,
  Descriptions,
  Typography,
} from "antd";
import {
  SearchOutlined,
  DownloadOutlined,
  EyeOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { ArchiveListItem, ArchiveDetail } from "../../types";
import * as archiveApi from "../../api/archives";
import * as templateApi from "../../api/templates";
import * as projectApi from "../../api/projects";

const { Text } = Typography;
const { RangePicker } = DatePicker;

const STATUS_LABELS: Record<string, { color: string; bg: string; label: string }> = {
  archived: { color: "#5B8C5A", bg: "#EFF5EF", label: "已归档" },
};

export default function ArchiveSearchPage() {
  // 列表状态
  const [archives, setArchives] = useState<ArchiveListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  // 过滤条件
  const [keyword, setKeyword] = useState("");
  const [templateFilter, setTemplateFilter] = useState<string | undefined>();
  const [projectFilter, setProjectFilter] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[string, string] | undefined>();

  // 下拉选项
  const [templateOptions, setTemplateOptions] = useState<{ value: string; label: string }[]>([]);
  const [projectOptions, setProjectOptions] = useState<{ value: string; label: string }[]>([]);

  // 详情弹窗
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<ArchiveDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 加载下拉选项
  useEffect(() => {
    templateApi.listTemplates({ page: 1, page_size: 200 }).then((res) => {
      setTemplateOptions(res.items.map((t) => ({ value: t.id, label: t.name })));
    });
    projectApi.listProjects({ page: 1, page_size: 200 }).then((res) => {
      setProjectOptions(res.items.map((p) => ({ value: p.id, label: p.name })));
    });
  }, []);

  const fetchArchives = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        template_id: templateFilter,
        project_id: projectFilter,
      };
      if (dateRange) {
        params.date_from = dateRange[0];
        params.date_to = dateRange[1];
      }
      const res = await archiveApi.listArchives(params as Parameters<typeof archiveApi.listArchives>[0]);
      setArchives(res.items);
      setTotal(res.total);
    } catch {
      message.error("获取归档列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, keyword, templateFilter, projectFilter, dateRange]);

  useEffect(() => {
    fetchArchives();
  }, [fetchArchives]);

  const handleSearch = () => {
    setPage(1);
    fetchArchives();
  };

  const handleReset = () => {
    setKeyword("");
    setTemplateFilter(undefined);
    setProjectFilter(undefined);
    setDateRange(undefined);
    setPage(1);
  };

  const openDetail = async (id: string) => {
    setDetailLoading(true);
    setDetailOpen(true);
    try {
      const d = await archiveApi.getArchiveDetail(id);
      setDetail(d);
    } catch {
      message.error("获取归档详情失败");
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ColumnsType<ArchiveListItem> = [
    {
      title: "合同标题",
      dataIndex: "title",
      render: (title: string, record: ArchiveListItem) => (
        <Button
          type="link"
          style={{ fontWeight: 500, color: "#1A1A1A", padding: 0 }}
          onClick={() => openDetail(record.id)}
        >
          {title}
        </Button>
      ),
    },
    {
      title: "模板",
      dataIndex: "template_name",
      width: 150,
      render: (name: string | null) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>{name || "-"}</Text>
      ),
    },
    {
      title: "项目",
      dataIndex: "project_name",
      width: 150,
      render: (name: string | null) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>{name || "-"}</Text>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (s: string) => {
        const st = STATUS_LABELS[s] || STATUS_LABELS.archived;
        return (
          <span
            style={{
              padding: "2px 12px",
              borderRadius: 6,
              fontSize: 12,
              color: st.color,
              background: st.bg,
              fontWeight: 500,
            }}
          >
            {st.label}
          </span>
        );
      },
    },
    {
      title: "归档时间",
      dataIndex: "archived_at",
      width: 170,
      render: (t: string | null) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>
          {t ? new Date(t).toLocaleString("zh-CN") : "-"}
        </Text>
      ),
    },
    {
      title: "操作",
      width: 160,
      render: (_: unknown, record: ArchiveListItem) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => openDetail(record.id)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            href={archiveApi.getArchiveDownloadUrl(record.id)}
          >
            下载
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ animation: "fadeIn 0.3s ease-out" }}>
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #E8E4DF",
          borderRadius: 16,
          overflow: "hidden",
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        }}
      >
        {/* 搜索栏 */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #E8E4DF",
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            alignItems: "center",
          }}
        >
          <Input
            placeholder="搜索合同标题"
            prefix={<SearchOutlined style={{ color: "#BFBFBF" }} />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 220, borderRadius: 8 }}
          />
          <Select
            placeholder="选择模板"
            value={templateFilter}
            onChange={setTemplateFilter}
            options={templateOptions}
            allowClear
            style={{ width: 180 }}
          />
          <Select
            placeholder="选择项目"
            value={projectFilter}
            onChange={setProjectFilter}
            options={projectOptions}
            allowClear
            style={{ width: 180 }}
          />
          <RangePicker
            onChange={(_, dateStrings) => {
              if (dateStrings[0] && dateStrings[1]) {
                setDateRange([dateStrings[0], dateStrings[1]]);
              } else {
                setDateRange(undefined);
              }
            }}
            style={{ borderRadius: 8 }}
          />
          <Button onClick={handleSearch} icon={<SearchOutlined />}>
            查询
          </Button>
          <Button onClick={handleReset} icon={<ReloadOutlined />}>
            重置
          </Button>
        </div>

        {/* 表格 */}
        <Table
          rowKey="id"
          columns={columns}
          dataSource={archives}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          style={{ borderRadius: 0 }}
        />
      </div>

      {/* 详情弹窗 */}
      <Modal
        title={
          <span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17, fontWeight: 500 }}>
            归档详情
          </span>
        }
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={700}
        loading={detailLoading}
      >
        {detail && (
          <div>
            <Descriptions column={2} bordered size="small" style={{ marginBottom: 24 }}>
              <Descriptions.Item label="合同标题" span={2}>
                <Text strong>{detail.title}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <span
                  style={{
                    padding: "2px 12px",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#5B8C5A",
                    background: "#EFF5EF",
                    fontWeight: 500,
                  }}
                >
                  已归档
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="归档时间">
                {detail.archived_at ? new Date(detail.archived_at).toLocaleString("zh-CN") : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="模板">
                {detail.template_name || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="项目">
                {detail.project_name || "-"}
              </Descriptions.Item>
            </Descriptions>

            {/* 变量值 */}
            {detail.variables && Object.keys(detail.variables).length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Text strong style={{ fontSize: 14, display: "block", marginBottom: 8 }}>
                  变量值
                </Text>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {Object.entries(detail.variables).map(([key, value]) => (
                    <Tag
                      key={key}
                      style={{
                        borderRadius: 6,
                        borderColor: "#E8E4DF",
                        color: "#B8860B",
                        background: "rgba(184,134,11,0.06)",
                      }}
                    >
                      {key}：{value}
                    </Tag>
                  ))}
                </div>
              </div>
            )}

            {/* 操作时间线 */}
            {detail.status_history && detail.status_history.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Text strong style={{ fontSize: 14, display: "block", marginBottom: 8 }}>
                  操作时间线
                </Text>
                <Timeline
                  items={detail.status_history.map((entry) => ({
                    color: entry.status === "archived" ? "green" : "blue",
                    children: (
                      <span>
                        <Text strong>{entry.status === "draft" ? "创建草稿" : entry.status === "archived" ? "已归档" : entry.status}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {new Date(entry.at).toLocaleString("zh-CN")}
                        </Text>
                      </span>
                    ),
                  }))}
                />
              </div>
            )}

            {/* 文件操作 */}
            <div style={{ display: "flex", gap: 8 }}>
              <Button
                icon={<DownloadOutlined />}
                href={archiveApi.getArchiveDownloadUrl(detail.id, "word")}
              >
                下载 Word
              </Button>
              <Button
                icon={<DownloadOutlined />}
                href={archiveApi.getArchiveDownloadUrl(detail.id, "pdf")}
              >
                下载 PDF
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
```

- [ ] **Step 2: 验证前端构建**

Run: `cd frontend && npm run build`

Expected: 构建成功，无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ArchiveSearch/index.tsx
git commit -m "feat: implement archive search page with filters, detail modal, and timeline"
```

---

### Task 9: 集成验证和 Progress Log 更新

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 运行后端全部测试，确认无回归**

Run: `cd backend && pytest tests/ -v`

Expected: 所有测试通过（含新增的 8 个 archives 测试）

- [ ] **Step 2: 前端构建验证**

Run: `cd frontend && npm run build`

Expected: 构建成功

- [ ] **Step 3: 更新 CLAUDE.md Progress Log**

在 Progress Log 末尾添加：

```
- [2026-06-13] 新增 | 模块3.5 | 完成档案归档与检索功能：Contract 模型扩展（archived_at + status_history）、自动归档、归档检索 API（关键词/模板/项目/时间过滤）、归档详情（操作时间线+文件下载）、前端 ArchiveSearchPage 重写、8 个后端测试通过
```

- [ ] **Step 4: 最终 Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update progress log - archive search feature completed"
```
