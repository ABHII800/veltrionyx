import json
import os
import time
from pathlib import Path

import numpy as np

# --------------------------------------------------
# TWO MODES
#
# Normal (your PC):  PyTorch MiniLM + ChromaDB.
# LIGHT_MODE=1 (free cloud server with 512 MB of memory):
#     the same MiniLM model through ONNX Runtime, and the chunks
#     are read from data/knowledge_base.json (made by
#     export_index.py). Neither PyTorch nor ChromaDB is loaded.
# --------------------------------------------------

LIGHT_MODE = os.getenv("LIGHT_MODE", "").strip().lower() in (
    "1", "true", "yes"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_FILE = PROJECT_ROOT / "data" / "knowledge_base.json"

if LIGHT_MODE:

    from app.rag.light_embedder import generate_single_embedding

else:

    from app.rag.embeddings import generate_single_embedding
    from app.rag.vector_store import collection

# --------------------------------------------------
# IN-MEMORY COPY OF THE KNOWLEDGE BASE
#
# The policy documents are small, so every chunk and its
# vector is read from ChromaDB ONCE at startup and searched
# in memory. This avoids a disk / SQLite round trip on every
# question, which was taking seconds.
#
# ChromaDB is still the persistent store. If you run the
# ingestion again, restart the app so the new chunks load.
# --------------------------------------------------

_documents = []
_sources = []
_vectors = np.zeros((0, 0), dtype=np.float32)


def reload_index():
    """Read all chunks and vectors from ChromaDB into memory."""

    global _documents, _sources, _vectors

    started = time.perf_counter()

    if LIGHT_MODE:

        if not INDEX_FILE.exists():
            raise FileNotFoundError(
                f"{INDEX_FILE} not found. On your PC run: "
                "python export_index.py  (then upload the file)"
            )

        saved = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

        documents = saved["documents"]
        sources = saved["sources"]
        embeddings = saved["vectors"]

    else:

        data = collection.get(
            include=["documents", "metadatas", "embeddings"]
        )

        documents = list(data["documents"])
        sources = [
            (metadata or {}).get("source", "unknown")
            for metadata in data["metadatas"]
        ]
        embeddings = data.get("embeddings")

    if embeddings is None or len(embeddings) == 0:

        _documents = []
        _sources = []
        _vectors = np.zeros((0, 0), dtype=np.float32)

        print("[retrieve] knowledge base is empty")
        return

    vectors = np.asarray(embeddings, dtype=np.float32)

    # Normalise so a dot product equals cosine similarity.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0

    _vectors = vectors / norms
    _documents = list(documents)
    _sources = list(sources)

    print(
        f"[retrieve] loaded {len(_documents)} chunks "
        f"into memory in {time.perf_counter() - started:.2f}s"
        f"{' (light mode)' if LIGHT_MODE else ''}"
    )


def retrieve_documents(query: str, top_k: int = 5):

    if len(_documents) == 0:
        return []

    started = time.perf_counter()

    query_vector = np.asarray(
        generate_single_embedding(query),
        dtype=np.float32
    )

    norm = np.linalg.norm(query_vector)

    if norm > 0:
        query_vector = query_vector / norm

    embedded = time.perf_counter()

    similarity = _vectors @ query_vector

    best = np.argsort(-similarity)[:min(top_k, len(similarity))]

    # Same meaning as ChromaDB's cosine distance: 0 = identical.
    retrieved_documents = [
        {
            "content": _documents[i],
            "source": _sources[i],
            "distance": float(1.0 - similarity[i])
        }
        for i in best
    ]

    finished = time.perf_counter()

    # Timing is printed in the terminal to help find slow steps.
    print(
        f"[retrieve] embed {embedded - started:.2f}s | "
        f"search {finished - embedded:.3f}s | "
        f"closest distance {retrieved_documents[0]['distance']:.2f}"
    )

    return retrieved_documents


# Load the index once, when the app starts.
reload_index()


if __name__ == "__main__":
    question = "How many casual leaves can an employee take per year?"

    documents = retrieve_documents(question)

    print("\nUser Question:", question)
    print("\nRetrieved Policy Information:\n")

    for doc in documents:
        print("Source:", doc["source"])
        print("Distance:", round(doc["distance"], 4))
        print("Content:", doc["content"])
        print("-" * 60)
