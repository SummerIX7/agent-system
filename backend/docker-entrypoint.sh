#!/usr/bin/env bash
set -e

echo "[entrypoint] 等待 PostgreSQL (${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}) ..."
python - <<'PY'
import asyncio, os
import asyncpg

host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
user = os.getenv("POSTGRES_USER", "postgres")
password = os.getenv("POSTGRES_PASSWORD", "")
db = os.getenv("POSTGRES_DATABASE", "agent_system")

async def wait_ready():
    for i in range(60):
        try:
            conn = await asyncpg.connect(host=host, port=port, user=user,
                                         password=password, database=db, timeout=3)
            await conn.close()
            print("[entrypoint] PostgreSQL 就绪")
            return
        except Exception as e:  # noqa: BLE001
            print(f"[entrypoint] PostgreSQL 未就绪({i+1}/60): {e}")
            await asyncio.sleep(2)
    raise SystemExit("[entrypoint] 等待 PostgreSQL 超时")

asyncio.run(wait_ready())
PY

# 建表由应用启动生命周期（main.py lifespan: Base.metadata.create_all）负责，
# 与当前整型模型保持一致；不使用 alembic 迁移（历史迁移与现模型已脱节）。

echo "[entrypoint] 启动服务: $*"
exec "$@"