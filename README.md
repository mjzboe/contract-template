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
