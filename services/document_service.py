import base64
from google.cloud import bigquery, storage

from config import (
    PROJECT_ID,
    DATASET_ID,
    DOCUMENTS_TABLE,
    BUCKET_NAME,
    require_settings,
)


def clean_name(name: str) -> str:
    name = name.replace("ar7wg1_fod_", "")
    name = name.replace("_ai.pdf", "")
    name = name.replace(".pdf", "")
    name = name.replace("---", " — ")
    name = name.replace("-", " ")
    return name.strip()


def _clients():
    require_settings("PROJECT_ID", "DATASET_ID", "DOCUMENTS_TABLE", "BUCKET_NAME")
    return (
        bigquery.Client(project=PROJECT_ID),
        storage.Client(project=PROJECT_ID),
        f"{PROJECT_ID}.{DATASET_ID}.{DOCUMENTS_TABLE}",
    )


def _blob_from_uri(storage_client: storage.Client, gcs_uri: str):
    prefix = f"gs://{BUCKET_NAME}/"
    if not gcs_uri.startswith(prefix):
        raise ValueError("Document URI does not belong to the configured bucket")
    return storage_client.bucket(BUCKET_NAME).blob(gcs_uri[len(prefix):])


def get_documents():
    bigquery_client, storage_client, documents_table = _clients()
    query = f"""
    SELECT
        document_name,
        ANY_VALUE(gcs_uri) AS gcs_uri,
        COUNT(*) AS chunks
    FROM `{documents_table}`
    GROUP BY document_name
    ORDER BY document_name
    """
    rows = bigquery_client.query(query).result()
    documents = []
    for row in rows:
        blob = _blob_from_uri(storage_client, row.gcs_uri)
        blob.reload()
        documents.append({
            "real": row.document_name,
            "display": clean_name(row.document_name),
            "chunks": row.chunks,
            "size_mb": round(blob.size / (1024 * 1024), 2),
        })
    return documents


def get_document_text(document_name: str):
    bigquery_client, _, documents_table = _clients()
    query = f"""
    SELECT content, page_start, chunk_index
    FROM `{documents_table}`
    WHERE document_name=@document_name
    ORDER BY chunk_index
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "document_name",
                "STRING",
                document_name,
            )
        ]
    )
    rows = bigquery_client.query(
        query,
        job_config=job_config,
    ).result()
    return "\n\n".join(row.content for row in rows)


def get_page_context(document_name: str, page: int) -> str:
    """Return bounded context for one displayed PDF page."""
    bigquery_client, _, documents_table = _clients()
    query = f"""
    SELECT content
    FROM `{documents_table}`
    WHERE document_name=@document_name
      AND page_start <= @page
      AND page_end >= @page
    ORDER BY chunk_index
    LIMIT 8
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("document_name", "STRING", document_name),
            bigquery.ScalarQueryParameter("page", "INT64", page),
        ]
    )
    rows = bigquery_client.query(query, job_config=job_config).result()
    return "\n\n".join(row.content for row in rows)


def get_pdf_base64(document_name: str):
    bigquery_client, storage_client, documents_table = _clients()
    query = f"""
    SELECT ANY_VALUE(gcs_uri) AS gcs_uri
    FROM `{documents_table}`
    WHERE document_name=@document_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "document_name",
                "STRING",
                document_name,
            )
        ]
    )
    rows = list(bigquery_client.query(query, job_config=job_config).result())
    if not rows or not rows[0].gcs_uri:
        raise FileNotFoundError(document_name)
    blob = _blob_from_uri(storage_client, rows[0].gcs_uri)
    pdf_bytes = blob.download_as_bytes()
    return base64.b64encode(pdf_bytes).decode("utf-8")