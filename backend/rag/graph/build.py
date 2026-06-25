"""Assemble the StateGraph.

START -> route -> (retrieve | reject)
retrieve -> grade_documents -> (generate | rewrite_query -> retrieve)
generate -> check_hallucination -> (END | generate)

A PostgresSaver checkpointer makes the agent stateful and resumable (every node
transition persisted; thread_id gives per-conversation memory) on the same
Postgres the rest of the system uses.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.rag.graph import edges, nodes
from backend.rag.graph.state import RAGState


def build_graph(checkpointer=None):
    g = StateGraph(RAGState)
    g.add_node("route", nodes.route)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("grade_documents", nodes.grade_documents)
    g.add_node("rewrite_query", nodes.rewrite_query)
    g.add_node("generate", nodes.generate)
    g.add_node("check_hallucination", nodes.check_hallucination)
    g.add_node("reject", nodes.reject)

    g.add_edge(START, "route")
    g.add_conditional_edges(
        "route", edges.decide_route, {"retrieve": "retrieve", "reject": "reject"}
    )
    g.add_edge("retrieve", "grade_documents")
    g.add_conditional_edges(
        "grade_documents",
        edges.decide_after_grading,
        {"generate": "generate", "rewrite_query": "rewrite_query"},
    )
    g.add_edge("rewrite_query", "retrieve")  # the self-correction loop
    g.add_edge("generate", "check_hallucination")
    g.add_conditional_edges(
        "check_hallucination",
        edges.decide_after_generation,
        {"end": END, "generate": "generate"},
    )
    g.add_edge("reject", END)
    return g.compile(checkpointer=checkpointer)


def build_graph_with_postgres(db_url: str):
    """Compile with a PostgresSaver checkpointer for resumable, memory-bearing runs."""
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(db_url) as cp:
        cp.setup()
        return build_graph(cp)


def draw_mermaid() -> str:
    """Export the graph topology as Mermaid (for the README)."""
    return build_graph().get_graph().draw_mermaid()
