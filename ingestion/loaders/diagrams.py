"""Architecture diagrams — describe-then-embed with Claude vision.

Embedding models can't read an image. The pattern: send the diagram to Claude
vision, get a dense structured description, embed THAT (so the diagram becomes
retrievable by natural-language questions), and keep the original image path in
metadata so the UI can show the actual diagram beside a cited answer.

Structured output gives clean, independently-filterable fields. It's incompatible
with citations — fine here, because we're transcribing an image, not grounding an
answer.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import pathlib

import anthropic
from langchain_core.documents import Document

from core.settings import get_settings
from ingestion.schema import ChunkMetadata, DocType, utcnow_iso

_s = get_settings()
_client = anthropic.Anthropic(api_key=_s.anthropic_api_key.get_secret_value())

VISION_SYSTEM = (
    "You are an expert software architect. You receive an architecture or system "
    "diagram and produce a precise, retrieval-friendly textual description. "
    "Name every component, every connection and its direction, every protocol/"
    "datastore/queue, and any annotations. Be exhaustive and concrete — this text "
    "is the ONLY representation of the diagram a search system will ever see."
)

DIAGRAM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string", "description": "2-4 sentence overview"},
        "components": {"type": "array", "items": {"type": "string"}},
        "connections": {
            "type": "array",
            "items": {"type": "string"},
            "description": "e.g. 'API Gateway -> Auth Service (gRPC)'",
        },
        "technologies": {"type": "array", "items": {"type": "string"}},
        "searchable_text": {
            "type": "string",
            "description": "A flowing paragraph restating the whole diagram for embedding.",
        },
    },
    "required": ["title", "summary", "components", "connections", "searchable_text"],
    "additionalProperties": False,
}


def describe_diagram(image_path: str) -> dict:
    media_type, _ = mimetypes.guess_type(image_path)
    data = base64.standard_b64encode(pathlib.Path(image_path).read_bytes()).decode()
    resp = _client.messages.create(
        model=_s.model_workhorse,  # workhorse; cheap enough for bulk transcription
        max_tokens=2000,
        system=VISION_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": DIAGRAM_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": data},
                    },
                    {"type": "text", "text": "Describe this architecture diagram."},
                ],
            }
        ],
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)  # always parse JSON, never string-match


def load_diagrams(
    image_paths: list[str], source: str, acl: list[str] | None = None
) -> list[Document]:
    docs: list[Document] = []
    for p in image_paths:
        desc = describe_diagram(p)
        page = f"{desc['title']}\n\n{desc['summary']}\n\n{desc['searchable_text']}"
        docs.append(
            Document(
                page_content=page,
                metadata=ChunkMetadata(
                    source=source,
                    path=p,
                    doc_type=DocType.DIAGRAM,
                    title=desc["title"],
                    created_at=utcnow_iso(),
                    acl=acl or ["all"],
                    extra={
                        "components": desc.get("components", []),
                        "connections": desc.get("connections", []),
                        "technologies": desc.get("technologies", []),
                        "image_path": p,  # UI renders the original diagram
                    },
                ).to_dict(),
            )
        )
    return docs
