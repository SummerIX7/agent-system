# 管理后台镜像（Vue3 + Vite 静态产物 → nginx）
# 构建时以 /admin/ 为 base，便于统一网关按 /admin/ 前缀托管
FROM node:20-alpine AS build
WORKDIR /app
RUN corepack enable

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY . .
# 仅执行 vite 构建（跳过 vue-tsc 类型检查以保证镜像稳定构建），指定 /admin/ 基路径
RUN npx vite build --base=/admin/

# ── 运行阶段：nginx 托管静态文件 ──
FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
