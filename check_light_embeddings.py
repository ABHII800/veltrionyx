"""Check that the light (ONNX) embedder matches your normal embedder.

Run on your PC, with your .venv active:
    python check_light_embeddings.py

It downloads the ~90 MB light model the first time. Every similarity
should be 0.999 or higher.
"""

import numpy as np

from app.rag.embeddings import generate_single_embedding as normal
from app.rag.light_embedder import (
    MODEL_DIR,
    download_model,
    generate_single_embedding as light,
)

SENTENCES = [
    "How many sick leaves are available per year?",
    "Can I work from home?",
    "What is the notice period when I resign?",
    "How do I claim travel expenses?",
    "What should I do if I lose my laptop?",
    "Employees are entitled to twelve casual leaves every calendar year "
    "and unused leave cannot be carried forward to the next year.",
]

if not (MODEL_DIR / "model.onnx").exists():
    download_model()

worst = 1.0

for text in SENTENCES:

    a = np.asarray(light(text), dtype=np.float64)
    b = np.asarray(normal(text), dtype=np.float64)

    similarity = float(
        a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
    )

    worst = min(worst, similarity)

    print(f"{similarity:.5f}  {text[:60]}")

print()

if worst >= 0.999:
    print(f"PASS - lowest similarity {worst:.5f}. Light mode is safe to use.")
else:
    print(f"CHECK - lowest similarity {worst:.5f}. Send me this output.")
