import vertexai
from vertexai.language_models import TextEmbeddingModel

from config import PROJECT_ID, LOCATION

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION
)

model = TextEmbeddingModel.from_pretrained("text-embedding-005")


def get_embedding(text: str):
    embedding = model.get_embeddings([text])[0]
    return embedding.values