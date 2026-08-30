# 学习者前端（C 端）

Vue 3 + Vite + TypeScript 单页应用，与 `admin-frontend` 同栈（pnpm / axios / unplugin-auto-import）。

## 开发

```bash
pnpm install
pnpm dev        # http://localhost:3000，/api 与 /ws 由 vite 代理到 localhost:8000
```

## 构建与部署

```bash
pnpm build      # vue-tsc 类型检查 + vite 构建 → dist/
```

- 所有请求走相对路径（`/api`、`/ws`）：开发由 `vite.config.ts` 代理，生产由 `gateway/nginx.conf` 同源转发，无需配置后端地址。
- Docker：仓库根目录 `docker compose --env-file .env.docker up -d --build`，本服务由网关在 `/` 托管，容器内 nginx 以 `try_files` 提供 SPA history 回退。
