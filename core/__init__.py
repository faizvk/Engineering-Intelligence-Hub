"""Shared, dependency-light kernel imported by backend, ingestion, and evals.

Nothing in core/ may import from backend/, ingestion/, or evals/ — the
dependency arrow points only inward.
"""
