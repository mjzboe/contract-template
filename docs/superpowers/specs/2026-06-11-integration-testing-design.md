# 集成与测试设计

## 概述

第6步：集成与测试。采用分层递进策略，从单元测试到 API 集成测试到前端组件测试，边测边修 Bug，最后编写 README。

## 决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 测试范围 | 前后端都写自动化测试 | 用户明确要求 |
| 数据库策略 | 复用开发 PostgreSQL | 无需额外配置 |
| Bug 修复策略 | 边测边修 | 问题即时修复，减少回归 |
| 测试方案 | 方案 A：分层递进 | 每层独立可运行，问题定位精准 |

## 1. 测试架构与基础设施

### 后端

- **测试数据库**：复用开发 PostgreSQL（`localhost:5432/contract`），每个测试用例在事务中运行（`connection.begin()`），测试结束后 `rollback` 清除所有插入/修改数据，确保不污染开发库
- **测试客户端**：`httpx.AsyncClient` + `ASGITransport`，直连 FastAPI app
- **依赖覆盖**：通过 FastAPI `dependency_overrides` 注入测试用数据库 session
- **新增测试依赖**：`pytest-asyncio`

### 前端

- **测试框架**：Vitest + React Testing Library
- **API Mock**：MSW（Mock Service Worker），拦截 `/api/v1/*` 请求
- **测试文件结构**：与源码同目录，`*.test.tsx` 命名

### 目录结构

```
backend/tests/
├── conftest.py              # 全局 fixtures
├── test_variable_parser.py  # 变量解析单元测试
├── test_doc_generator.py    # 文档生成单元测试
├── test_templates_api.py    # 模板 API 集成测试
├── test_projects_api.py     # 项目 API 集成测试
├── test_contracts_api.py    # 合同 API 集成测试
└── test_e2e_flow.py         # 端到端流程测试

frontend/src/
├── pages/TemplateManage/index.test.tsx
├── pages/ContractGenerate/index.test.tsx
└── pages/Home/index.test.tsx
```

## 2. 后端单元测试

### 变量解析器测试（test_variable_parser.py）

| 测试用例 | 输入 | 预期输出 |
|---------|------|---------|
| 提取简单变量 | `"甲方：【公司名称】"` | `["公司名称"]` |
| 提取多个变量 | `"【公司名称】【法定代表人】【日期】"` | `["公司名称", "法定代表人", "日期"]` |
| 无变量 | `"普通文本无变量"` | `[]` |
| 去重 | `"【公司名称】【公司名称】"` | `["公司名称"]` |
| 混合格式 | `"【变量A】和{{变量B}}"` | `["变量A"]` |
| 从 DOCX 文件提取 | 样例模板文件 | 正确变量列表 |

### 文档生成器测试（test_doc_generator.py）

| 测试用例 | 说明 |
|---------|------|
| 简单替换 | `【公司名称】` → `"测试公司"` |
| 多变量替换 | 同时替换多个变量 |
| 未填充变量保留 | 未提供的变量保留原文 `【变量名】` |
| 生成文件可打开 | 生成的 DOCX 文件结构完整 |
| 批量变量映射 | 多行变量批量替换 |

## 3. 后端 API 集成测试

### 模板 API 测试（test_templates_api.py）

| 测试用例 | 方法 | 路径 | 预期 |
|---------|------|------|------|
| 创建分类 | POST | `/categories` | 201 + 分类对象 |
| 获取分类列表 | GET | `/categories` | 200 + 列表 |
| 上传模板 | POST | `/templates` (multipart) | 201 + 模板+解析变量 |
| 获取模板列表 | GET | `/templates` | 200 + 分页列表 |
| 获取模板详情 | GET | `/templates/{id}` | 200 + 详情 |
| 删除模板 | DELETE | `/templates/{id}` | 204 |
| 提取变量 | GET | `/templates/{id}/variables` | 200 + 变量列表 |

### 项目 API 测试（test_projects_api.py）

| 测试用例 | 方法 | 路径 | 预期 |
|---------|------|------|------|
| 创建项目 | POST | `/projects` | 201 + 项目对象 |
| 获取项目列表 | GET | `/projects` | 200 + 分页列表 |
| 获取项目详情 | GET | `/projects/{id}` | 200 + 详情含模板列表 |
| 获取去重变量 | GET | `/projects/{id}/deduplicated-variables` | 200 + 去重变量+来源映射 |
| 添加模板到项目 | POST | `/projects/{id}/templates` | 200 |

### 合同 API 测试（test_contracts_api.py）

| 测试用例 | 方法 | 路径 | 预期 |
|---------|------|------|------|
| 预览合同 | POST | `/contracts/preview` | 200 + 预览数据 |
| 生成合同 | POST | `/contracts` | 201 + 合同对象 |
| 导出 Word | GET | `/contracts/{id}/export?format=word` | 200 + DOCX |
| 导出 PDF | GET | `/contracts/{id}/export?format=pdf` | 200 + PDF |
| 解析 Excel | POST | `/contracts/parse-excel` | 200 + 表头+行数据 |
| 批量生成同步 | POST | `/contracts/batch-from-rows` | 200 + 合同列表 |
| 批量生成异步 | POST | `/contracts/batch-from-rows-async` | 200 + task_id |
| 查询任务状态 | GET | `/contracts/tasks/{id}` | 200 + 状态 |
| 下载 ZIP | GET | `/contracts/tasks/{id}/download-zip` | 200 + ZIP |

### 端到端流程测试（test_e2e_flow.py）

完整业务流程：创建分类 → 上传3个模板 → 确认变量 → 创建项目 → 关联模板 → 获取去重变量 → 填充变量 → 生成合同 → 导出 Word → 上传 Excel → 批量生成 → 下载 ZIP

## 4. 前端自动化测试

### 框架

Vitest + React Testing Library + MSW

### 覆盖范围

3个核心页面：首页、模板管理、合同生成。不覆盖审批中心和归档搜索（占位页面）。

### 首页测试（Home/index.test.tsx）

| 测试用例 | 说明 |
|---------|------|
| 渲染统计卡片 | 页面加载后显示统计卡片 |
| 渲染最近项目 | 显示最近项目列表 |
| API 错误处理 | API 返回错误时显示提示 |

### 模板管理页测试（TemplateManage/index.test.tsx）

| 测试用例 | 说明 |
|---------|------|
| 渲染模板列表 | 页面加载后显示模板表格 |
| 上传模板 | 点击上传按钮触发上传流程 |
| 删除模板 | 点击删除确认后调用删除 API |
| 查看变量 | 点击查看变量弹出 Modal |

### 合同生成页测试（ContractGenerate/index.test.tsx）

| 测试用例 | 说明 |
|---------|------|
| 步骤切换 | Steps 组件正确切换 |
| 创建项目 | Step 1 填写项目名称并创建 |
| 选择模板 | Step 2 显示可选模板列表 |
| 填充变量 | Step 3 显示变量表单 |
| 生成下载 | Step 4 触发生成+下载 |

### MSW Mock 设计

拦截所有 `/api/v1/*` 请求，返回预设数据，前端测试不依赖后端。

## 5. Bug 修复与 README

### Bug 修复流程

1. 先写 failing test 复现 Bug
2. 修复代码使测试通过
3. Progress Log 记录

### 常见预期 Bug 区域

- 文件上传：multipart 处理、Windows 路径
- DOCX 变量替换：特殊字符、编码
- 异步任务：task_manager 内存状态、并发
- 前端 API 调用：响应格式不匹配、错误处理缺失
- Excel 解析：空行处理、数据类型转换

### README 内容

1. 项目简介与核心功能
2. 技术栈
3. 本地运行步骤（Docker → 后端 → 前端）
4. 测试运行命令
5. 样例数据使用说明
6. 已知限制
