"""Extract, structure-aware chunk, embed, and index PDFs stored in GCS."""

import argparse
import hashlib
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Support the documented direct invocation: python3 scripts/index_papers.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vertexai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from google.cloud import bigquery, storage
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from config import (
    BUCKET_NAME,
    CHUNK_OVERLAP_WORDS,
    CHUNK_SIZE_WORDS,
    DATASET_ID,
    DOCUMENTS_TABLE,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    EMBEDDINGS_TABLE,
    GCS_PREFIX,
    LOCATION,
    PROJECT_ID,
    require_settings,
)
from services.chunker import chunk_pages
from services.pdf_processor import extract_pdf_text


def chunk_id(document_name: str, page: int, content: str) -> str:
    payload = f"{document_name}\n{page}\n{content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def batched(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]


class PaperIndexer:
    def __init__(self) -> None:
        require_settings(
            "PROJECT_ID",
            "DATASET_ID",
            "DOCUMENTS_TABLE",
            "EMBEDDINGS_TABLE",
            "BUCKET_NAME",
        )
        self.storage = storage.Client(project=PROJECT_ID)
        self.bigquery = bigquery.Client(project=PROJECT_ID)
        self.bucket = self.storage.bucket(BUCKET_NAME)
        self.documents = f"{PROJECT_ID}.{DATASET_ID}.{DOCUMENTS_TABLE}"
        self.embeddings = f"{PROJECT_ID}.{DATASET_ID}.{EMBEDDINGS_TABLE}"
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        self.embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    def rows_for_blob(self, blob: storage.Blob) -> list[dict]:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            temp_path = handle.name
        try:
            blob.download_to_filename(temp_path)
            pages = extract_pdf_text(temp_path)
        finally:
            os.remove(temp_path)

        chunks = chunk_pages(
            pages,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=CHUNK_OVERLAP_WORDS,
        )
        now = datetime.now(timezone.utc).isoformat()
        rows: list[dict] = []
        for index, chunk in enumerate(chunks):
            content_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
            rows.append(
                {
                    "id": chunk_id(blob.name, chunk.page_start, chunk.content),
                    "document_name": os.path.basename(blob.name),
                    "gcs_uri": f"gs://{BUCKET_NAME}/{blob.name}",
                    "chunk_index": index,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "content": chunk.content,
                    "content_sha256": content_hash,
                    "ingested_at": now,
                }
            )
        return rows

    def existing_ids(self, document_name: str) -> set[str]:
        query = f"SELECT id FROM `{self.documents}` WHERE document_name=@name"
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("name", "STRING", document_name)
            ]
        )
        return {
            row.id
            for row in self.bigquery.query(query, job_config=config).result()
        }

    def delete_document(self, document_name: str) -> None:
        query = f"""
        DELETE FROM `{self.embeddings}`
        WHERE id IN (
            SELECT id FROM `{self.documents}` WHERE document_name=@name
        );
        DELETE FROM `{self.documents}` WHERE document_name=@name
        """
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("name", "STRING", document_name)
            ]
        )
        self.bigquery.query(query, job_config=config).result()

    def insert_documents(self, rows: list[dict]) -> None:
        for batch in batched(rows, 500):
            errors = self.bigquery.insert_rows_json(
                self.documents,
                batch,
                row_ids=[row["id"] for row in batch],
            )
            if errors:
                raise RuntimeError(f"BigQuery document insert failed: {errors}")

    def embedded_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        completed: set[str] = set()
        for batch in batched(ids, 5000):
            query = f"SELECT id FROM `{self.embeddings}` WHERE id IN UNNEST(@ids)"
            config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("ids", "STRING", batch)
                ]
            )
            completed.update(
                row.id
                for row in self.bigquery.query(query, job_config=config).result()
            )
        return completed

    def embed_with_retry(self, texts: list[str], attempts: int = 6) -> list[list[float]]:
        for attempt in range(attempts):
            try:
                inputs = [
                    TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")
                    for text in texts
                ]
                responses = self.embedding_model.get_embeddings(inputs)
                return [response.values for response in responses]
            except (ResourceExhausted, ServiceUnavailable):
                if attempt == attempts - 1:
                    raise
                time.sleep(min(2 ** attempt, 30))
        raise AssertionError("unreachable")

    def insert_embeddings(self, rows: list[dict]) -> int:
        completed = self.embedded_ids([row["id"] for row in rows])
        remaining = [row for row in rows if row["id"] not in completed]
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        for batch in batched(remaining, EMBEDDING_BATCH_SIZE):
            vectors = self.embed_with_retry([row["content"] for row in batch])
            records = [
                {
                    "id": row["id"],
                    "embedding": vector,
                    "embedding_model": EMBEDDING_MODEL,
                    "embedded_at": now,
                }
                for row, vector in zip(batch, vectors)
            ]
            errors = self.bigquery.insert_rows_json(
                self.embeddings,
                records,
                row_ids=[record["id"] for record in records],
            )
            if errors:
                raise RuntimeError(f"BigQuery embedding insert failed: {errors}")
            inserted += len(records)
            print(f"  Embedded {inserted}/{len(remaining)} new chunks")
        return inserted

    def index_blob(self, blob: storage.Blob, replace: bool = False) -> tuple[int, int]:
        document_name = os.path.basename(blob.name)
        print(f"Processing {document_name}")
        rows = self.rows_for_blob(blob)
        if not rows:
            raise RuntimeError(f"No extractable text found in {blob.name}")

        expected = {row["id"] for row in rows}
        existing = self.existing_ids(document_name)
        if existing and existing != expected:
            if not replace:
                raise RuntimeError(
                    f"{document_name} changed or uses an old chunking scheme; "
                    "rerun with --replace"
                )
            self.delete_document(document_name)
            existing = set()

        new_rows = [row for row in rows if row["id"] not in existing]
        if new_rows:
            self.insert_documents(new_rows)
        embedded = self.insert_embeddings(rows)
        print(f"  Ready: {len(rows)} chunks, {embedded} new embeddings")
        return len(new_rows), embedded

    def run(self, prefix: str = GCS_PREFIX, replace: bool = False) -> None:
        blobs = [
            blob
            for blob in self.bucket.list_blobs(prefix=prefix.strip("/") + "/")
            if blob.name.lower().endswith(".pdf")
        ]
        if not blobs:
            raise RuntimeError(
                f"No PDFs found under gs://{BUCKET_NAME}/{prefix.strip('/')}/"
            )
        total_chunks = 0
        total_embeddings = 0
        for blob in sorted(blobs, key=lambda item: item.name):
            chunks, embeddings = self.index_blob(blob, replace=replace)
            total_chunks += chunks
            total_embeddings += embeddings
        print(
            f"Index complete: {len(blobs)} PDFs, {total_chunks} new chunks, "
            f"{total_embeddings} new embeddings."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default=GCS_PREFIX)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    PaperIndexer().run(prefix=args.prefix, replace=args.replace)


if __name__ == "__main__":
    main()
