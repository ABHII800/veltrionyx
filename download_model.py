"""Download the small MiniLM model used by light mode (about 90 MB).

Render runs this during the build:
    python download_model.py
"""

from app.rag.light_embedder import MODEL_DIR, download_model

if __name__ == "__main__":

    download_model()

    print(f"Model files are in {MODEL_DIR}")
