"""Mock 嵌入模型：返回零向量，不调用外部 API。"""


class MockEmbeddings:
    """替代 OpenAIEmbeddings，返回 768 维零向量。不发出网络请求。"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档（用于索引构建）"""
        return [[0.0] * 768 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        """嵌入单个查询（用于相似度搜索）"""
        return [0.0] * 768
