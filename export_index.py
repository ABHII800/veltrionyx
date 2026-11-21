"""Save your ChromaDB knowledge base as one small JSON file.

The cloud server (light mode) reads data/knowledge_base.json instead of
ChromaDB. Run this on your PC whenever you change the policy documents
and run the ingestion again:

    python export_index.py
"""

import json
from pathlib import Path

from app.rag.vector_store import collection

OUTPUT = Path(__file__).resolve().parent / "data" / "knowledge_base.json"

data = collection.get(
    include=["documents", "metadatas", "embeddings"]
)

embeddings = data.get("embeddings")

if embeddings is None or len(embeddings) == 0:
    raise SystemExit(
        "ChromaDB is empty. Run your ingestion script first."
    )

payload = {
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "documents": list(data["documents"]),
    "sources": [
        (metadata or {}).get("source", "unknown")
        for metadata in data["metadatas"]
    ],
    "vectors": [
        [float(number) for number in vector]
        for vector in embeddings
    ],
}

OUTPUT.write_text(json.dumps(payload), encoding="utf-8")

print(
    f"Saved {len(payload['documents'])} chunks "
    f"({OUTPUT.stat().st_size // 1024} KB) to {OUTPUT}"
)
