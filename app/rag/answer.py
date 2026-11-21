import re
from collections import OrderedDict

from app.rag.retriever import retrieve_documents
from app.agents.llm import stream_response

FALLBACK_ANSWER = (
    "I couldn't find this information in the available company documents."
)

# Number of policy chunks sent to the model.
TOP_K = 3

# Chunks further away than this (cosine distance, 0 = identical)
# are treated as unrelated. Off-topic questions then get the
# fallback answer immediately, without waiting for the model.
# If good questions ever get "not found", raise this value.
MAX_DISTANCE = 0.8

# Answers to repeated questions are remembered until the app restarts.
CACHE_SIZE = 128
_cache = OrderedDict()


def _clean(text: str) -> str:
    """Remove any source / reference lines the model adds anyway."""

    text = re.sub(
        r"(?im)^\s*(source|sources|reference|references)\s*:.*$",
        "",
        text
    )

    return text.strip()


def _build_prompt(question: str, documents: list) -> str:

    # Keep retrieved content internally for accurate answers.
    context = "\n\n".join(
        doc["content"]
        for doc in documents
    )

    return f"""
You are Veltrionyx's Enterprise Knowledge Assistant.

Answer the employee's question using ONLY the company
policy information provided below.

Rules:
1. Do not invent or assume information.
2. If the answer is unavailable, reply exactly:
   "{FALLBACK_ANSWER}"
3. Give a direct, clear and concise answer.
4. Do not mention sources, filenames, references or citations.
5. Do not include unnecessary introductions.

Company Policy Context:
{context}

Employee Question:
{question}

Answer:
""".strip()


def stream_answer(question: str):
    """Yield the answer as it is written.
    Every item is the full answer so far, so the last item is final."""

    key = " ".join(question.lower().split())

    if key in _cache:

        _cache.move_to_end(key)
        yield _cache[key]
        return

    # Retrieve the most relevant policy chunks.
    documents = [
        doc
        for doc in retrieve_documents(question, top_k=TOP_K)
        if doc.get("distance", 0.0) <= MAX_DISTANCE
    ]

    if not documents:
        yield FALLBACK_ANSWER
        return

    prompt = _build_prompt(question, documents)

    text = ""

    for piece in stream_response(prompt):

        text += piece
        yield _clean(text)

    final = _clean(text) or FALLBACK_ANSWER

    _cache[key] = final

    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)

    yield final


def answer_question(question: str) -> str:
    """Return the complete answer (no streaming)."""

    answer = ""

    for answer in stream_answer(question):
        pass

    return answer or FALLBACK_ANSWER


if __name__ == "__main__":
    question = "How many sick leaves are available per year?"
    print(answer_question(question))
