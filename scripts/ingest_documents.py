import os
import tempfile
import uuid

from google.cloud import storage
from google.cloud import bigquery

from config import (
    PROJECT_ID,
    DATASET_ID,
    DOCUMENTS_TABLE,
    BUCKET_NAME,
)

from services.pdf_processor import extract_pdf_text
from services.chunker import chunk_text

# --------------------------------------------------
# Clients
# --------------------------------------------------

storage_client = storage.Client(project=PROJECT_ID)
bigquery_client = bigquery.Client(project=PROJECT_ID)

bucket = storage_client.bucket(BUCKET_NAME)

table = f"{PROJECT_ID}.{DATASET_ID}.{DOCUMENTS_TABLE}"


# --------------------------------------------------
# Already ingested documents
# --------------------------------------------------

def get_existing_documents():

    query = f"""
    SELECT DISTINCT document_name
    FROM `{table}`
    """

    rows = bigquery_client.query(query).result()

    return {row.document_name for row in rows}


# --------------------------------------------------
# Insert rows
# --------------------------------------------------

def insert_rows(rows):

    errors = bigquery_client.insert_rows_json(
        table,
        rows,
    )

    if errors:
        print(errors)


# --------------------------------------------------
# Main
# --------------------------------------------------

existing_documents = get_existing_documents()

blobs = list(bucket.list_blobs())

pdfs = [
    blob
    for blob in blobs
    if blob.name.lower().endswith(".pdf")
]

print(f"\nFound {len(pdfs)} PDF files.\n")

for pdf in pdfs:

    filename = os.path.basename(pdf.name)

    if filename in existing_documents:

        print(f"Skipping {filename}")

        continue

    print(f"\nProcessing {filename}")

    with tempfile.NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
    ) as temp_file:

        pdf.download_to_filename(
            temp_file.name
        )

        pages = extract_pdf_text(
            temp_file.name
        )

    os.remove(temp_file.name)

    rows = []

    chunk_index = 0

    for page in pages:

        chunks = chunk_text(
            page["content"]
        )

        for chunk in chunks:

            rows.append({

                "id": str(uuid.uuid4()),

                "document_name": filename,

                "chunk_index": chunk_index,

                "content": chunk,

            })

            chunk_index += 1

    insert_rows(rows)

    print(
        f"Inserted {len(rows)} chunks."
    )

print("\nFinished ingesting documents!")