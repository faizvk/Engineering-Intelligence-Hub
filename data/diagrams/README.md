# Diagrams

Drop architecture diagrams here (`.png`, `.jpg`, `.jpeg`). On ingest, each image
is sent to Claude vision, transcribed into a structured description, and the
description is embedded so the diagram becomes searchable by natural-language
questions. The original image path is preserved in metadata so the UI can show
the diagram beside a cited answer.

No images are committed (they're demo-specific); add your own and run
`python -m ingestion.run`.
