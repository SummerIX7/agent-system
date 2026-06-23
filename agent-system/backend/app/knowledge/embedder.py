from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings


@lru_cache()
def get_embeddings() -> OpenAIEmbeddings:
    """获取嵌入模型实例（通过 OpenAI 兼容 API 调用，无需本地下载）"""
    settings = get_settings()

    if not settings.EMBEDDING_API_KEY:
        raise ValueError(
            "EMBEDDING_API_KEY 未配置。请在 .env 中设置嵌入 API Key。\n"
            "推荐使用阿里云 DashScope：https://dashscope.console.aliyun.com/\n"
            "或使用任何 OpenAI 兼容的嵌入服务。"
        )

    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
        chunk_size=10,  # DashScope 对 batch 大小有限制
        check_embedding_ctx_length=False,  # 禁用自动分块，避免格式问题
    )
