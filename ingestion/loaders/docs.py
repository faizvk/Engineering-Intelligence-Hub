"""Technical docs — Markdown, Confluence, Notion.

Use LangChain's loaders directly: DirectoryLoader walks a tree,
UnstructuredMarkdownLoader parses Markdown structure, ConfluenceLoader handles
the wiki export. Native metadata (title, author, last-modified) is lifted into
ChunkMetadata. Public docs default to a broad ACL of ["all"].
"""

from __future__ import annotations

from langchain_community.document_loaders import (
    DirectoryLoader,
    UnstructuredMarkdownLoader,
)
from langchain_core.documents import Document

from core.settings import get_settings
from ingestion.redact import redact
from ingestion.schema import ChunkMetadata, DocType, utcnow_iso


def load_markdown_tree(root: str, source: str, acl: list[str] | None = None) -> list[Document]:
    loader = DirectoryLoader(
        root,
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        loader_kwargs={"mode": "single"},  # one Document per file; we split later
        show_progress=True,
        use_multithreading=True,
    )
    docs = loader.load()
    for d in docs:
        d.page_content = redact(d.page_content)  # scrub secrets before they're embedded
        d.metadata = ChunkMetadata(
            source=source,
            path=d.metadata.get("source", ""),
            doc_type=DocType.DOC,
            title=_first_heading(d.page_content),
            created_at=utcnow_iso(),
            acl=acl or ["all"],
        ).to_dict()
    return docs


def load_confluence(space_key: str, url: str, username: str) -> list[Document]:
    """Confluence export. The API token is read from config, never hardcoded.

    Note: ConfluenceLoader authenticates to Atlassian, not Anthropic — set a
    CONFLUENCE_API_TOKEN in your environment and wire it through settings if you
    use this path. Kept here as the documented pattern.
    """
    from langchain_community.document_loaders import ConfluenceLoader

    get_settings()  # ensure config is loaded/validated
    loader = ConfluenceLoader(
        url=url,
        username=username,
        space_key=space_key,
        include_attachments=False,
        limit=50,
    )
    docs = loader.load()
    for d in docs:
        d.page_content = redact(d.page_content)
        d.metadata = ChunkMetadata(
            source=f"confluence:{space_key}",
            path=d.metadata.get("source", ""),
            doc_type=DocType.DOC,
            title=d.metadata.get("title"),
            author=d.metadata.get("author"),
            created_at=d.metadata.get("when") or utcnow_iso(),
            acl=["all"],
        ).to_dict()
    return docs


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None
