"""Code repositories — GitLoader for real repos, a local walker for the demo.

Code is not prose: it is tagged doc_type="code" (so it lands in code_chunks and
is embedded with voyage-code-3) and chunked on syntax boundaries downstream.
Binaries, vendored deps, lockfiles, and build output are filtered out.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from ingestion.redact import redact
from ingestion.schema import ChunkMetadata, DocType, utcnow_iso

# Map file extension -> LangChain Language enum value (used by the code splitter).
EXT_TO_LANG = {
    ".py": "python",
    ".js": "js",
    ".ts": "ts",
    ".tsx": "ts",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".rb": "ruby",
    ".cpp": "cpp",
    ".c": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sol": "sol",
    ".md": "markdown",
}

_EXCLUDE = ("node_modules/", "/vendor/", "/dist/", "/.git/", "/build/")


def load_repo(clone_url: str, repo_path: str, branch: str = "main") -> list[Document]:
    """Clone (or read a local) git repo via GitLoader; one Document per file."""
    from langchain_community.document_loaders import GitLoader

    loader = GitLoader(
        clone_url=clone_url,
        repo_path=repo_path,
        branch=branch,
        file_filter=lambda p: (
            any(p.endswith(ext) for ext in EXT_TO_LANG) and not any(x in p for x in _EXCLUDE)
        ),
    )
    docs = loader.load()
    repo_name = clone_url.rstrip("/").split("/")[-1].removesuffix(".git")
    for d in docs:
        _tag(d, repo_name, d.metadata["file_path"])
    return docs


def load_local_code(root: str, repo: str, acl: list[str] | None = None) -> list[Document]:
    """Walk a local directory tree (no git required) — used for the demo corpus."""
    root_path = Path(root)
    docs: list[Document] = []
    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue
        posix = path.as_posix()
        if path.suffix not in EXT_TO_LANG or any(x in posix for x in _EXCLUDE):
            continue
        rel = path.relative_to(root_path).as_posix()
        d = Document(page_content=redact(path.read_text(encoding="utf-8", errors="ignore")))
        _tag(d, repo, rel, acl=acl)
        docs.append(d)
    return docs


def _tag(d: Document, repo: str, file_path: str, acl: list[str] | None = None) -> None:
    ext = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
    d.metadata = ChunkMetadata(
        source=f"repo:{repo}",
        path=f"{repo}/{file_path}",
        doc_type=DocType.CODE,
        repo=repo,
        language=EXT_TO_LANG.get(ext),
        title=file_path,
        created_at=utcnow_iso(),
        acl=acl or ["all"],
    ).to_dict()
