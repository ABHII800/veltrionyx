
from sentence_transformers import SentenceTransformer

# Load the embedding model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Convert text into numerical vectors.
    """

    embeddings = embedding_model.encode(
        texts,
        normalize_embeddings=True
    )

    return embeddings.tolist()


def generate_single_embedding(text: str) -> list[float]:
    """
    Convert one text into a numerical vector.
    """

    embedding = embedding_model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()
