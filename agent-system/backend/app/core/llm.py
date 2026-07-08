from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def get_llm(provider: str | None = None, temperature: float = 0.7) -> ChatOpenAI:
    """
    获取 LLM 实例。

    通过 OpenAI 兼容接口调用任意 LLM 服务（DeepSeek、Kimi、GLM、Qwen、MiniMax 等）。
    具体服务地址和模型名由 .env 中的 LLM_BASE_URL 和 LLM_MODEL 决定。

    Args:
        provider: 保留参数，已不再影响 base_url 选择，仅用于保持旧调用兼容
        temperature: 温度参数，控制随机性

    Returns:
        ChatOpenAI 实例，MOCK_MODE=true 时返回 MockLLM
    """
    settings = get_settings()

    # Mock 模式：返回本地模拟 LLM，不调用外部 API
    if settings.MOCK_MODE:
        from app.mock.llm import MockLLM
        return MockLLM()

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=temperature,
    )
