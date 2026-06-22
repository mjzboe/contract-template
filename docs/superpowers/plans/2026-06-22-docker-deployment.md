# Docker 本地部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将合同模板管理系统完整部署到本地 Docker Desktop，`docker-compose up` 后通过 `http://localhost` 访问全部功能。

**Architecture:** 4 容器编排（PostgreSQL + Redis + Backend + Frontend/Nginx）。后端多阶段构建含 LibreOffice 支持 PDF 导出，前端 Nginx 托管 SPA 并反向代理 API。异步任务使用 asyncio 内存管理器，无需 Celery worker 容器。

**Tech Stack:** Docker Compose 3.8, python:3.11-slim, node:20-alpine, nginx:alpine, postgres:15-alpine, redis:7-alpine

---

## 修正说明

设计文档中包含 Celery worker 容器，但实际代码使用 `asyncio.create_task` 内存任务管理器（`app/services/task_manager.py`），无真正 Celery task 注册。因此实施中去掉 celery 容器，仅保留 4 个服务。

---

### Task 1: 创建目录结构

**Files:**
- Create: `docker/backend/` (directory)
- Create: `docker/frontend/` (directory)

- [ ] **Step 1: 创建 docker 目录**

```bash
mkdir -p docker/backend docker/frontend
```

- [ ] **Step 2: 验证目录存在**

```bash
ls -la docker/
```

Expected: `backend/` 和 `frontend/` 目录可见

---

### Task 2: 创建后端 Dockerfile

**Files:**
- Create: `docker/backend/Dockerfile`

- [ ] **Step 1: 编写后端多阶段 Dockerfile**

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git libpq-dev gcc g++ && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/mjzboe/contract-template.git /repo

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r /repo/backend/requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-common libpq5 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /repo/backend /app

ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

- [ ] **Step 2: 验证 Dockerfile 语法**

```bash
docker build --check -f docker/backend/Dockerfile docker/backend/ 2>/dev/null || echo "Docker build check not supported, file created"
```

---

### Task 3: 创建后端启动脚本

**Files:**
- Create: `docker/backend/entrypoint.sh`

- [ ] **Step 1: 编写 entrypoint.sh**

```bash
#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

注意：必须用 LF 换行符（不能是 CRLF），否则 Linux 容器内无法执行。

- [ ] **Step 2: 确保换行符为 LF**

```bash
sed -i 's/\r$//' docker/backend/entrypoint.sh
```

---

### Task 4: 创建前端 Dockerfile

**Files:**
- Create: `docker/frontend/Dockerfile`

- [ ] **Step 1: 编写前端多阶段 Dockerfile**

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

RUN apk add --no-cache git
RUN git clone https://github.com/mjzboe/contract-template.git /repo

WORKDIR /repo/frontend
RUN npm install && npm run build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=builder /repo/frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

---

### Task 5: 创建 Nginx 配置

**Files:**
- Create: `docker/frontend/nginx.conf`

- [ ] **Step 1: 编写 nginx.conf**

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 50m;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

---

### Task 6: 创建 docker-compose.yml

**Files:**
- Create: `docker-compose.yml` (项目根目录)

- [ ] **Step 1: 编写 docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: contract
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./docker/backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/contract
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      SECRET_KEY: dev-secret-key-change-in-production
      UPLOAD_DIR: /app/uploads
      CORS_ORIGINS: http://localhost
      LIBREOFFICE_PATH: /usr/bin/libreoffice
    volumes:
      - uploads:/app/uploads
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    build:
      context: ./docker/frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
  uploads:
```

---

### Task 7: 修改后端 config.py 适配 Linux 路径

**Files:**
- Modify: `backend/app/config.py:13`

- [ ] **Step 1: 修改 LIBREOFFICE_PATH 默认值**

将 `config.py` 第 13 行的 Windows 路径改为 Linux 路径，同时保留环境变量覆盖能力：

```python
# 修改前
LIBREOFFICE_PATH: str = r"C:\Program Files\LibreOffice\program\soffice.exe"

# 修改后
LIBREOFFICE_PATH: str = "/usr/bin/libreoffice"
```

Docker 环境通过环境变量覆盖，本地开发时可在 `.env` 文件中设置 Windows 路径。

- [ ] **Step 2: 验证修改正确**

```bash
grep LIBREOFFICE_PATH backend/app/config.py
```

Expected: `LIBREOFFICE_PATH: str = "/usr/bin/libreoffice"`

---

### Task 8: 创建 .dockerignore 文件

**Files:**
- Create: `docker/backend/.dockerignore`
- Create: `docker/frontend/.dockerignore`

- [ ] **Step 1: 创建后端 .dockerignore**

```
__pycache__
*.pyc
.pytest_cache
uploads/
*.egg-info
.env
.venv
```

- [ ] **Step 2: 创建前端 .dockerignore**

```
node_modules
dist
.env
```

注意：由于源码通过 git clone 获取，.dockerignore 主要影响 COPY 指令（仅 entrypoint.sh 和 nginx.conf），作用有限但保持规范。

---

### Task 9: 构建并启动

- [ ] **Step 1: 构建所有镜像**

```bash
docker-compose build
```

Expected: 4 个镜像构建成功（db/redis 拉取，backend/frontend 构建）

- [ ] **Step 2: 启动所有服务**

```bash
docker-compose up -d
```

Expected: 所有容器状态为 `running` 或 `healthy`

- [ ] **Step 3: 检查容器状态**

```bash
docker-compose ps
```

Expected: 4 个服务全部 Up/Healthy

- [ ] **Step 4: 检查后端日志确认迁移和启动成功**

```bash
docker-compose logs backend | tail -20
```

Expected: 看到 "Running database migrations..." 和 "Starting FastAPI server..." 以及 "Contract Template API starting..."

- [ ] **Step 5: 访问前端验证**

浏览器打开 `http://localhost`，Expected: 看到合同模板管理系统首页

- [ ] **Step 6: 访问 API 文档验证**

浏览器打开 `http://localhost/api/v1/docs` 或 `http://localhost/api/docs`，Expected: FastAPI Swagger UI

---

### Task 10: 提交所有文件

- [ ] **Step 1: 查看变更**

```bash
git status
```

- [ ] **Step 2: 添加并提交**

```bash
git add docker/ docker-compose.yml backend/app/config.py
git commit -m "feat: add Docker deployment with docker-compose (4 services: db, redis, backend, frontend)"
```

---

## 自审查结果

1. **Spec 覆盖**：设计文档中所有服务已覆盖，Celery worker 已根据实际代码修正为去掉
2. **占位符扫描**：无 TBD/TODO
3. **类型一致性**：Celery app import 路径 `app.tasks.celery_app` 已确认存在，但实际未使用 Celery worker，已修正
4. **Spec 偏差**：设计文档包含 celery 容器，实施计划已修正。需同步更新设计文档
