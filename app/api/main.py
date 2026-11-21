
from fastapi import FastAPI
from pydantic import BaseModel

from app.agents.graph import ask_assistant

# Create FastAPI application
app = FastAPI(
    title="Veltrionyx Enterprise AI Assistant",
    description="API for the Veltrionyx Agentic AI Knowledge Assistant",
    version="1.0.0"
)

# Define the question format
class QuestionRequest(BaseModel):
    question: str

# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to Veltrionyx Enterprise AI Assistant",
        "status": "Running"
    }

# AI question endpoint
@app.post("/ask")
def ask_question(request: QuestionRequest):

    answer = ask_assistant(request.question)

    return {
        "question": request.question,
        "answer": answer
    }