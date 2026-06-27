from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "agent_system"

    # JWT
    JWT_SECRET_KEY: str = "agent-system-secret-key-change-in-production"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # LLM
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    # 嵌入模型 API（OpenAI 兼容接口）
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_API_KEY: str = ""  # 阿里云 DashScope API Key
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # 知识库开关
    ENABLE_KNOWLEDGE_BASE: bool = True

    # 知识库目录（多个目录用逗号分隔，相对于 backend 目录）
    KNOWLEDGE_BASE_DIRS: str = "../knowledge-base/demo_domain/python_data_analysis,../knowledge-base/cnc_domain"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步 URL，供 Alembic 迁移使用"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
