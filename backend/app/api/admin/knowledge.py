"""知识库管理 API"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.config import get_settings
from app.models.database import get_db

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])


# ========== 请求/响应模型 ==========

class FileContent(BaseModel):
    content: str


class FileItem(BaseModel):
    path: str
    name: str
    domain: str
    category: str
    size: int
    title: str = ""


class RebuildResult(BaseModel):
    ok: bool
    total_chunks: int = 0
    added: int = 0
    updated: int = 0
    skipped: int = 0
    deleted: int = 0
    message: str = ""


# ========== 工具函数 ==========

def _get_kb_root() -> str:
    """获取知识库根目录（相对于 backend 目录）"""
    settings = get_settings()
    dirs = settings.KNOWLEDGE_BASE_DIRS.split(",")[0].strip()
    # KNOWLEDGE_BASE_DIRS 是相对于 backend 的，如 "../knowledge-base/cnc_domain"
    # build_index.py 运行时 cwd 是 backend/，所以直接 resolve
    return str(Path(dirs).resolve())


def _get_parent_dir() -> str:
    """获取知识库父目录（../knowledge-base/）"""
    full = _get_kb_root()
    parent = str(Path(full).parent)  # ../knowledge-base
    return parent


def _safe_path(rel_path: str) -> Path:
    """将相对路径解析为安全绝对路径，防止路径穿越"""
    parent = _get_parent_dir()
    # 统一使用 / 分隔符
    rel_path = rel_path.replace("\\", "/")
    resolved = (Path(parent) / rel_path).resolve()
    if not str(resolved).startswith(str(Path(parent).resolve())):
        raise HTTPException(status_code=403, detail="非法路径")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {rel_path}")
    return resolved


def _parse_frontmatter_title(file_path: Path) -> str:
    """读取 .md 文件 YAML frontmatter 中的 title"""
    try:
        text = file_path.read_text(encoding="utf-8")
        if text.startswith("---"):
            for line in text.split("\n")[1:]:
                line = line.strip()
                if line.startswith("title:"):
                    return line.split(":", 1)[1].strip()
                if line == "---":
                    break
    except Exception:
        pass
    return ""


# ========== API 端点 ==========

@router.get("/list")
async def list_files(
    _admin=Depends(require_admin),
):
    """列出所有知识库文件（含领域/类别分组）"""
    parent = _get_parent_dir()
    files: list[dict] = []

    for root, dirs, filenames in os.walk(parent):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            full_path = Path(root) / fname
            rel_path = full_path.relative_to(parent).as_posix()
            parts = rel_path.split("/")
            domain = parts[0] if len(parts) > 0 else ""
            category = parts[1] if len(parts) > 1 else ""
            name = parts[-1]

            title = _parse_frontmatter_title(full_path)

            files.append({
                "path": rel_path,
                "name": name,
                "domain": domain,
                "category": category,
                "size": full_path.stat().st_size,
                "title": title or name.replace(".md", ""),
            })

    return {"files": files}


@router.get("/read")
async def read_file(
    path: str = Query(..., description="文件相对路径"),
    _admin=Depends(require_admin),
):
    """读取单个知识库文件内容"""
    file_path = _safe_path(path)
    content = file_path.read_text(encoding="utf-8")
    return {"path": path, "content": content}


@router.post("/write")
async def write_file(
    body: FileContent,
    path: str = Query(..., description="文件相对路径（如不存在则新建）"),
    _admin=Depends(require_admin),
):
    """创建或覆盖知识库文件"""
    parent = _get_parent_dir()
    rel_path = path.replace("\\", "/")
    target = (Path(parent) / rel_path).resolve()

    if not str(target).startswith(str(Path(parent).resolve())):
        raise HTTPException(status_code=403, detail="非法路径")

    # 确保目录存在
    target.parent.mkdir(parents=True, exist_ok=True)

    # 在写入前判断文件是否存在，以正确区分创建和更新
    existed_before = target.exists()

    target.write_text(body.content, encoding="utf-8")

    action = "更新" if existed_before else "创建"
    return {"message": f"文件{action}成功", "path": path}


@router.delete("/delete")
async def delete_file(
    path: str = Query(..., description="文件相对路径"),
    _admin=Depends(require_admin),
):
    """删除知识库文件"""
    file_path = _safe_path(path)
    if not file_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="只能删除 .md 文件")
    file_path.unlink()
    return {"message": f"文件已删除: {path}"}


@router.post("/rebuild-index", response_model=RebuildResult)
async def rebuild_index(
    full: bool = Query(False, description="是否强制全量重建（默认增量同步）"),
    _admin=Depends(require_admin),
):
    """同步向量索引：默认增量（仅处理新增/变更/删除文件），full=true 时全量重建。"""
    import asyncio
    from functools import partial
    from app.knowledge.retriever import KnowledgeRetriever
    from app.core.config import get_settings

    settings = get_settings()
    kb_dirs = [d.strip() for d in settings.KNOWLEDGE_BASE_DIRS.split(",") if d.strip()]

    try:
        retriever = KnowledgeRetriever()

        # 在线程池中执行同步的索引构建
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            None, partial(retriever.build_index_from_dirs, kb_dirs, force=full)
        )

        # 重置全局单例，让下次检索使用新索引
        import app.knowledge.retriever as retriever_mod
        retriever_mod._retriever = None

        mode = "全量重建" if full else "增量同步"
        return RebuildResult(
            ok=True,
            total_chunks=stats["total_chunks"],
            added=stats["added"],
            updated=stats["updated"],
            skipped=stats["skipped"],
            deleted=stats["deleted"],
            message=(
                f"索引{mode}完成，共 {stats['total_chunks']} 个知识块"
                f"（新增 {stats['added']} / 更新 {stats['updated']}"
                f" / 跳过 {stats['skipped']} / 删除 {stats['deleted']}）"
            ),
        )
    except Exception as e:
        return RebuildResult(ok=False, message=f"索引重建失败: {str(e)}")
