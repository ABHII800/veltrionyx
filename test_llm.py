
from app.agents.llm import generate_response

answer = generate_response(
    "What is Retrieval-Augmented Generation? Explain in simple words."
)

print("Veltrionyx AI Response:")
print(answer)
