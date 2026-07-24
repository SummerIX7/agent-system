# 后端镜像：FastAPI + uvicorn（Python 3.11）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 运行期系统依赖：curl 供健康检查使用
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖以利用构建缓存（torch / sentence-transformers 较大，首次构建较慢）
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 拷贝后端代码（.dockerignore 已排除 chroma_db / __pycache__ / .env 等）
COPY . .

# 入口脚本：等待 MySQL → alembic 迁移 →（可选）建索引 → 启动服务
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
