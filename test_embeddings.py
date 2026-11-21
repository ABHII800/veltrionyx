from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

text = ["Veltrionyx is an AI-powered knowledge assistant."]

embedding = model.encode(text, normalize_embeddings=True)

print("Embedding generated successfully!")
print("Embedding dimensions:", len(embedding[0]))
print("First 5 values:", embedding[0][:5])