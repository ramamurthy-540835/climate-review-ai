import vertexai
from vertexai.language_models import TextEmbeddingModel

from config import PROJECT_ID, LOCATION

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION
)

model = TextEmbeddingModel.from_pretrained(
    "text-embedding-005"
)

embedding = model.get_embeddings(
    ["Hello World"]
)[0].values

print("Embedding Dimension:", len(embedding))