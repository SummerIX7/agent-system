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


def get_verifier_llm(temperature: float = 0.0) -> ChatOpenAI:
    """
    获取用于跨模型谬误核查的校验 LLM。

    若 VERIFIER_LLM_* 三项均配置，则返回独立的（通常与生成模型不同厂商/模型的）
    ChatOpenAI，用不同模型做事实核查以降低"自评偏差"；否则回落主 LLM。
    MOCK_MODE=true 时返回 MockLLM。
    """
    settings = get_settings()

    if settings.MOCK_MODE:
        from app.mock.llm import MockLLM
        return MockLLM()

    if settings.VERIFIER_LLM_API_KEY and settings.VERIFIER_LLM_BASE_URL and settings.VERIFIER_LLM_MODEL:
        return ChatOpenAI(
            model=settings.VERIFIER_LLM_MODEL,
            api_key=settings.VERIFIER_LLM_API_KEY,
            base_url=settings.VERIFIER_LLM_BASE_URL,
            temperature=temperature,
        )

    # 未配置独立校验模型：回落主 LLM
    return get_llm(temperature=temperature)
