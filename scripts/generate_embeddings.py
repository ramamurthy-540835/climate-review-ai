from google.cloud import bigquery
import vertexai
from vertexai.language_models import TextEmbeddingModel

from config import PROJECT_ID, LOCATION, DATASET_ID, TABLE_ID

# Initialize Vertex AI
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION
)

# Load embedding model
model = TextEmbeddingModel.from_pretrained(
    "text-embedding-005"
)

client = bigquery.Client()

table = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# Read all chunks
query = f"""
SELECT
    id,
    content
FROM `{table}`
"""

rows = client.query(query).result()

for row in rows:

    print(f"Embedding: {row.id}")

    embedding = model.get_embeddings([row.content])[0].values

    update_query = f"""
    UPDATE `{table}`
    SET embedding=@embedding
    WHERE id=@id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "embedding",
                "FLOAT64",
                embedding,
            ),
            bigquery.ScalarQueryParameter(
                "id",
                "STRING",
                row.id,
            ),
        ]
    )

    client.query(update_query, job_config=job_config).result()

print("Finished generating embeddings!")