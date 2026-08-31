import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from config import (
    PROJECT_ID,
    LOCATION,
    EMBEDDING_MODEL,
)

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
)

model = TextEmbeddingModel.from_pretrained(
    EMBEDDING_MODEL
)


def get_embedding(text: str):

    query = TextEmbeddingInput(text, "RETRIEVAL_QUERY")
    response = model.get_embeddings([query])

    return response[0].values


def get_embeddings(texts: list[str]):

    documents = [
        TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")
        for text in texts
    ]
    response = model.get_embeddings(documents)

    return [x.values for x in response]
