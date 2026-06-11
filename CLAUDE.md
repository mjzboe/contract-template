# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 开发流程规范（每次对话必须遵守）

### 1. 对话启动检查

每次新对话开始时，必须执行以下三步：

1. **阅读本文件（CLAUDE.md）**：理解项目全貌、当前进展和约束
2. **识别当前步骤**：对照"Implementation Steps & Time Budget"（第1-7步），判断项目进展到哪一步
3. **识别当前模块**：对照"Feature Modules & Priorities"（3.1-3.5），判断正在开发开发文档中的哪一部分

在首次回复中明确声明：
> 当前进展：第 X 步（步骤名称）| 正在开发：模块 Y（模块名称）

### 2. 进展记录

每次取得实质性进展后，更新本文件底部的"Progress Log"部分，记录格式：

```
- [日期] 第X步 | 模块Y | 完成内容简述
```

包括但不限于：完成了某个功能、创建了某个文件、修复了某个问题、做出了某个技术决策。

### 3. 步骤切换

当某一步骤的所有任务完成，准备进入下一步骤时：
- 在 Progress Log 中标记该步骤完成
- 声明进入下一步骤

---

## Project Overview

Law firm IPO signature page management system. Core workflow: **Create Project → Select Templates → Variable Deduplication → Fill Variables → Generate Signature Pages → Download**. The system eliminates repetitive data entry when the same shareholder/director/lawyer information appears across dozens of signature page templates.

## Business Domain

- **Signature Page (签字页)**: A document page in IPO filings requiring signatures from stakeholders
- **Variable syntax in templates**: `【变量名】` (Chinese square brackets), NOT `{{变量名}}` — the PRD uses curly braces but the actual requirement uses square brackets
- **Variable deduplication is the key feature**: When multiple templates share the same variable name (e.g., `【张三】`), filling it once applies to all templates — this is the core value proposition

### User Pain Points

| ID | Pain Point | Severity | Solution Direction |
|----|-----------|----------|-------------------|
| P1 | Templates scattered everywhere, hard to find | High | Unified template library + category tags |
| P2 | Version confusion, unclear which is latest | High | Version control + master version flag |
| P3 | Repetitive contract data entry, low efficiency | High | Variable templates + auto-fill |
| P4 | Opaque approval process, hard to track progress | Medium | Approval workflow + status board |
| P5 | Formatting breaks after contract generation | Medium | Template preview + format validation |
| P6 | Lack of contract archiving and search | Medium | Contract archive + full-text search |

### Core Business Flow

```
选择模板 → 解析变量 → 填充表单 → 实时预览 → 确认生成 → 导出文件
```

### Approval State Machine

```
草稿 → 待审批 → 审批中 → 已通过 → 已归档
                ↓
              已驳回 → 草稿
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Ant Design 5.x + Vite |
| State Management | Zustand / React Query |
| Backend | Python 3.11+ / FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 (or SQLite for MVP simplification) |
| Cache/Queue | Redis 7 + Celery (or simplify for MVP) |
| File Storage | MinIO (or local filesystem for MVP) |
| Document Processing | python-docx + docxtpl (Word template rendering) |
| PDF Generation | WeasyPrint |
| Migration | Alembic |

## Backend Dependencies (requirements.txt)

```
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0

# Database
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
alembic==1.13.1

# Validation
pydantic==2.5.3
pydantic-settings==2.1.0

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Document Processing
python-docx==1.1.0
docxtpl==0.16.7
weasyprint==60.2
openpyxl==3.1.2  # Excel processing

# Async Tasks
celery[redis]==5.3.6

# Object Storage
minio==7.2.3

# Utils
python-multipart==0.0.6  # File upload
httpx==0.26.0            # HTTP client
```

## Project Structure (Planned)

```
contract-template/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # DB connection pool
│   │   ├── dependencies.py      # DI
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── base.py          # Base model
│   │   │   ├── user.py
│   │   │   ├── template.py
│   │   │   ├── template_version.py
│   │   │   ├── contract.py
│   │   │   └── approval.py
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   │   ├── user.py
│   │   │   ├── template.py
│   │   │   ├── contract.py
│   │   │   └── approval.py
│   │   ├── api/                 # API routes
│   │   │   ├── router.py        # Route aggregation
│   │   │   ├── auth.py
│   │   │   ├── templates.py
│   │   │   ├── contracts.py
│   │   │   ├── approvals.py
│   │   │   └── archives.py
│   │   ├── services/            # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── template_service.py
│   │   │   ├── contract_service.py
│   │   │   ├── approval_service.py
│   │   │   └── archive_service.py
│   │   ├── tasks/               # Celery async tasks
│   │   │   ├── celery_app.py
│   │   │   ├── batch_generate.py
│   │   │   ├── pdf_export.py
│   │   │   └── notification.py
│   │   └── utils/
│   │       ├── security.py      # JWT/password handling
│   │       ├── variable_parser.py  # Variable extraction
│   │       ├── doc_generator.py    # Document generation
│   │       └── storage.py       # MinIO operations
│   ├── alembic/                 # DB migrations
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_templates.py
│   │   ├── test_contracts.py
│   │   └── test_approvals.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                 # API calls
│   │   ├── components/          # Shared components
│   │   ├── pages/
│   │   │   ├── TemplateManage/
│   │   │   ├── ContractGenerate/
│   │   │   ├── ApprovalCenter/
│   │   │   └── ArchiveSearch/
│   │   ├── stores/              # Zustand stores
│   │   ├── hooks/               # Custom hooks
│   │   ├── utils/
│   │   └── types/               # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
└── docker-compose.yml
```

## Development Commands

Once the project is scaffolded:

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Database migrations
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head

# Run tests
cd backend
pytest tests/ -v
pytest tests/test_templates.py -v  # single test file
```

## Variable System

### Variable Syntax Design

```
简单变量:     {{变量名}}
带默认值:     {{变量名|默认值}}
带校验:       {{变量名:type:rule}}  // e.g. {{身份证:text:idcard}}
循环变量:     {{#列表}}...{{/列表}}
条件变量:     {{?条件}}...{{/条件}}
```

**IMPORTANT**: The PRD above uses `{{变量名}}` syntax, but the actual project requirement uses `【变量名】` (Chinese square brackets). The variable parser must handle `【变量名】` as the primary format.

### Variable Types

| Type | Identifier | Validation Examples |
|------|-----------|-------------------|
| Text | text | maxlength, pattern |
| Number | number | min, max |
| Date | date | format |
| Select | select | options |
| ID Card | idcard | 18-digit validation |
| Phone | phone | 11-digit validation |
| Money | money | decimal places |

### Variable Parsing Regex

```python
import re

# Simple variable
SIMPLE_VAR_PATTERN = r'\{\{(\w+)\}\}'

# With default value
DEFAULT_VAR_PATTERN = r'\{\{(\w+)\|([^}]+)\}\}'

# With type validation
TYPED_VAR_PATTERN = r'\{\{(\w+):(\w+)(?::([^}]+))?\}\}'

# Loop variable
LOOP_VAR_PATTERN = r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}'

# Conditional variable
CONDITION_VAR_PATTERN = r'\{\{\?(\w+)\}\}(.*?)\{\{/\1\}\}'

# Chinese bracket format (actual requirement)
CHINESE_BRACKET_PATTERN = r'【(.+?)】'
```

## Feature Modules & Priorities

### Template Management (3.1)

| Feature | Priority | Description |
|---------|----------|-------------|
| Template creation | P0 | Upload Word/PDF templates, online editing |
| Template categories | P0 | Multi-level category tree, custom tags |
| Template search | P0 | Keyword search + category filter |
| Template preview | P0 | Online preview of template content |
| Version management | P1 | Save history versions, support rollback |
| Master version flag | P1 | Mark current active version |

### Variable System (3.2)

| Feature | Priority | Description |
|---------|----------|-------------|
| Variable definition | P0 | Mark variable positions in templates |
| Variable types | P0 | Text, date, number, select, etc. |
| Variable validation | P1 | Required, format validation (e.g. ID card) |
| Variable presets | P2 | Common variable library (party A, party B, date, etc.) |

### Contract Generation (3.3)

| Feature | Priority | Description |
|---------|----------|-------------|
| Variable fill | P0 | Form-based variable filling |
| Real-time preview | P0 | Preview generation result while filling |
| Contract export | P0 | Export Word/PDF format |
| Batch generation | P1 | Import Excel for batch generation |
| History | P1 | Save generation history, re-download |

### Approval Flow (3.4)

| Feature | Priority | Description |
|---------|----------|-------------|
| Approval config | P1 | Configure approval nodes and approvers |
| Initiate approval | P1 | Submit contract for approval after generation |
| Approval actions | P1 | Approve/reject/transfer |
| Approval records | P1 | Record opinions and timestamps |
| Status notification | P2 | Email/in-app notification on result |

### Contract Archive (3.5)

| Feature | Priority | Description |
|---------|----------|-------------|
| Auto-archive | P1 | Auto-archive after approval |
| Search | P1 | Search by keyword/time/status |
| Details | P1 | View content and approval records |
| Download | P1 | Download archived contracts |

## Key API Endpoints

### Template Management

```
GET    /api/v1/templates                          # List (query: page, page_size, category_id, keyword, status)
POST   /api/v1/templates                          # Create (body: name, category_id, tags[], file)
GET    /api/v1/templates/{template_id}            # Detail
PUT    /api/v1/templates/{template_id}            # Update
DELETE /api/v1/templates/{template_id}            # Delete
GET    /api/v1/templates/{template_id}/versions   # Version list
PUT    /api/v1/templates/{template_id}/versions/{version_id}/set-master  # Set master version
```

### Contract Generation

```
GET  /api/v1/templates/{template_id}/variables    # Parse template variables
POST /api/v1/contracts/preview                     # Preview (body: template_id, variables)
POST /api/v1/contracts                             # Generate (body: template_id, variables, title)
GET  /api/v1/contracts/{contract_id}/export        # Export (query: format=word|pdf)
POST /api/v1/contracts/batch                       # Batch generate (body: template_id, excel_file)
POST /api/v1/contracts/parse-excel                 # Parse Excel only, return headers+rows (no generation)
POST /api/v1/contracts/batch-from-rows             # Batch generate from selected rows (body: project_id, rows, selected_indices)
POST /api/v1/contracts/batch-from-rows-async       # Async batch generate (returns task_id)
GET  /api/v1/contracts/tasks/{task_id}             # Poll async task status
GET  /api/v1/contracts/tasks/{task_id}/download-zip # Download task zip
GET  /api/v1/contracts/project/{project_id}/download-zip # Download project zip
```

### Approval Flow

```
POST /api/v1/approvals                             # Initiate (body: contract_id, approver_ids[])
GET  /api/v1/approvals/pending                     # Pending list
POST /api/v1/approvals/{approval_id}/action        # Action (body: action=approve|reject|transfer, comment, transfer_to?)
GET  /api/v1/approvals/{approval_id}/records       # Approval records
```

## Database Schema

### Core Tables

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    parent_id UUID REFERENCES categories(id),
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Templates
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    category_id UUID REFERENCES categories(id),
    tags JSONB DEFAULT '[]',
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Template Versions
CREATE TABLE template_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES templates(id) ON DELETE CASCADE,
    version_number VARCHAR(20) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    variables JSONB DEFAULT '[]',
    is_master BOOLEAN DEFAULT false,
    change_log TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(template_id, version_number)
);

-- Contracts
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    template_id UUID REFERENCES templates(id),
    template_version_id UUID REFERENCES template_versions(id),
    variables JSONB NOT NULL,
    file_path VARCHAR(500),
    file_path_pdf VARCHAR(500),
    status VARCHAR(20) DEFAULT 'draft',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Approvals
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID REFERENCES contracts(id),
    status VARCHAR(20) DEFAULT 'pending',
    current_step INT DEFAULT 1,
    total_steps INT NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Approval Records
CREATE TABLE approval_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id UUID REFERENCES approvals(id) ON DELETE CASCADE,
    step INT NOT NULL,
    operator_id UUID REFERENCES users(id),
    action VARCHAR(20) NOT NULL,
    comment TEXT,
    transfer_to UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_templates_category ON templates(category_id);
CREATE INDEX idx_templates_status ON templates(status);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_created_by ON contracts(created_by);
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_template_versions_master ON template_versions(template_id, is_master);
```

## Architecture Notes

- **3-layer backend**: API routes → Services → Models. Business logic lives in `services/`, not in route handlers.
- **Variable parsing**: Regex-based extraction from DOCX using `【变量名】` pattern. See variable_parser.py for the regex patterns supporting simple vars, defaults, typed vars, loop vars, and condition vars.
- **Async task flow**: Batch generation and PDF export run through Celery workers. Frontend polls task status via `GET /api/v1/contracts/batch/{task_id}`.
- **File storage abstraction**: All file I/O goes through `utils/storage.py`, making it swappable between local filesystem and MinIO.
- **Approval state machine**: `draft → pending → in_review → approved → archived`, with `rejected → draft` branch.

## MVP Scope (7-day / 14-hour deadline)

Simplifications for the initial build:
- Auth: simple JWT, no role-based access (mock roles)
- Database: can use SQLite instead of PostgreSQL
- File storage: local filesystem instead of MinIO
- PDF preview: download-only instead of in-browser preview
- Approval: single-step approval instead of multi-step workflow
- Notifications: skip email/in-app notifications

### Implementation Steps & Time Budget

| Step | Description | Time |
|------|-------------|------|
| 1 | Understand business (signature page flow, core objects, variable dedup) | ~1h |
| 2 | Tech selection & architecture design (data model, API, tradeoff decisions) | ~1h |
| 3 | Project scaffolding (FastAPI init, DB tables, React init, CORS, sample DOCX) | ~1.5h |
| 4 | Backend core (template upload, variable extraction, dedup, project CRUD, doc generation, download, Excel import) | ~4h |
| 5 | Frontend core (project list, create project, variable fill form, generate & download, Excel import) | ~4h |
| 6 | Integration & testing (end-to-end flow, sample templates, bug fixes, README) | ~1.5h |
| 7 | Report writing (≤10 pages) | ~1h |

**Total: ~14h maximum. Exceeding this is penalized.**

### Core Evaluation Criteria

1. Working minimum viable loop end-to-end
2. Ability to articulate tradeoffs clearly
3. Clear documentation of AI tool usage and boundaries

## Acceptance Criteria

### Functional

| Module | Test Case | Expected Result |
|--------|-----------|----------------|
| Template mgmt | Upload Word template | Successfully uploaded, variables correctly parsed |
| Template mgmt | Template list | Paginated display, search/filter works |
| Variable system | Variable parsing | Correctly identifies `【变量名】` format |
| Variable system | Variable filling | Form renders correctly, validation works |
| Contract gen | Real-time preview | Preview updates as variables are filled |
| Contract gen | Export Word | Correct format, complete variable replacement |
| Contract gen | Export PDF | Correct format, opens normally |
| Version mgmt | Version list | Shows all historical versions |
| Version mgmt | Version rollback | Can rollback to specified version |
| Approval | Initiate approval | Correctly creates approval flow |
| Approval | Approval actions | Approve/reject state transitions correct |

### Performance

| Metric | Target |
|--------|--------|
| Template list load | < 1s |
| Single contract generation | < 3s |
| Word export | < 3s |
| PDF export | < 5s (≤50 pages) |
| Batch generation (100) | < 60s |

### Security

- User permission isolation (user/admin)
- JWT token expiry and refresh mechanism
- Sensitive operation audit logging
- File upload type and size restrictions
- SQL injection prevention (ORM parameterized queries)
- XSS prevention (frontend input escaping)

## Risks & Dependencies

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Word template parsing complexity | Medium | Use mature lib docxtpl, limit template format |
| PDF format compatibility | Medium | Multi-browser testing, provide Word fallback |
| Approval flow requirement changes | High | Design flexible flow config, leave extension points |
| Large file upload performance | Medium | Chunked upload, file size limit |
| Concurrent generation pressure | Medium | Celery async queue, rate limiting |

## Report Requirements (≤10 pages)

Must include:
1. **Business understanding**: Core pain points of signature page business and solution approach
2. **Software architecture**: Frontend/backend architecture diagram, tech selection rationale
3. **Data model**: Core table structures and relationships
4. **Key interfaces/flows**: API design and business flow diagrams
5. **Implementation tradeoffs**: What was simplified, why, and what would be done with more time
6. **Test/validation results**: Screenshots or descriptions of working flows
7. **Unresolved issues**: Known limitations
8. **If given another month**: What could be achieved
9. **AI tool usage log** (evaluated separately): Which AI tools, which stages, where errors occurred, how verified

## Key Deliverables

- Working end-to-end flow: create project → select templates → fill deduplicated variables → generate signature pages → download DOCX
- README with local reproduction steps
- Report (≤10 pages) covering: business understanding, architecture, data model, API design, tradeoffs, test results, AI tool usage log

---

## Progress Log

- [2026-06-09] 第1步 | 全局 | 完成业务理解，梳理签字页业务核心流程与痛点
- [2026-06-09] 第2步 | 全局 | 完成技术选型与架构设计，确定 React+FastAPI 技术栈
- [2026-06-09] 第2步 | 全局 | 完成数据模型设计、API 接口设计、数据库表结构设计
- [2026-06-09] 第1-2步 | 全局 | 创建 CLAUDE.md，整合开发文档与完成步骤内容，建立进展追踪机制
- [2026-06-09] 第3步 | 全局 | 完成后端骨架搭建（FastAPI + SQLAlchemy + Celery），health check 接口验证通过
- [2026-06-09] 第3步 | 全局 | 完成前端骨架搭建（Vite + React + TS + Ant Design），路由和布局配置完成，构建验证通过
- [2026-06-09] 第3步 | 全局 | 创建 docker-compose.dev.yml（PostgreSQL 15 + Redis 7），需启动 Docker Desktop 后运行
- [2026-06-09] 第3步 | 全局 | 生成 3 个样例签字页 DOCX 模板（股东会决议/董事会决议/律师见证函），包含【变量名】占位符
- [2026-06-09] 第3步 | 全局 | **第3步完成** — 项目骨架搭建完毕，可进入第4步后端核心功能开发
- [2026-06-10] 第4步 | 模块3.1+3.2 | 完成模板上传与变量提取功能：Category/Template/TemplateVersion/User 模型、variable_parser.py（【变量名】解析+跨模板去重）、Pydantic schemas、template_service.py、API 路由（CRUD+变量提取）、Alembic 初始迁移
- [2026-06-10] 第4步 | 模块3.2 | 完成变量去重功能：Project 模型+多对多关联表、project_service.py（项目CRUD+跨模板变量去重）、deduplicated-variables API（含变量来源映射）、Alembic 迁移
- [2026-06-10] 第4步 | 模块3.3 | 完成文档生成与下载：doc_generator.py（【变量名】→值替换）、Contract 模型+schemas、contract_service.py（预览/生成/导出）、API 路由（preview/generate/export/download）、FileResponse 下载
- [2026-06-10] 第4步 | 模块3.3 | 完成 Excel 批量导入：openpyxl 解析 Excel 表头为变量名、每行生成一份合同、batch_generate API、创建样例 Excel
- [2026-06-10] 第4步 | 全局 | **第4步后端核心功能完成** — 5个功能点全部实现并验证通过
- [2026-06-10] 第5步 | 前端 | 完成前端核心功能开发：类型定义更新（对齐后端 schema）、API 调用层（templates/projects/contracts）、模板管理页（列表/上传/删除/变量查看）、合同生成页（Steps 流程：创建项目→选模板→填变量→生成下载）、首页仪表盘（统计卡片+最近项目）、构建验证通过、前后端代理联通
- [2026-06-11] 第5步 | 模块3.3 | 三个功能改进点实施完成：(1) Excel 批量导入移到 Step 2 并实现多行预览+勾选 — 后端新增 parse-excel/batch-from-rows API，前端 Step 2 集成 Excel 上传+Table 行选择；(2) 异步导出 — 后端新增 task_manager.py（内存任务状态+asyncio 后台任务）、batch-from-rows-async/tasks/{id} API，前端轮询+进度展示；(3) zip 打包+文件名优化 — 后端 build_zip() 打包+有意义文件名（模板名_变量摘要），前端 ZIP 下载按钮
- [2026-06-11] 第5步 | 模块3.3 | 端到端测试通过：Excel 解析 3 行 → 异步生成 9 份（3行×3模板）→ ZIP 下载 320KB，前后端构建均通过
- [2026-06-11] 第6步 | 全局 | 完成后端单元测试（variable_parser 8个 + doc_generator 7个）+ API 集成测试（templates 7个 + projects 5个 + contracts 8个 + e2e 1个）= 41 个测试全部通过；添加分类 API 路由；修复 conftest.py 事件循环问题
- [2026-06-11] 第6步 | 全局 | 完成前端组件测试（Home 3个 + TemplateManage 3个 + ContractGenerate 4个）= 10 个测试全部通过；MSW Mock 基础设施；matchMedia polyfill
- [2026-06-11] 第6步 | 全局 | 完成 README.md 编写（项目简介、技术栈、本地运行、测试命令、已知限制）
- [2026-06-11] 第6步 | 全局 | **第6步完成** — 集成与测试全部完成，可进入第7步报告撰写
