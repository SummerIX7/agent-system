"""混合检索单元测试（BM25 + 向量 RRF 融合）——不依赖 Chroma 与嵌入 API。

覆盖主检索路径 hybrid_search 的三个关键行为：
1. BM25 不可用时回落纯向量
2. 双路命中的文档经 RRF 融合后排名提升
3. standards/规程 类文档获得加权提升
"""
import pytest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.knowledge.retriever import KnowledgeRetriever


def make_doc(content: str, source: str = "theory/t1.md", source_type: str = "theory") -> Document:
    return Document(page_content=content, metadata={"source": source, "source_type": source_type})


@pytest.fixture
def retriever():
    """构造不触碰真实 Chroma/嵌入的 KnowledgeRetriever"""
    with patch("app.knowledge.retriever.get_embeddings", return_value=None):
        r = KnowledgeRetriever(persist_dir="./_unused_chroma_for_tests")
    r.vectorstore = MagicMock()
    return r


def _install_bm25(retriever, docs: list, scores: list):
    """以可控分数安装伪 BM25（分数与 docs 下标一一对应，rank0 = 分数最高）"""
    retriever._bm25 = MagicMock()
    retriever._bm25.get_scores.return_value = scores
    retriever._bm25_docs = docs
    retriever._jieba = MagicMock()
    retriever._jieba.cut.return_value = ["tok"]


def test_fallback_to_pure_vector_when_bm25_unavailable(retriever):
    """BM25 不可用 → 回落纯向量 top-k"""
    docs = [make_doc(f"仅向量文档{i}") for i in range(8)]
    retriever.vectorstore.similarity_search.return_value = docs
    with patch.object(KnowledgeRetriever, "_ensure_bm25", return_value=False):
        result = retriever.hybrid_search("查询", k=5)
    assert result == docs[:5]


def test_rrf_promotes_docs_hit_by_both_channels(retriever):
    """向量与 BM25 双路命中的文档，RRF 累加后应排在单路命中文档之前"""
    both = make_doc("双路命中文档：G00 快速定位", source="theory/both.md")
    vector_only = [make_doc(f"仅向量{i}", source=f"theory/v{i}.md") for i in range(3)]
    bm25_only = [make_doc(f"仅BM25{i}", source=f"theory/b{i}.md") for i in range(3)]

    retriever.vectorstore.similarity_search.return_value = [both] + vector_only
    _install_bm25(retriever, [both] + bm25_only, scores=[1.0, 0.5, 0.4, 0.3])

    with patch.object(KnowledgeRetriever, "_ensure_bm25", return_value=True):
        result = retriever.hybrid_search("G00 快速定位", k=3)

    assert len(result) == 3
    assert result[0] is both


def test_standard_type_gets_weight_boost(retriever):
    """融合分数相同时，standards 类文档因加权排在 theory 之前"""
    theory_doc = make_doc("理论内容", source="theory/t1.md", source_type="theory")
    standard_doc = make_doc("安全规程内容", source="standards/s1.md", source_type="standards")

    # 向量序: theory 先；BM25 序: standards 先 → 两文档融合分恰好相等
    retriever.vectorstore.similarity_search.return_value = [theory_doc, standard_doc]
    _install_bm25(retriever, [standard_doc, theory_doc], scores=[0.9, 0.8])

    with patch.object(KnowledgeRetriever, "_ensure_bm25", return_value=True):
        result = retriever.hybrid_search("安全规程", k=2)
    assert result[0] is standard_doc

    # 对照：去掉加权后，平分按插入序应 theory 在前 → 证明排名变化来自加权
    with patch.object(KnowledgeRetriever, "_STANDARD_BOOST", 1.0), \
         patch.object(KnowledgeRetriever, "_ensure_bm25", return_value=True):
        result_plain = retriever.hybrid_search("安全规程", k=2)
    assert result_plain[0] is theory_doc


def test_is_standard_classification(retriever):
    """source_type 白名单判定：standard/standards/规程/标准 命中，其余不命中"""
    assert retriever._is_standard(make_doc("x", source_type="standards")) is True
    assert retriever._is_standard(make_doc("x", source_type="标准")) is True
    assert retriever._is_standard(make_doc("x", source_type="规程")) is True
    assert retriever._is_standard(make_doc("x", source_type="theory")) is False
    assert retriever._is_standard(make_doc("x", source_type="practice")) is False
