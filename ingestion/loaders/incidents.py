"""Incident reports — Jira / PagerDuty / Slack exports.

One chunk per incident with heavy structured metadata (severity, status,
services, dates) that powers metadata-filtered retrieval ("SEV-1s touching the
auth service in the last quarter"). Bodies are redacted before embedding.

ACL note: production incidents/postmortems should default to a RESTRICTIVE group
set (default deny). The demo uses ["all"] so the no-auth walkthrough can surface
them; swap to ["oncall", "eng"] behind real auth.
"""

from __future__ import annotations

import json
import pathlib

from langchain_core.documents import Document

from ingestion.redact import redact
from ingestion.schema import ChunkMetadata, DocType


def load_jira_incidents(export_path: str, acl: list[str] | None = None) -> list[Document]:
    raw = json.loads(pathlib.Path(export_path).read_text(encoding="utf-8"))
    docs: list[Document] = []
    for issue in raw["issues"]:
        f = issue["fields"]
        body = redact(
            f"INCIDENT {issue['key']}: {f['summary']}\n\n"
            f"Status: {f['status']['name']} | Priority: {f['priority']['name']}\n\n"
            f"Description:\n{f.get('description', '')}\n\n"
            f"Resolution:\n{(f.get('resolution') or {}).get('description', 'N/A')}"
        )
        docs.append(
            Document(
                page_content=body,
                metadata=ChunkMetadata(
                    source="jira",
                    path=f"https://your-org.atlassian.net/browse/{issue['key']}",
                    doc_type=DocType.INCIDENT,
                    title=f["summary"],
                    author=(f.get("assignee") or {}).get("displayName"),
                    created_at=f.get("created"),
                    acl=acl or ["all"],
                    extra={
                        "ticket": issue["key"],
                        "severity": f["priority"]["name"],  # filter on this
                        "status": f["status"]["name"],
                        "services": [c["name"] for c in f.get("components", [])],
                        "labels": f.get("labels", []),
                    },
                ).to_dict(),
            )
        )
    return docs
