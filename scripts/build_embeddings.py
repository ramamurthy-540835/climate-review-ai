import time
from google.api_core.exceptions import ResourceExhausted
from google.cloud import bigquery

from config import (
    PROJECT_ID,
    DATASET_ID,
    DOCUMENTS_TABLE,
    EMBEDDINGS_TABLE,
    BATCH_SIZE,
)

from services.embedding_service import get_embeddings

client = bigquery.Client(project=PROJECT_ID)

DOCUMENTS = f"{PROJECT_ID}.{DATASET_ID}.{DOCUMENTS_TABLE}"
EMBEDDINGS = f"{PROJECT_ID}.{DATASET_ID}.{EMBEDDINGS_TABLE}"


def get_completed_ids():

    query = f"""
    SELECT id
    FROM `{EMBEDDINGS}`
    """

    return {
        row.id
        for row in client.query(query).result()
    }


def get_remaining_rows(completed_ids):

    query = f"""
    SELECT
        id,
        document_name,
        chunk_index,
        content
    FROM `{DOCUMENTS}`
    ORDER BY document_name, chunk_index
    """

    rows = []

    for row in client.query(query).result():

        if row.id in completed_ids:
            continue

        rows.append(row)

    return rows


def insert_embeddings(batch_rows, batch_embeddings):

    records = []

    for row, embedding in zip(batch_rows, batch_embeddings):

        records.append({
            "id": row.id,
            "document_name": row.document_name,
            "chunk_index": row.chunk_index,
            "embedding": embedding,
        })

    errors = client.insert_rows_json(
        EMBEDDINGS,
        records,
    )

    if errors:
        print(errors)


completed = get_completed_ids()

remaining = get_remaining_rows(completed)

print(f"\nRemaining chunks : {len(remaining)}")

total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

for batch_number, start in enumerate(range(0, len(remaining), BATCH_SIZE), start=1):

    batch = remaining[start:start + BATCH_SIZE]

    texts = [row.content for row in batch]

    while True:

        try:

            embeddings = get_embeddings(texts)

            insert_embeddings(
                batch,
                embeddings,
            )

            print(
                f"Batch {batch_number}/{total_batches} completed "
                f"({len(batch)} chunks)"
            )

            break

        except ResourceExhausted:

            print("\n===================================================")
            print("Google quota reached (429).")
            print("Waiting 60 seconds before retrying...")
            print("===================================================\n")

            time.sleep(60)

        except Exception as e:

            print(f"\nUnexpected error:\n{e}")

            print("Retrying in 30 seconds...\n")

            time.sleep(30)

print("\nFinished building embeddings!")