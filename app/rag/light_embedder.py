"""Small MiniLM embedder for servers with little memory (Render free).

It is the SAME model as sentence-transformers' all-MiniLM-L6-v2, but it
runs with ONNX Runtime instead of PyTorch. PyTorch alone needs more than
the 512 MB a free Render server has. This needs about 150 MB.

Your PC keeps using app/rag/embeddings.py. This file is only used when
the LIGHT_MODE=1 setting is on.
"""

import os
import threading
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_DIR = Path(
    os.getenv("LIGHT_MODEL_DIR")
    or PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"
)

# Two Hugging Face repositories that hold the ONNX copy of the model.
# The second one is only a backup.
MODEL_REPOS = [
    "Qdrant/all-MiniLM-L6-v2-onnx",
    "optimum/all-MiniLM-L6-v2",
]

MODEL_FILES = ["model.onnx", "tokenizer.json"]

# The same limit sentence-transformers uses for this model.
MAX_TOKENS = 256

_lock = threading.Lock()
_session = None
_tokenizer = None
_input_names = set()
_output_index = 0


def download_model():
    """Download the model files (about 90 MB) into the models folder."""

    from huggingface_hub import hf_hub_download

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    last_error = None

    for repo in MODEL_REPOS:

        try:

            for name in MODEL_FILES:

                hf_hub_download(
                    repo_id=repo,
                    filename=name,
                    local_dir=str(MODEL_DIR)
                )

            print(f"[light] model downloaded from {repo}")
            return

        except Exception as error:

            last_error = error
            print(f"[light] could not download from {repo}: {error}")

    raise RuntimeError(
        f"Could not download the MiniLM ONNX model: {last_error}"
    )


def _load():
    """Load the model once, the first time it is needed."""

    global _session, _tokenizer, _input_names, _output_index

    if _session is not None:
        return

    with _lock:

        if _session is not None:
            return

        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_path = MODEL_DIR / "model.onnx"
        tokenizer_path = MODEL_DIR / "tokenizer.json"

        # Normally the build step downloads these. If they are missing
        # (for example after a restart), fetch them now.
        if not model_path.exists() or not tokenizer_path.exists():
            download_model()

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1

        # Less memory, a little slower - fine for one short question.
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False

        session = ort.InferenceSession(
            str(model_path),
            sess_options=options,
            providers=["CPUExecutionProvider"]
        )

        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        tokenizer.no_padding()
        tokenizer.enable_truncation(max_length=MAX_TOKENS)

        names = [output.name for output in session.get_outputs()]

        _input_names = {item.name for item in session.get_inputs()}
        _output_index = (
            names.index("last_hidden_state")
            if "last_hidden_state" in names
            else 0
        )
        _tokenizer = tokenizer
        _session = session


def generate_embeddings(texts):
    """Return one normalised 384-number vector for every text."""

    _load()

    vectors = []

    for text in texts:

        encoded = _tokenizer.encode(text)

        feeds = {
            "input_ids": np.array([encoded.ids], dtype=np.int64),
            "attention_mask": np.array(
                [encoded.attention_mask], dtype=np.int64
            ),
            "token_type_ids": np.array(
                [encoded.type_ids], dtype=np.int64
            ),
        }

        feeds = {
            name: value
            for name, value in feeds.items()
            if name in _input_names
        }

        hidden = _session.run(None, feeds)[_output_index][0]

        # Mean pooling: average the word vectors, ignoring padding.
        mask = np.array(
            encoded.attention_mask, dtype=np.float32
        )[:, None]

        pooled = (hidden * mask).sum(axis=0) / max(float(mask.sum()), 1e-9)

        norm = np.linalg.norm(pooled)

        if norm > 0:
            pooled = pooled / norm

        vectors.append(pooled.astype(np.float32).tolist())

    return vectors


def generate_single_embedding(text):

    return generate_embeddings([text])[0]
