import re
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析文档头部的 YAML 元数据"""
    metadata = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()
            return metadata, body
    return metadata, content


def load_documents(doc_dir: str) -> list:
    """加载目录下所有 Markdown 文档，解析元数据"""
    loader = DirectoryLoader(
        doc_dir,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()

    # 解析每个文档的元数据
    for doc in documents:
        content = doc.page_content
        frontmatter, body = _parse_frontmatter(content)

        # 将元数据存入 metadata
        for key, value in frontmatter.items():
            doc.metadata[key] = value

        # 用去掉元数据后的内容替换
        doc.page_content = body

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
