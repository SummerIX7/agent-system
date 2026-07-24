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
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50

    # LLM（OpenAI 兼容接口，支持 DeepSeek / Kimi / GLM / Qwen / MiniMax 等任意平台）
    LLM_PROVIDER: str = "deepseek"  # 仅用于日志展示，不再决定 base_url
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    # 校验 LLM（跨模型谬误核查用；留空则回落主 LLM）
    # 建议配置为与生成模型不同厂商/模型，降低"自评偏差"
    VERIFIER_LLM_API_KEY: str = ""
    VERIFIER_LLM_BASE_URL: str = ""
    VERIFIER_LLM_MODEL: str = ""

    # Agent 工具调用（tool-calling）开关
    # 默认关闭：Generation/Review 走现有纯 prompt 流程，行为与当前一致。
    # 开启后：Generation 可用 retrieve_knowledge 按需补充检索，Review 可用 fact_check_lookup 核查断言。
    # MOCK_MODE=true 时工具路径自动回落纯 prompt（MockLLM 不支持 tool-calling）。
    USE_AGENT_TOOLS: bool = False
    AGENT_TOOL_MAX_ROUNDS: int = 3

    # 嵌入模型 API（OpenAI 兼容接口）
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_API_KEY: str = ""  # 阿里云 DashScope API Key
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # 知识库开关
    ENABLE_KNOWLEDGE_BASE: bool = True

    # 知识库目录（多个目录用逗号分隔，相对于 backend 目录）
    KNOWLEDGE_BASE_DIRS: str = "../knowledge-base/cnc_domain"

    # Mock 模式（MOCK_MODE=true 时所有 LLM/嵌入调用返回本地模拟数据，不访问外部 API）
    MOCK_MODE: bool = False

    # 测试数据库 URL（非空时覆盖 DATABASE_URL property，用于 e2e 测试的 SQLite 内存库）
    TEST_DATABASE_URL: str = ""
    TEST_DATABASE_URL_SYNC: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    @property
    def DATABASE_URL(self) -> str:
        if self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步 URL，供 Alembic 迁移使用"""
        if self.TEST_DATABASE_URL_SYNC:
            return self.TEST_DATABASE_URL_SYNC
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
