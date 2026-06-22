# Docker 本地部署设计

## 目标

将合同模板管理系统完整部署到本地 Docker Desktop，用户只需 `docker-compose up` 即可通过 `http://localhost` 访问全部功能。

## 架构

4 个容器通过 Docker 网络互联：

```
浏览器 → frontend (Nginx:80)
              ├─ / → React SPA
              └─ /api → proxy → backend (FastAPI:8000)
                                  ├─ PostgreSQL:5432
                                  └─ Redis:6379
```

> **注意**：当前项目 MVP 阶段使用 `asyncio.create_task` 内存任务管理器（`app/services/task_manager.py`），不使用 Celery worker，因此无需 celery 容器。

## 服务定义

### db (PostgreSQL 15)

- 镜像：`postgres:15-alpine`
- 端口：仅内部网络 5432
- Volume：`postgres_data` 持久化
- 环境变量：`POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=contract`
- Healthcheck：`pg_isready -U postgres`

### redis (Redis 7)

- 镜像：`redis:7-alpine`
- 端口：仅内部网络 6379
- Volume：`redis_data` 持久化
- Healthcheck：`redis-cli ping`

### backend (FastAPI)

- 自建多阶段镜像，基于 `python:3.11-slim`
- 代码来源：Dockerfile 内 `git clone https://github.com/mjzboe/contract-template.git`
- 端口：仅内部网络 8000
- Volume：`uploads` 挂载到 `/app/uploads`
- depends_on：db (healthy), redis (healthy)
- 启动脚本：`alembic upgrade head` → `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- 环境变量覆盖：
  - `DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/contract`
  - `REDIS_URL=redis://redis:6379/0`
  - `CELERY_BROKER_URL=redis://redis:6379/0`
  - `LIBREOFFICE_PATH=/usr/bin/libreoffice`
  - `UPLOAD_DIR=/app/uploads`
  - `CORS_ORIGINS=http://localhost`

### frontend (Nginx)

- 自建多阶段镜像
- Stage 1：`node:20-alpine`，git clone → npm install → npm run build
- Stage 2：`nginx:alpine`，拷贝 dist + 自定义 nginx.conf
- 端口：`80:80`（唯一对外暴露端口）
- depends_on：backend
- Nginx 配置：
  - `/api/` → `proxy_pass http://backend:8000`
  - `/` → SPA fallback (`try_files $uri $uri/ /index.html`)
  - `client_max_body_size 50m`（支持大文件上传）

## Dockerfile 细节

### backend/Dockerfile

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

### backend/entrypoint.sh

```bash
#!/bin/bash
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### frontend/Dockerfile

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

### frontend/nginx.conf

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

## docker-compose.yml

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

## 目录结构

构建文件独立于源码，放在项目根目录的 `docker/` 下：

```
docker/
├── backend/
│   ├── Dockerfile
│   └── entrypoint.sh
├── frontend/
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml    # 放在项目根目录，方便 docker-compose up
```

compose 中 build context 指向 `./docker/backend` 和 `./docker/frontend`，这些目录只含构建文件，不含源码。源码在 Dockerfile 内 git clone 获取。

## 需要创建的文件

| 文件 | 用途 |
|------|------|
| `docker/backend/Dockerfile` | 后端多阶段构建 |
| `docker/backend/entrypoint.sh` | 后端启动脚本（迁移+启动） |
| `docker/frontend/Dockerfile` | 前端多阶段构建 |
| `docker/frontend/nginx.conf` | Nginx 反向代理 + SPA 配置 |
| `docker-compose.yml` | 完整编排（项目根目录，替代 docker-compose.dev.yml） |

## 需要修改的文件

| 文件 | 修改内容 |
|------|----------|
| `backend/app/config.py` | `LIBREOFFICE_PATH` 默认值改为 `/usr/bin/libreoffice`（Linux 路径），保留 Windows 路径作为环境变量覆盖 |
| `backend/app/tasks/celery_app.py` | 确认 Celery app import 路径正确 |

## 数据持久化

- `postgres_data`：数据库数据
- `redis_data`：Redis 数据
- `uploads`：模板文件、合同文件、Excel 文件、ZIP 包

三个 Volume 均为 Docker named volume，容器重启不丢失。

## 使用方式

```bash
# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止
docker-compose down

# 停止并清除数据
docker-compose down -v

# 重新构建（代码更新后）
docker-compose up -d --build
```

## 已知限制

- 首次构建需联网（git clone + pip install + apt-get），耗时约 5-10 分钟
- 后端镜像含 LibreOffice，体积约 800MB
- 代码更新需重新构建镜像（`docker-compose up -d --build`）
- 未配置 HTTPS（本地部署不需要）
