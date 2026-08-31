from services.embedding_service import get_embedding

embedding = get_embedding(
    "Climate change is one of the biggest challenges."
)

print(len(embedding))