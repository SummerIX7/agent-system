from pathlib import Path

from langchain_community.vectorstores import Chroma

from app.core.config import get_settings
from app.knowledge.embedder import get_embeddings
from app.knowledge.loader import load_documents, split_documents


class KnowledgeRetriever:
    """知识库检索器"""

    def __init__(self, persist_dir: str | None = None):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.embeddings = get_embeddings()
        self.vectorstore: Chroma | None = None

    def build_index(self, doc_dir: str) -> int:
        """从文档目录构建向量索引"""
        documents = load_documents(doc_dir)
        chunks = split_documents(documents)

        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_dir,
        )
        print(f"索引构建完成，共 {len(chunks)} 个知识块")
        return len(chunks)

    def load_index(self) -> None:
        """从磁盘加载已有索引"""
        if Path(self.persist_dir).exists():
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
            )
            print(f"已加载索引: {self.persist_dir}")
        else:
            raise FileNotFoundError(f"索引目录不存在: {self.persist_dir}")

    def search(self, query: str, k: int = 5) -> list:
        """相似度搜索"""
        if self.vectorstore is None:
            try:
                self.load_index()
            except FileNotFoundError:
                raise RuntimeError("知识库索引未构建，请先调用 build_index()")

        results = self.vectorstore.similarity_search(query, k=k)
        return results

    def search_with_score(self, query: str, k: int = 5) -> list:
        """带分数的相似度搜索"""
        if self.vectorstore is None:
            try:
                self.load_index()
            except FileNotFoundError:
                raise RuntimeError("知识库索引未构建，请先调用 build_index()")

        results = self.vectorstore.similarity_search_with_score(query, k=k)
        return results


# 全局单例
_retriever: KnowledgeRetriever | None = None


def get_retriever() -> KnowledgeRetriever:
    """获取知识库检索器单例"""
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever()
    return _retriever
