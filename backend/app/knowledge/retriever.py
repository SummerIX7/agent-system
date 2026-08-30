import json
from pathlib import Path

from langchain_community.vectorstores import Chroma

from app.core.config import get_settings
from app.knowledge.embedder import get_embeddings
from app.knowledge.loader import (
    file_content_hash,
    load_single_document,
    split_documents,
)

_MANIFEST_NAME = ".index_manifest.json"


class KnowledgeRetriever:
    """知识库检索器（支持多目录、增量索引）"""

    def __init__(self, persist_dir: str | None = None):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.embeddings = get_embeddings()
        self.vectorstore: Chroma | None = None

    # ── manifest 读写：记录 文件 → {hash, chunk_ids} ──
    def _manifest_path(self) -> Path:
        return Path(self.persist_dir) / _MANIFEST_NAME

    def _load_manifest(self) -> dict:
        p = self._manifest_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_manifest(self, manifest: dict) -> None:
        p = self._manifest_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_vectorstore(self) -> Chroma:
        """打开（或新建）持久化 Chroma collection"""
        if self.vectorstore is None:
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
            )
        return self.vectorstore

    @staticmethod
    def _chunk_ids(rel_key: str, count: int) -> list[str]:
        """为单个文件的 chunks 生成稳定 id：{相对路径}::{序号}"""
        return [f"{rel_key}::{i}" for i in range(count)]

    def _index_file(self, vs: Chroma, file_path: Path, rel_key: str) -> list[str]:
        """加载、切分并写入单个文件的 chunks，返回其 chunk_ids"""
        doc = load_single_document(file_path)
        chunks = split_documents([doc])
        if not chunks:
            return []
        ids = self._chunk_ids(rel_key, len(chunks))
        vs.add_documents(chunks, ids=ids)
        return ids

    def build_index(self, doc_dir: str) -> int:
        """从单个文档目录增量构建索引（便捷入口）"""
        stats = self.build_index_from_dirs([doc_dir])
        return stats["total_chunks"]

    def build_index_from_dirs(self, doc_dirs: list[str], force: bool = False) -> dict:
        """增量同步多个文档目录的向量索引。

        force=True 时清空 collection 与 manifest 后全量重建。
        返回统计：{total_chunks, added, updated, skipped, deleted}。
        """
        vs = self._ensure_vectorstore()
        manifest = {} if force else self._load_manifest()

        if force:
            # 清空旧数据：删除已知的所有 chunk（manifest 记录）以避免残留
            old_manifest = self._load_manifest()
            old_ids = [cid for e in old_manifest.values() for cid in e.get("chunk_ids", [])]
            if old_ids:
                try:
                    vs.delete(ids=old_ids)
                except Exception as e:  # noqa: BLE001
                    print(f"[警告] 清空旧索引失败: {e}")

        # 收集磁盘上现存的所有 md 文件（rel_key 用绝对路径 posix 形式，保证唯一稳定）
        present: dict[str, Path] = {}
        for doc_dir in doc_dirs:
            doc_path = Path(doc_dir)
            if not doc_path.exists():
                print(f"[警告] 知识库目录不存在: {doc_dir}")
                continue
            for md in doc_path.rglob("*.md"):
                present[md.resolve().as_posix()] = md

        added = updated = skipped = deleted = 0
        new_manifest: dict = {}

        for rel_key, md_path in present.items():
            content_hash = file_content_hash(md_path)
            prev = manifest.get(rel_key)
            if prev and prev.get("hash") == content_hash:
                # 未变化：跳过 embedding，沿用旧记录
                new_manifest[rel_key] = prev
                skipped += 1
                continue
            # 新增或变更：先删旧 chunk 再写新 chunk
            if prev and prev.get("chunk_ids"):
                try:
                    vs.delete(ids=prev["chunk_ids"])
                except Exception as e:  # noqa: BLE001
                    print(f"[警告] 删除旧 chunk 失败 ({rel_key}): {e}")
            ids = self._index_file(vs, md_path, rel_key)
            new_manifest[rel_key] = {"hash": content_hash, "chunk_ids": ids}
            if prev:
                updated += 1
            else:
                added += 1

        # 处理磁盘已删除、manifest 仍存在的文件
        for rel_key, entry in manifest.items():
            if rel_key not in present:
                if entry.get("chunk_ids"):
                    try:
                        vs.delete(ids=entry["chunk_ids"])
                    except Exception as e:  # noqa: BLE001
                        print(f"[警告] 删除已移除文件 chunk 失败 ({rel_key}): {e}")
                deleted += 1

        self._save_manifest(new_manifest)
        total_chunks = sum(len(e.get("chunk_ids", [])) for e in new_manifest.values())
        print(
            f"索引同步完成：新增 {added} / 更新 {updated} / 跳过 {skipped} / 删除 {deleted}"
            f"，共 {total_chunks} 个知识块"
        )
        return {
            "total_chunks": total_chunks,
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "deleted": deleted,
        }

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

    # ── 混合检索：BM25 关键词召回 + 向量召回，RRF 融合，standards 加权 ──
    _STANDARD_TYPES = {"standard", "standards", "规程", "标准"}
    _RRF_K = 60
    _STANDARD_BOOST = 1.2

    def _ensure_bm25(self) -> bool:
        """惰性构建 BM25 语料（从 Chroma 拉取全量 chunk）。不可用时返回 False。"""
        if getattr(self, "_bm25", None) is not None:
            return True
        if getattr(self, "_bm25_unavailable", False):
            return False
        try:
            import jieba
            from rank_bm25 import BM25Okapi
            from langchain_core.documents import Document

            got = self.vectorstore.get(include=["documents", "metadatas"])
            texts = got.get("documents") or []
            metas = got.get("metadatas") or []
            if not texts:
                self._bm25_unavailable = True
                return False
            self._bm25_docs = [
                Document(page_content=t, metadata=(metas[i] if i < len(metas) else {}))
                for i, t in enumerate(texts)
            ]
            tokenized = [list(jieba.cut(t)) for t in texts]
            self._bm25 = BM25Okapi(tokenized)
            self._jieba = jieba
            return True
        except Exception as e:  # noqa: BLE001 依赖缺失或加载失败 → 回落纯向量
            print(f"[提示] BM25 不可用，回落纯向量检索: {e}")
            self._bm25_unavailable = True
            return False

    @staticmethod
    def _doc_key(doc) -> str:
        src = (doc.metadata or {}).get("source", "")
        return f"{src}::{doc.page_content[:120]}"

    def _is_standard(self, doc) -> bool:
        st = str((doc.metadata or {}).get("source_type", "")).lower()
        return st in self._STANDARD_TYPES

    def hybrid_search(self, query: str, k: int = 5, vector_k: int = 20, bm25_k: int = 20) -> list:
        """向量 + BM25 的 RRF 融合检索；BM25 不可用时回落纯向量。"""
        vector_docs = self.vectorstore.similarity_search(query, k=vector_k)

        if not self._ensure_bm25():
            return vector_docs[:k]

        # BM25 召回
        tokens = list(self._jieba.cut(query))
        scores = self._bm25.get_scores(tokens)
        ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:bm25_k]
        bm25_docs = [self._bm25_docs[i] for i in ranked_idx]

        # RRF 融合
        fused: dict[str, float] = {}
        doc_by_key: dict[str, object] = {}
        for rank, doc in enumerate(vector_docs):
            key = self._doc_key(doc)
            fused[key] = fused.get(key, 0.0) + 1.0 / (self._RRF_K + rank)
            doc_by_key.setdefault(key, doc)
        for rank, doc in enumerate(bm25_docs):
            key = self._doc_key(doc)
            fused[key] = fused.get(key, 0.0) + 1.0 / (self._RRF_K + rank)
            doc_by_key.setdefault(key, doc)

        # standards 分类加权
        for key, doc in doc_by_key.items():
            if self._is_standard(doc):
                fused[key] *= self._STANDARD_BOOST

        top_keys = sorted(fused, key=lambda kk: fused[kk], reverse=True)[:k]
        return [doc_by_key[kk] for kk in top_keys]

    def search(self, query: str, k: int = 5) -> list:
        """混合检索（BM25 + 向量 RRF 融合）"""
        if self.vectorstore is None:
            try:
                self.load_index()
            except FileNotFoundError:
                raise RuntimeError("知识库索引未构建，请先调用 build_index()")

        return self.hybrid_search(query, k=k)

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
    """获取知识库检索器单例。MOCK_MODE=true 时返回 MockRetriever。"""
    global _retriever
    settings = get_settings()

    # Mock 模式：返回本地模拟检索器，不调用嵌入 API 和 ChromaDB
    if settings.MOCK_MODE:
        if _retriever is None:
            from app.mock.knowledge import MockRetriever
            _retriever = MockRetriever()
        return _retriever

    if _retriever is None:
        _retriever = KnowledgeRetriever()
    return _retriever
