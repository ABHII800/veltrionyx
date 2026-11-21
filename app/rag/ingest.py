
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.embeddings import generate_embeddings
from app.rag.vector_store import collection

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_PATH = PROJECT_ROOT / "data" / "documents"

def load_documents():
    documents = []

    for file_path in DOCUMENTS_PATH.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8")

        if text.strip():
            documents.append({
                "text": text,
                "source": file_path.name
            })

    return documents


def ingest_documents():
    documents = load_documents()

    if not documents:
        print("No policy documents found.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = []
    metadatas = []

    for document in documents:
        document_chunks = splitter.split_text(document["text"])

        for chunk in document_chunks:
            chunks.append(chunk)
            metadatas.append({
                "source": document["source"]
            })

    embeddings = generate_embeddings(chunks)

    # Replace existing records to avoid duplicate ingestion
    existing_ids = collection.get()["ids"]

    if existing_ids:
        collection.delete(ids=existing_ids)

    collection.add(
        ids=[f"policy_chunk_{i}" for i in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print("Document ingestion completed!")
    print("Files loaded:", len(documents))
    print("Total chunks stored:", collection.count())


if __name__ == "__main__":
    ingest_documents()
