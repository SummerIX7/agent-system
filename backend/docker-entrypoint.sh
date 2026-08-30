#!/usr/bin/env bash
set -e

echo "[entrypoint] 等待 MySQL (${MYSQL_HOST:-mysql}:${MYSQL_PORT:-3306}) ..."
python - <<'PY'
import os, time
import pymysql

host = os.getenv("MYSQL_HOST", "mysql")
port = int(os.getenv("MYSQL_PORT", "3306"))
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "")
db = os.getenv("MYSQL_DATABASE", "agent_system")

for i in range(60):
    try:
        conn = pymysql.connect(host=host, port=port, user=user,
                               password=password, database=db, connect_timeout=3)
        conn.close()
        print("[entrypoint] MySQL 就绪")
        break
    except Exception as e:  # noqa: BLE001
        print(f"[entrypoint] MySQL 未就绪({i+1}/60): {e}")
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] 等待 MySQL 超时")
PY

# 建表由应用启动生命周期（main.py lifespan: Base.metadata.create_all）负责，
# 与当前整型模型保持一致；不使用 alembic 迁移（历史迁移与现模型已脱节）。

echo "[entrypoint] 启动服务: $*"
exec "$@"
