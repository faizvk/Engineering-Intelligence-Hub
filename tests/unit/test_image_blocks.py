"""Diagram chunks attach their image to the generation call; others don't.
Pure-stdlib + pydantic, always green.
"""

import base64

import pytest

pytest.importorskip("pydantic")

from backend.llm.blocks import to_image_blocks  # noqa: E402
from core.schemas import DocType, RetrievedChunk  # noqa: E402

# A 1x1 transparent PNG.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _diagram(path):
    return RetrievedChunk(
        doc_id="d#0", title="Arch", text="...", source_uri="diagrams/a.png",
        doc_type=DocType.DIAGRAM, metadata={"image_path": str(path)},
    )


def test_diagram_with_real_image_is_attached(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(_PNG)
    blocks = to_image_blocks([_diagram(img)])
    assert len(blocks) == 1
    assert blocks[0]["type"] == "image"
    assert blocks[0]["source"]["media_type"] == "image/png"


def test_missing_file_is_skipped(tmp_path):
    assert to_image_blocks([_diagram(tmp_path / "nope.png")]) == []


def test_non_diagram_is_skipped():
    doc = RetrievedChunk(doc_id="x", title="t", text="...", source_uri="u", doc_type=DocType.DOC)
    assert to_image_blocks([doc]) == []
