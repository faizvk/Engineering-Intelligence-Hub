"""Source-aware chunking, dispatched on doc_type.

Prose uses a recursive character splitter; code uses the language-aware variant
(splits on class/def/function boundaries, not blind character counts) so a chunk
is a coherent unit. Diagrams and incidents are already one logical unit each and
are not re-split. add_start_index records the char offset for precise citations.

After splitting, each chunk gets a deterministic chunk_index within its source so
re-ingesting a changed file replaces its chunks instead of duplicating them.
"""

from __future__ import annotations

from collections import defaultdict

from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from ingestion.schema import DocType

PROSE_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1200,  # characters; ~300 tokens of prose
    chunk_overlap=150,  # overlap preserves cross-boundary context
    add_start_index=True,  # records char offset -> precise citations later
)

# Cache one splitter per language so we don't rebuild separators every file.
_CODE_SPLITTERS: dict[str, RecursiveCharacterTextSplitter] = {}


def _code_splitter(language: str) -> RecursiveCharacterTextSplitter:
    if language not in _CODE_SPLITTERS:
        try:
            lang_enum = Language(language)
        except ValueError:
            return PROSE_SPLITTER  # unknown language -> safe fallback
        _CODE_SPLITTERS[language] = RecursiveCharacterTextSplitter.from_language(
            language=lang_enum,
            chunk_size=1600,  # code tolerates larger chunks
            chunk_overlap=200,
            add_start_index=True,
        )
    return _CODE_SPLITTERS[language]


def split_documents(docs: list[Document]) -> list[Document]:
    out: list[Document] = []
    for d in docs:
        dt = d.metadata.get("doc_type")
        if dt == DocType.CODE.value and d.metadata.get("language"):
            splitter = _code_splitter(d.metadata["language"])
        elif dt in (DocType.DIAGRAM.value, DocType.INCIDENT.value):
            out.append(d)  # already atomic; do not re-split
            continue
        else:
            splitter = PROSE_SPLITTER
        out.extend(splitter.split_documents([d]))
    return _assign_chunk_index(out)


def _assign_chunk_index(chunks: list[Document]) -> list[Document]:
    """Number chunks 0..n within each source_uri (the 'path' metadata key)."""
    counter: dict[str, int] = defaultdict(int)
    for ch in chunks:
        path = ch.metadata.get("path", "")
        ch.metadata["chunk_index"] = counter[path]
        counter[path] += 1
    return chunks
