# Stage 1: Build
FROM node:20-alpine AS builder

RUN apk add --no-cache git
RUN git clone https://github.com/mjzboe/contract-template.git /repo

WORKDIR /repo/frontend
RUN npm install --registry=https://registry.npmmirror.com && npm run build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=builder /repo/frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
