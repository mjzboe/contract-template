# 档案归档与检索功能设计

## 概述

实现完整的档案归档与检索功能模块：合同生成后自动归档，支持关键词搜索、时间范围过滤、模板/项目过滤，详情页支持查看合同信息、下载文件、操作时间线。

当前状态：`ArchiveSearchPage` 为空壳页面，后端无任何归档相关实现。

## 方案选择

选择**方案 A：扩展现有 Contract 模型**，在 `contracts` 表上添加 `archived_at` 和 `status_history` 字段。

理由：
- 改动最小，不需要新表和数据迁移
- 合同与归档记录天然关联
- status_history JSONB 字段满足时间线需求，不需要事件溯源
- MVP 阶段减少表和代码量，降低风险

## 数据模型变更

### 新增字段

```sql
ALTER TABLE contracts ADD COLUMN archived_at TIMESTAMP;
ALTER TABLE contracts ADD COLUMN status_history JSONB DEFAULT '[]';

CREATE INDEX idx_contracts_archived ON contracts(archived_at) WHERE archived_at IS NOT NULL;
```

### status_history 结构

```json
[
  {"status": "draft", "at": "2026-06-13T10:00:00Z"},
  {"status": "generated", "at": "2026-06-13T10:05:00Z"},
  {"status": "archived", "at": "2026-06-13T10:05:01Z"}
]
```

### 状态机调整

`draft → generated → archived`

合同生成完成后自动归档，状态直接设为 `archived`，`archived_at` 设为当前时间。

## 后端 API

### 新增路由

```
GET  /api/v1/archives                          # 归档列表
GET  /api/v1/archives/{contract_id}            # 归档详情
GET  /api/v1/archives/{contract_id}/download   # 下载文件
```

### 列表 API

**请求参数**：
- `keyword` (str, optional): 按标题模糊搜索
- `template_id` (UUID, optional): 按关联模板过滤
- `project_id` (UUID, optional): 按关联项目过滤
- `date_from` (date, optional): 归档时间起始
- `date_to` (date, optional): 归档时间截止
- `page`, `page_size`: 分页

**返回字段**：contract id, title, status, archived_at, template_name, project_name, created_at

### 详情 API

在列表返回基础上额外返回：
- `variables`：变量值 JSON
- `status_history`：状态变更时间线
- `file_path`, `file_path_pdf`：文件路径

### 下载 API

复用现有合同导出逻辑，`format=word|pdf`。

### 文件结构

- `backend/app/api/archives.py` — API 路由
- `backend/app/services/archive_service.py` — 查询、过滤、详情业务逻辑
- 复用 `contract` 的 Pydantic schema 并扩展

### 搜索实现

keyword 搜索使用 SQL `ILIKE` 对 `title` 字段模糊匹配（SQLite 用 `LIKE`）。不引入全文搜索引擎。

## 自动归档集成

### 触发点

`contract_service.py` 的 `generate_contract()` 方法末尾，生成合同文件成功后：
1. 设置 `status = 'archived'`
2. 设置 `archived_at = datetime.utcnow()`
3. 追加 `status_history` 记录

批量生成（`batch_from_rows_async`）中每份合同独立归档。

## 前端页面

### 档案检索页布局

搜索栏 + 表格 + 分页：

- **搜索栏**：关键词输入、模板选择（下拉）、项目选择（下拉）、日期范围选择器、查询/重置按钮
- **表格列**：合同标题、模板名称、项目名称、归档时间、操作（详情/下载）
- **分页**：复用项目列表的分页模式

### 详情弹窗

三个区域：
1. **基本信息**：合同标题、状态、模板名称、项目名称、变量值列表
2. **操作时间线**：基于 `status_history` 渲染 Ant Design `Timeline` 组件
3. **文件操作**：下载 Word / PDF 按钮

### 组件结构

- `frontend/src/pages/ArchiveSearch/index.tsx` — 主页面（重写空壳）
- 搜索栏和表格直接在页面内实现，详情用 Modal
- 复用现有 API 层模式，新增 `frontend/src/api/archives.ts`

## 错误处理

- 搜索无结果：Ant Design `Empty` 组件
- 下载失败：`message.error` 提示
- 详情加载失败：Modal 内错误提示

## 测试策略

### 后端测试

- 列表过滤（keyword、template_id、project_id、日期范围）
- 详情查询（含 status_history）
- 下载接口
- 空结果返回

### 前端测试

- 搜索交互（输入、选择、查询）
- 分页切换
- 详情弹窗展示

### 集成测试

- 生成合同 → 自动归档 → 档案检索 → 下载（端到端流程）
