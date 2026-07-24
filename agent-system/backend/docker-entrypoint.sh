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

echo "[entrypoint] 执行数据库迁移 alembic upgrade head ..."
alembic upgrade head

# 可选：构建知识库索引 + 创建管理员（真实模式且需要初始化时设 RUN_SETUP=true）
if [ "${RUN_SETUP}" = "true" ]; then
    echo "[entrypoint] RUN_SETUP=true，执行 setup.py（建管理员 + 建索引）..."
    python setup.py || echo "[entrypoint] setup.py 执行失败（忽略，继续启动）"
fi

echo "[entrypoint] 启动服务: $*"
exec "$@"
