from app.rag.vector_store import client, collection

print("ChromaDB connected successfully!")
print("Collection name:", collection.name)
print("Document count:", collection.count())
print("Database location:", client.get_settings())