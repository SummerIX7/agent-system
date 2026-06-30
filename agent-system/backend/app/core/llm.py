from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def get_llm(provider: str | None = None, temperature: float = 0.7) -> ChatOpenAI:
    """
    获取 LLM 实例。

    Args:
        provider: 提供商名称，None 时使用配置文件默认值
        temperature: 温度参数，控制随机性

    Returns:
        ChatOpenAI 实例（兼容 DeepSeek/Qwen API），MOCK_MODE=true 时返回 MockLLM
    """
    settings = get_settings()

    # Mock 模式：返回本地模拟 LLM，不调用外部 API
    if settings.MOCK_MODE:
        from app.mock.llm import MockLLM
        return MockLLM()
    provider = provider or settings.LLM_PROVIDER

    if provider == "deepseek":
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            temperature=temperature,
        )
    elif provider == "qwen":
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=temperature,
        )
    elif provider == "minimax":
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url="https://api.minimaxi.com/v1",
            temperature=temperature,
        )
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
