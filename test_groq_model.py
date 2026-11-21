import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
model = os.getenv("GROQ_MODEL")

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Explain what a RAG chatbot does in three simple sentences."
        }
    ],
)

print("Model:", model)
print("Response:", response.choices[0].message.content)