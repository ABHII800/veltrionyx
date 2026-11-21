import chromadb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"

client = chromadb.PersistentClient(
    path=str(CHROMA_PATH)
)

collection = client.get_or_create_collection(
    name="veltrionyx_knowledge_base",
    metadata={"hnsw:space": "cosine"}
)

def add_documents(chunks, embeddings, metadatas):
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=[f"chunk_{i}" for i in range(collection.count(), collection.count() + len(chunks))]
    )

def search_documents(query_embedding, top_k=5):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results