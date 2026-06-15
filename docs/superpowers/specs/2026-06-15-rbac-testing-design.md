# RBAC 权限矩阵 + 项目管理测试设计

日期：2026-06-15

## 背景

第7步完成后，新增了 RBAC 权限校验（`require_role` + `_can_access`）和项目管理功能（编辑/删除/用户隔离），但测试未同步更新。需要从第6步重新进行测试，确保所有新增功能的正确性。

## 测试范围

- 后端：权限矩阵测试 + 项目管理 CRUD + 合同/档案用户隔离 + dedup 端点权限修复
- 前端：ProjectManage 页面组件测试

## 1. 后端权限矩阵测试 (`test_rbac_matrix.py`)

### 权限矩阵

| API 端点 | Method | super_admin | template_admin | approver | user | 无 token |
|---------|--------|:-----------:|:--------------:|:--------:|:----:|:--------:|
| /projects | POST | 200 | 200 | 200 | 200 | 401 |
| /projects | GET | 200(全部) | 200(全部) | 200(自己) | 200(自己) | 401 |
| /projects/{id} | GET | 200 | 200 | 200(自己)/403(他人) | 200(自己)/403(他人) | 401 |
| /projects/{id} | PUT | 200 | 200 | 200(自己)/403(他人) | 200(自己)/403(他人) | 401 |
| /projects/{id} | DELETE | 200 | 403 | 403 | 403 | 401 |
| /projects/{id}/deduplicated-variables | GET | 200 | 200 | 200 | 200 | 401 |
| /projects/{id}/excel-template | GET | 200 | 200 | 200 | 200 | 401 |
| /contracts | POST | 200 | 200 | 200 | 200 | 401 |
| /contracts | GET | 200(全部) | 200(全部) | 200(自己) | 200(自己) | 401 |
| /contracts/{id} | GET | 200 | 200 | 200(自己)/403(他人) | 200(自己)/403(他人) | 401 |
| /contracts/{id}/export | GET | 200 | 200 | 200(自己)/403(他人) | 200(自己)/403(他人) | 401 |
| /contracts/{id} | DELETE | 200 | 403 | 403 | 403 | 401 |
| /archives | GET | 200(全部) | 200(全部) | 200(自己) | 200(自己) | 401 |
| /archives/{id} | GET | 200 | 200 | 200(自己)/403(他人) | 200(自己)/403(他人) | 401 |
| /archives/{id}/download | GET | 200 | 200 | 200(自己)/403(他人) | 200(自己)/403(他人) | 401 |

### 实现方式

- `@pytest.mark.parametrize` 参数化 `(endpoint_key, method, role, expected_status)`
- 每个测试用例自动构造请求（需要先创建模板/项目/合同作为前置数据）
- "自己/他人"隔离测试：创建两个不同角色的用户，分别创建资源，交叉访问

### 测试分组

1. **无 token 保护测试**：所有受保护端点在无 token 时返回 401
2. **角色权限测试**：每个端点 × 每个角色的预期状态码
3. **资源隔离测试**：`_can_access` / `_can_access_contract` 逻辑验证

## 2. 项目管理 CRUD 测试补充 (`test_projects_api.py`)

### 新增测试用例

| 测试 | 描述 |
|------|------|
| test_update_project_name | 修改项目名称 |
| test_update_project_templates | 修改关联模板，验证变量自动重新去重 |
| test_update_project_status | 修改项目状态 |
| test_delete_project_by_admin | super_admin 删除项目成功 |
| test_delete_project_forbidden | 非 super_admin 删除项目返回 403 |
| test_project_user_isolation | 用户 A 创建的项目，用户 B 无法查看/编辑 |
| test_admin_sees_all_projects | super_admin/template_admin 可看到所有用户的项目 |
| test_list_projects_keyword_filter | 关键词搜索过滤 |
| test_list_projects_status_filter | 状态过滤 |

## 3. 合同/档案用户隔离补充

### `test_contracts_api.py` 新增

| 测试 | 描述 |
|------|------|
| test_contract_user_isolation | 用户 A 生成的合同，用户 B 无法查看详情 |
| test_contract_export_isolation | 用户 B 无法导出用户 A 的合同 |
| test_contract_list_user_scoping | 普通用户列表只返回自己的合同 |

### `test_archives_api.py` 新增

| 测试 | 描述 |
|------|------|
| test_archive_user_isolation | 用户 A 的归档，用户 B 无法查看详情 |
| test_archive_download_isolation | 用户 B 无法下载用户 A 的归档 |
| test_archive_list_user_scoping | 普通用户归档列表只返回自己的 |

## 4. 前端 ProjectManage 页面测试

### 文件：`frontend/src/pages/ProjectManage/index.test.tsx`

| 测试 | 描述 |
|------|------|
| renders project table | 页面渲染表格和搜索栏 |
| loads and displays projects | API 调用后表格显示项目数据 |
| search by keyword | 输入关键词触发搜索 |
| filter by status | 状态筛选器工作 |
| open detail modal | 点击项目名打开详情弹窗 |
| open edit modal | 点击编辑按钮打开编辑弹窗 |
| delete with confirmation | 删除按钮触发 Popconfirm |
| navigate to generate | 点击"生成"跳转到合同生成页 |

## 5. 代码修复

- `GET /projects/{project_id}/deduplicated-variables` 添加 `require_role("user", "template_admin", "approver", "super_admin")` 保护

## 预期测试数量

- `test_rbac_matrix.py`：~30 个参数化测试用例
- `test_projects_api.py` 补充：~9 个
- `test_contracts_api.py` 补充：~3 个
- `test_archives_api.py` 补充：~3 个
- `ProjectManage/index.test.tsx`：~8 个
- **总计新增：~53 个测试**
