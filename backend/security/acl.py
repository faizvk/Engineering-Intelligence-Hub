"""Row-level access control — the load-bearing RAG security control.

Embeddings are derived from source text, so an un-ACL'd retriever leaks private
content even if the UI hides it. Every retrieval query (dense, lexical, and
therefore hybrid + rerank candidates) MUST carry this predicate, derived from the
server-side authenticated principal — never from a client-supplied filter.

A chunk is visible iff its acl[] overlaps the user's groups. An empty group set
overlaps nothing, so a principal with no groups retrieves nothing (default deny).
"""

from __future__ import annotations

from collections.abc import Sequence

# Mandatory predicate appended to every retrieval WHERE. Bind :acl as text[].
ACL_PREDICATE = "acl && %(acl)s::text[]"


def acl_param(groups: Sequence[str]) -> list[str]:
    return [str(g) for g in groups]
