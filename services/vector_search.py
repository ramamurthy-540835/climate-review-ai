from google.cloud import bigquery

from config import (
    PROJECT_ID,
    DATASET_ID,
    DOCUMENTS_TABLE,
    EMBEDDINGS_TABLE,
    require_settings,
)

from services.embedding_service import get_embedding


def search_documents(question: str, top_k: int = 5):
    """Return nearest chunks with page-level source metadata."""
    require_settings(
        "PROJECT_ID",
        "DATASET_ID",
        "DOCUMENTS_TABLE",
        "EMBEDDINGS_TABLE",
    )
    if not 1 <= top_k <= 50:
        raise ValueError("top_k must be between 1 and 50")

    client = bigquery.Client(project=PROJECT_ID)
    documents = f"{PROJECT_ID}.{DATASET_ID}.{DOCUMENTS_TABLE}"
    embeddings = f"{PROJECT_ID}.{DATASET_ID}.{EMBEDDINGS_TABLE}"
    query_embedding = get_embedding(question)
    query = f"""
    SELECT
        documents.id,
        documents.document_name,
        documents.chunk_index,
        documents.page_start,
        documents.page_end,
        documents.content,
        matches.distance
    FROM VECTOR_SEARCH(
        TABLE `{embeddings}`,
        'embedding',
        (
            SELECT
                @embedding AS embedding
        ),
        top_k => {top_k},
        distance_type => 'COSINE'
    ) AS matches
    JOIN `{documents}` AS documents
      ON documents.id = matches.base.id
    ORDER BY matches.distance
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "embedding",
                "FLOAT64",
                query_embedding,
            )
        ]
    )
    rows = client.query(
        query,
        job_config=job_config,
    ).result()
    return [
        {
            "id": row.id,
            "document": row.document_name,
            "chunk": row.chunk_index,
            "page_start": row.page_start,
            "page_end": row.page_end,
            "distance": row.distance,
            "content": row.content,
        }
        for row in rows
    ]
