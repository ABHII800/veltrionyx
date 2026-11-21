import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# Load project environment variables
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Read configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# "or" (not a default argument) so a blank GROQ_MODEL= line in
# .env falls back to the default model instead of an empty name.
GROQ_MODEL = os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b"

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing from .env")

# Initialize Groq client.
# A shorter timeout and one retry means a network problem shows
# an error quickly instead of leaving the chat waiting for minutes.
client = Groq(
    api_key=GROQ_API_KEY,
    timeout=30.0,
    max_retries=1
)


def _request_options() -> dict:
    """Settings shared by normal and streaming requests."""

    options = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
    }

    # gpt-oss models "think" before they answer. Low reasoning effort
    # makes them think less, so policy answers start sooner.
    # Only these models accept the setting.
    if "gpt-oss" in GROQ_MODEL:
        options["extra_body"] = {"reasoning_effort": "low"}

    return options


def generate_response(prompt: str) -> str:
    """Generate a full response using the configured Groq model."""

    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": prompt}
        ],
        **_request_options()
    )

    return response.choices[0].message.content or ""


def stream_response(prompt: str):
    """Yield the response in small pieces as the model writes it,
    so the chat can show words straight away."""

    stream = client.chat.completions.create(
        messages=[
            {"role": "user", "content": prompt}
        ],
        stream=True,
        **_request_options()
    )

    for chunk in stream:

        if not chunk.choices:
            continue

        piece = chunk.choices[0].delta.content

        if piece:
            yield piece
