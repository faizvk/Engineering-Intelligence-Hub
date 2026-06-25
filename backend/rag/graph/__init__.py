"""Self-correcting CRAG agent as a LangGraph StateGraph.

LCEL is a DAG; corrective RAG needs loops and branches — grade docs, rewrite +
retry if weak, generate, then check for hallucination and regenerate if
ungrounded. That is a state machine.
"""
