# Stage 1: Builder
FROM python:3.11-slim AS builder

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http:|https:|g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    git libpq-dev gcc g++ && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/mjzboe/contract-template.git /repo

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r /repo/backend/requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http:|https:|g' /etc/apt/sources.list.d/debian.sources

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
