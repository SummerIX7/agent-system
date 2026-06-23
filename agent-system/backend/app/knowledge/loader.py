from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_documents(doc_dir: str) -> list:
    """加载目录下所有 Markdown 文档"""
    loader = DirectoryLoader(
        doc_dir,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()
    print(f"加载了 {len(documents)} 篇文档")
    return documents


def split_documents(documents: list, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    """将文档切分为小块"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"切分为 {len(chunks)} 个知识块")
    return chunks
