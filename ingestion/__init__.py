"""Offline ingestion pipeline: docs/repos/diagrams/incidents -> chunks -> pgvector.

A separate service from backend/, not a module of it — embedding a corpus is a
batch job, not a request handler. Imports from core/ only.
"""
