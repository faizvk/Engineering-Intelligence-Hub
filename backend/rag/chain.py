"""The core RAG chain in LCEL, plus conversational RAG with message history.

LCEL composes Runnables with `|`. RunnableParallel fans the input out (retrieve
docs AND keep the question); the result pipes through a prompt into a tiered
ChatAnthropic. The conversational variant condenses history + follow-up into a
standalone query before retrieving (fixing the pronoun-laden follow-up failure)
and persists turns in Postgres.

This is the declarative single-/multi-turn path; the self-correcting CRAG graph
(graph/) handles the hard case. For span-level citations use the raw-SDK answer()
— citations are incompatible with structured outputs, so they live on the answer
call, not the grading nodes.
"""

from __future__ import annotations

from operator import itemgetter

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnableParallel

from backend.llm.models import llm_haiku, llm_sonnet
from backend.rag.pipeline import retrieve
from core.settings import get_settings

SYSTEM = (
    "You are the Engineering Intelligence Hub assistant. Answer using ONLY the "
    "provided context, drawn from internal docs, architecture diagrams, code, and "
    "incident reports. If the context is insufficient, say so explicitly. Cite "
    "every claim with its [source] tag. Be precise and terse — engineers are reading this."
)

# Cache the stable system prompt across turns (prefix match). Per-turn retrieved
# chunks are NOT cached — they change every request.
_system_block = {"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}

prompt = ChatPromptTemplate.from_messages(
    [("system", [_system_block]), ("human", "Context:\n{context}\n\nQuestion: {question}")]
)

# Retrieval as a Runnable (routing happens inside the pipeline).
retriever = RunnableLambda(lambda q: retrieve(q))


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(
        f"[source: {d.metadata.get('source_uri', 'unknown')}]\n{d.page_content}"
        for d in docs
    )


# Single-turn RAG: retrieve in parallel with passing the question through.
rag_chain = (
    RunnableParallel(
        context=(itemgetter("question") | retriever | format_docs),
        question=itemgetter("question"),
    )
    | prompt
    | llm_sonnet
    | StrOutputParser()
)

# Variant that returns the cited source Documents alongside the answer.
rag_with_sources = RunnableParallel(
    context=(itemgetter("question") | retriever),
    question=itemgetter("question"),
).assign(
    answer=(
        RunnableParallel(
            context=itemgetter("context") | RunnableLambda(format_docs),
            question=itemgetter("question"),
        )
        | prompt
        | llm_sonnet
        | StrOutputParser()
    )
)

# ---- Conversational RAG (history-aware retrieval) ----

_condense_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given the chat history and a follow-up question, rewrite the "
            "follow-up as a standalone question. Return only the question.",
        ),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)
condense_q = _condense_prompt | llm_haiku | StrOutputParser()  # cheap rewrite -> Haiku

_answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", [_system_block]),
        MessagesPlaceholder("history"),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)

conversational_chain = (
    RunnableParallel(
        standalone=condense_q,
        question=itemgetter("question"),
        history=itemgetter("history"),
    )
    .assign(context=itemgetter("standalone") | retriever | format_docs)
    | _answer_prompt
    | llm_sonnet
    | StrOutputParser()
)


_HISTORY_READY = False


def get_history(session_id: str):
    """Postgres-backed transcript per session. Auto-creates the chat_history table
    on first use (langchain-postgres owns its schema). Swap for Redis if latency demands."""
    global _HISTORY_READY
    import psycopg
    from langchain_postgres import PostgresChatMessageHistory

    conn = psycopg.connect(get_settings().database_url_raw)
    if not _HISTORY_READY:
        try:
            PostgresChatMessageHistory.create_tables(conn, "chat_history")
        except Exception:
            pass  # already exists
        _HISTORY_READY = True
    return PostgresChatMessageHistory("chat_history", session_id, sync_connection=conn)


def build_chat_rag():
    """Wrap the conversational chain with per-session Postgres history."""
    from langchain_core.runnables.history import RunnableWithMessageHistory

    return RunnableWithMessageHistory(
        conversational_chain,
        get_history,
        input_messages_key="question",
        history_messages_key="history",
    )
