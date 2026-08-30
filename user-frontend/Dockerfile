# 学习者前端镜像（Vue3 + Vite 静态产物 → nginx，SPA history 路由回退）
FROM node:20-alpine AS build
WORKDIR /app
# 固定 pnpm 到 v10（与 admin-frontend 一致；兼容 Node 20，默认最新版需 Node 22+）
RUN corepack enable && corepack prepare pnpm@10.15.0 --activate

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY . .
# 完整构建（含 vue-tsc 类型检查）；本镜像以 / 为 base，由网关直接托管根路径
RUN pnpm build

# ── 运行阶段：nginx 托管静态文件 ──
FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
