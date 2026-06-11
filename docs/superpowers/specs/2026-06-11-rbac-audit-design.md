# RBAC 权限与审计系统设计

## 概述

为合同模板系统新增 RBAC 多角色权限控制和审计日志功能。权限模型定义 4 个角色，审计系统覆盖数据变更追踪、登录审计、文件操作审计三类场景，采用数据库+文件混合存储。

## 1. RBAC 权限模型

### 1.1 角色定义

| 角色 | 代码 | 权限范围 |
|------|------|---------|
| 超级管理员 | `super_admin` | 全部权限，含用户管理、角色分配、审计查看 |
| 模板管理员 | `template_admin` | 模板 CRUD、版本管理、分类管理 |
| 审批人 | `approver` | 审批/驳回/转交合同、查看审批列表 |
| 普通用户 | `user` | 创建项目、生成合同、下载自己创建的合同 |

### 1.2 权限矩阵

| 资源/操作 | super_admin | template_admin | approver | user |
|-----------|:-----------:|:--------------:|:--------:|:----:|
| 用户管理 | Y | N | N | N |
| 角色分配 | Y | N | N | N |
| 审计日志查看 | Y | N | N | N |
| 模板创建/编辑 | Y | Y | N | N |
| 模板删除 | Y | Y | N | N |
| 模板查看 | Y | Y | Y | Y |
| 合同审批 | Y | N | Y | N |
| 项目创建 | Y | Y | Y | Y |
| 合同生成 | Y | Y | Y | Y |
| 下载自己的合同 | Y | Y | Y | Y |
| 下载所有合同 | Y | N | Y | N |

### 1.3 存储方式

不新增角色/权限表，直接在 `users` 表添加 `role` 字段：

```sql
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user';
-- 可选值: 'super_admin', 'template_admin', 'approver', 'user'
```

### 1.4 权限校验实现

FastAPI 依赖注入 `require_role()` 校验：

```python
def require_role(*allowed_roles: str):
    async def checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(403, "权限不足")
        return current_user
    return checker
```

路由使用：

```python
@router.delete("/templates/{id}",
    dependencies=[Depends(require_role("super_admin", "template_admin"))])
```

JWT token 中携带角色信息，前端根据角色控制 UI 显示。

## 2. 审计系统

### 2.1 三类审计

**登录审计**
- 记录：用户、时间、IP、User-Agent、登录成功/失败
- 触发点：`/api/v1/auth/login`

**数据变更追踪**
- 记录：操作者、目标表、目标ID、操作类型(INSERT/UPDATE/DELETE)、变更前快照、变更后快照
- 触发点：关键业务操作装饰器

**文件操作审计**
- 记录：操作者、文件路径、操作类型(上传/下载/导出)、关联业务ID
- 触发点：模板上传、合同导出/下载、ZIP下载

### 2.2 混合存储架构

```
请求 → 中间件(基线记录) → 路由 → 装饰器(精确记录) → 业务逻辑
                ↓                              ↓
         audit_logs 表                    audit_logs 表
                ↓                              ↓
         异步写入文件 ←────────────────────────┘
         (logs/audit/YYYY-MM-DD.jsonl)
```

- 数据库：`audit_logs` 表存近 30 天记录，支持查询/筛选/分页
- 文件归档：异步写入 `logs/audit/YYYY-MM-DD.jsonl`，长期保留
- 清理策略：后台定时任务每月清理 30 天前的数据库记录

### 2.3 audit_logs 表结构

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    detail JSONB DEFAULT '{}',
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

`action` 枚举值：`login, logout, create, update, delete, export, download, approve, reject, transfer, upload`

`detail` JSONB 示例：

```json
{
  "before": {"name": "旧模板名", "status": "draft"},
  "after": {"name": "新模板名", "status": "active"}
}
```

### 2.4 审计中间件

- 拦截所有 `/api/v1/*` 请求
- 跳过 GET 请求，仅记录写操作（POST/PUT/DELETE/PATCH）
- 从 JWT 解析 user_id
- 记录：user_id、action（HTTP方法推断）、path、时间、IP

### 2.5 审计装饰器

```python
def audit_action(action: str, resource_type: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await audit_service.log(action, resource_type, ...)
            return result
        return wrapper
    return decorator
```

用于关键业务操作的精确记录，补充中间件的粗粒度基线。

### 2.6 文件归档写入器

- 异步写入 `logs/audit/YYYY-MM-DD.jsonl`
- 每行一条 JSON，append 模式
- 使用 `aiofiles` 避免阻塞

## 3. 后端新增文件

```
backend/app/
├── models/
│   └── audit_log.py              # AuditLog 模型
├── schemas/
│   ├── role.py                   # 角色相关 schema
│   └── audit.py                  # 审计日志 schema
├── api/
│   ├── auth.py                   # 登录/注册/角色分配
│   ├── users.py                  # 用户管理
│   └── audit.py                  # 审计日志查询
├── services/
│   ├── auth_service.py           # 认证+角色校验
│   └── audit_service.py          # 审计写入+查询+归档
├── middleware/
│   └── audit_middleware.py        # 基线审计中间件
└── utils/
    └── audit_file_writer.py      # 文件归档写入器
```

修改文件：
- `models/user.py` — 添加 role 字段
- `dependencies.py` — 添加 require_role()
- `api/router.py` — 注册新路由
- `database.py` — 注册新模型

## 4. 前端实现

### 4.1 新增文件

```
frontend/src/
├── pages/
│   ├── Login/                    # 登录页
│   │   └── index.tsx
│   └── AuditLog/                 # 审计日志页
│       └── index.tsx
├── components/
│   └── RoleGuard.tsx             # 权限守卫组件
├── api/
│   ├── auth.ts                   # 登录/注册API
│   ├── users.ts                  # 用户管理API
│   └── audit.ts                  # 审计日志API
├── stores/
│   └── authStore.ts              # 认证状态
└── hooks/
    └── useRole.ts                # 角色判断hook
```

### 4.2 路由变更

- `/login` — 登录页（新增）
- `/audit-logs` — 审计日志页（新增，仅 super_admin）

### 4.3 RoleGuard 组件

```tsx
<RoleGuard allowedRoles={["super_admin", "template_admin"]}>
  <Button danger onClick={handleDelete}>删除模板</Button>
</RoleGuard>
```

读取 authStore 中的当前用户角色，不在允许角色列表中则不渲染子组件。

### 4.4 菜单权限

| 菜单项 | 可见角色 |
|--------|---------|
| 首页 | 全部 |
| 模板管理 | 全部 |
| 合同生成 | 全部 |
| 审批中心 | super_admin, approver |
| 档案检索 | 全部 |
| 审计日志 | super_admin |
| 用户管理 | super_admin |

### 4.5 审计日志页面

- 筛选：操作类型、资源类型、操作人、时间范围
- 表格：时间、操作人、操作、资源类型、资源ID、详情（展开JSON）
- 分页

### 4.6 登录页

- 用户名/密码表单
- JWT 存 localStorage
- 登录成功跳转首页
- 未登录访问受保护页面自动重定向到登录页

## 5. 新增 API 端点

```
# 认证
POST   /api/v1/auth/login              # 登录
POST   /api/v1/auth/register           # 注册（仅 super_admin）
GET    /api/v1/auth/me                  # 获取当前用户信息

# 用户管理
GET    /api/v1/users                    # 用户列表（super_admin）
PUT    /api/v1/users/{id}/role          # 修改用户角色（super_admin）

# 审计日志
GET    /api/v1/audit-logs               # 审计日志列表（super_admin）
GET    /api/v1/audit-logs/{id}          # 审计日志详情（super_admin）
```

## 6. 权衡与限制

| 决策 | 原因 | 未来扩展 |
|------|------|---------|
| 角色存在 user 表而非独立表 | 4 个固定角色无需动态管理 | 可迁移到 RBAC 多表方案 |
| 中间件跳过 GET 请求 | 减少审计噪音，读操作通常不敏感 | 可配置白名单记录特定 GET |
| 数据库 30 天清理 | 避免表无限增长 | 可配置保留天数 |
| JWT 存 localStorage | MVP 简化 | 生产环境应使用 HttpOnly cookie |
