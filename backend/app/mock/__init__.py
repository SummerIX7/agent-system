"""Mock 模式包：MOCK_MODE=true 时替换所有外部 API 调用为本地模拟数据。"""

from app.mock.llm import MockLLM, _mock_label
from app.mock.embeddings import MockEmbeddings
from app.mock.knowledge import MockRetriever

__all__ = ["MockLLM", "MockEmbeddings", "MockRetriever", "_mock_label"]
