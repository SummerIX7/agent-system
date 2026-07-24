# 前端镜像（Nuxt 3 SSR）：多阶段构建 → Node 运行 .output
FROM node:20-alpine AS build
WORKDIR /app
RUN corepack enable

# 依赖层缓存
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

# 源码 + 构建
COPY . .
RUN pnpm build

# ── 运行阶段 ──
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

COPY --from=build /app/.output ./.output

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
