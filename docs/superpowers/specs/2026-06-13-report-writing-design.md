---
name: report-writing-design
description: 第7步项目报告撰写的设计规格 — ≤10页 Markdown 报告，含9个必选部分，Pandoc 导出 Word
---

# 第7步：项目报告撰写 — 设计规格

## 目标

撰写一份 ≤10 页的项目报告（中文 + 英文技术术语），覆盖 CLAUDE.md 要求的 9 个必选部分，以 Markdown 格式编写，通过 Pandoc 导出为 Word 文档。

## 输出

- **主文件**：`docs/report.md` — 完整报告 Markdown
- **导出文件**：`docs/report.docx` — Pandoc 导出的 Word 版本

## 报告结构

### 1. 业务理解（~1页）

- 签字页业务场景：IPO 文件中多方签字，同一人信息在数十份签字页模板中重复出现
- 6 大痛点概述（P1-P6）：模板分散、版本混乱、重复录入、审批不透明、格式损坏、缺乏归档
- 核心价值主张：变量去重 — 一次填写，多模板生效
- 核心业务流程 Mermaid 图：选择模板 → 解析变量 → 填充表单 → 实时预览 → 确认生成 → 导出文件

### 2. 软件架构（~1.5页）

- 前后端分离架构 Mermaid 图：React ↔ FastAPI ↔ PostgreSQL/SQLite ↔ Local Storage
- 技术选型理由：
  - FastAPI：异步高性能，自动 OpenAPI 文档
  - React + Ant Design：组件丰富，适合管理后台
  - SQLAlchemy 2.0 async：类型安全，异步支持
  - docxtpl/python-docx：成熟的 Word 模板渲染方案
- 3 层架构说明：API routes → Services → Models
- MVP 简化项概览（SQLite 替代 PostgreSQL、本地存储替代 MinIO 等）

### 3. 数据模型（~1页）

- ER 关系 Mermaid 图
- 7 张核心表及其关系：
  - users → templates/contracts/approvals（创建者）
  - categories → templates（分类归属）
  - templates → template_versions（一对多版本）
  - templates → contracts（模板关联合同）
  - contracts → approvals → approval_records（审批链）
- 关键字段与约束说明

### 4. 关键接口/流程（~1.5页）

- 核心 API 端点分类列表：
  - 模板管理：CRUD + 版本管理
  - 变量系统：提取 + 去重
  - 合同生成：预览/生成/导出/批量
  - 审批流：发起/审批/记录
- 签字页生成完整流程 Mermaid 图：选模板 → 解析变量 → 跨模板去重 → 填变量 → 生成 → 下载
- 变量去重机制详细说明：同一变量名在多模板中合并，一次填写全部生效

### 5. 实现权衡（~1页）

- MVP 简化项对照表：

| 原设计 | MVP 实现 | 简化理由 |
|--------|---------|---------|
| PostgreSQL | SQLite | 减少部署依赖 |
| MinIO 对象存储 | 本地文件系统 | 减少基础设施 |
| 多步审批流 | 单步审批 | 降低复杂度 |
| Celery 异步任务 | asyncio 后台任务 | 减少依赖 |
| 浏览器内 PDF 预览 | 下载预览 | 降低实现难度 |
| 邮件/应用内通知 | 无通知 | MVP 非核心 |

- 额外实现：RBAC 权限系统（4 角色）+ 审计日志（DB+JSONL 混合存储），超出 MVP 范围

### 6. 测试/验证结果（~1页）

- 测试统计：78 后端测试 + 10 前端测试 = 88 测试全部通过
- 后端测试覆盖：
  - variable_parser 单元测试 8 个
  - doc_generator 单元测试 7 个
  - auth API 测试 24 个
  - audit API 测试 10 个
  - templates/projects/contracts API 集成测试
  - e2e 端到端测试
- 前端测试覆盖：Home 3 个 + TemplateManage 3 个 + ContractGenerate 4 个
- 端到端验证描述：Excel 导入 3 行 → 异步生成 9 份合同 → ZIP 下载

### 7. 未解决问题（~0.5页）

- 已知限制列表：
  - SQLite 并发写入限制
  - 无浏览器内 PDF 预览
  - 无邮件/消息通知
  - 审批流为单步
  - 文件存储无分布式支持

### 8. 如再给一个月（~0.5页）

- 可实现的功能升级：
  - PostgreSQL + MinIO 生产级部署
  - 多步审批流 + 审批配置
  - 浏览器内 PDF 预览
  - Celery + Redis 异步任务队列
  - 邮件/应用内通知
  - 全文搜索（Elasticsearch）
  - 合同模板在线编辑器

### 9. AI 工具使用日志（~2页）

- 按开发步骤（1-6 + RBAC）梳理，每步包含：
  - 使用的 AI 工具：Claude Code（主要）
  - 生成的内容类型：代码、测试、文档、设计
  - 出错点及修复方式
  - 验证方式：测试通过、构建验证、手动检查
- 数据来源：
  - `git log --oneline` 提取时间线
  - CLAUDE.md Progress Log 提取每步完成内容
  - `docs/superpowers/specs/` 设计文档提取设计过程
- AI 交互模式：指令式（描述需求）+ 迭代式（审阅修改）+ 验证式（运行测试确认）

## 技术实现

### Mermaid 图表

报告中计划包含 4 个 Mermaid 图表：
1. 业务流程图（flowchart TD）
2. 系统架构图（flowchart LR）
3. ER 关系图（erDiagram）
4. 审批状态机（stateDiagram-v2）

如果 Pandoc 导出时 Mermaid 无法渲染，回退为文字+ASCII 描述。

### 导出流程

```bash
# 安装 Pandoc（如未安装）
# choco install pandoc  # Windows

# 导出 Word
pandoc docs/report.md -o docs/report.docx

# 如果需要 PDF（需安装 LaTeX）
# pandoc docs/report.md -o docs/report.pdf
```

### 语言风格

- 中文撰写，技术术语保留英文原文（FastAPI, SQLAlchemy, React, etc.）
- 简洁专业，避免冗余描述
- 表格优先于文字列表（信息密度更高）

## 验收标准

- [ ] 报告覆盖全部 9 个必选部分
- [ ] 篇幅 ≤ 10 页（Word 导出版）
- [ ] 包含至少 3 个 Mermaid 图表
- [ ] AI 使用日志详细记录各阶段使用情况
- [ ] Pandoc 成功导出 Word 文档
- [ ] 中文撰写 + 英文技术术语
