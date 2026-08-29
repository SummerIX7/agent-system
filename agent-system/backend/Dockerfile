# 后端镜像：FastAPI + uvicorn（Python 3.11，uv 管理依赖）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# uv（版本与本地 uv.lock 生成环境一致）+ 运行期系统依赖：curl 供健康检查使用
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖清单并按锁文件安装（利用构建缓存；--frozen 保证不偏离 uv.lock）
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# 拷贝后端代码（.dockerignore 已排除 chroma_db / .venv / tests / .env 等）
COPY . .

# uv sync 创建的虚拟环境直接放进 PATH（entrypoint 与 CMD 均使用它）
ENV PATH="/app/.venv/bin:$PATH"

# 入口脚本：等待 MySQL → 启动服务（建表由 main.py lifespan 的 create_all 负责）
RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
