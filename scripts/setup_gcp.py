"""Create the private GCS and BigQuery resources required by the RAG pipeline."""

import argparse
import sys
from pathlib import Path

# Support the documented direct invocation: python3 scripts/setup_gcp.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.api_core.exceptions import NotFound
from google.cloud import bigquery, storage

from config import (
    BUCKET_NAME,
    DATASET_ID,
    DOCUMENTS_TABLE,
    EMBEDDINGS_TABLE,
    LOCATION,
    PROJECT_ID,
    require_settings,
)


DOCUMENT_SCHEMA = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("document_name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("gcs_uri", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("chunk_index", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("page_start", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("page_end", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("content", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("content_sha256", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
]

EMBEDDING_SCHEMA = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
    bigquery.SchemaField("embedding_model", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("embedded_at", "TIMESTAMP", mode="REQUIRED"),
]


def ensure_bucket(
    client: storage.Client,
    create: bool,
    harden: bool,
) -> storage.Bucket:
    bucket = client.bucket(BUCKET_NAME)
    created = False
    try:
        bucket.reload()
    except NotFound:
        if not create:
            raise RuntimeError(
                f"Bucket gs://{BUCKET_NAME} does not exist; rerun with --create-bucket"
            )
        bucket = client.create_bucket(bucket, location=LOCATION)
        created = True

    # Confidential review drafts must not be made public through object ACLs or IAM.
    iam = bucket.iam_configuration
    secure = (
        iam.uniform_bucket_level_access_enabled
        and iam.public_access_prevention == "enforced"
    )
    if not secure and not (created or harden):
        raise RuntimeError(
            f"gs://{BUCKET_NAME} is not hardened for confidential drafts. "
            "Use a dedicated bucket, or rerun with --harden-bucket after "
            "checking the impact on existing object ACLs."
        )
    if created or harden:
        iam.uniform_bucket_level_access_enabled = True
        iam.public_access_prevention = "enforced"
        bucket.labels = {
            **(bucket.labels or {}),
            "data_classification": "confidential",
        }
        bucket.patch()
    return bucket


def ensure_table(
    client: bigquery.Client,
    table_id: str,
    schema: list[bigquery.SchemaField],
) -> None:
    table = bigquery.Table(table_id, schema=schema)
    table.labels = {"data_classification": "confidential", "application": "ipcc-rag"}
    try:
        existing = client.get_table(table_id)
    except NotFound:
        client.create_table(table)
        return

    existing_names = {field.name for field in existing.schema}
    additions = [field for field in schema if field.name not in existing_names]
    if additions:
        # BigQuery only permits newly added fields to be nullable. A fresh AR7
        # table is recommended; this compatibility path supports old deployments.
        nullable = [
            bigquery.SchemaField(
                field.name,
                field.field_type,
                mode=field.mode if field.mode == "REPEATED" else "NULLABLE",
            )
            for field in additions
        ]
        existing.schema = [*existing.schema, *nullable]
        client.update_table(existing, ["schema"])


def setup(
    create_bucket: bool = False,
    harden_bucket: bool = False,
) -> None:
    require_settings(
        "PROJECT_ID",
        "DATASET_ID",
        "DOCUMENTS_TABLE",
        "EMBEDDINGS_TABLE",
        "BUCKET_NAME",
    )
    storage_client = storage.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)
    ensure_bucket(storage_client, create_bucket, harden_bucket)

    dataset_id = f"{PROJECT_ID}.{DATASET_ID}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = LOCATION
    dataset.labels = {"data_classification": "confidential", "application": "ipcc-rag"}
    bq_client.create_dataset(dataset, exists_ok=True)

    ensure_table(bq_client, f"{dataset_id}.{DOCUMENTS_TABLE}", DOCUMENT_SCHEMA)
    ensure_table(bq_client, f"{dataset_id}.{EMBEDDINGS_TABLE}", EMBEDDING_SCHEMA)
    print(f"Private RAG resources ready in project {PROJECT_ID}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--create-bucket",
        action="store_true",
        help="Create BUCKET_NAME when it does not already exist.",
    )
    parser.add_argument(
        "--harden-bucket",
        action="store_true",
        help=(
            "Enforce public-access prevention and uniform access on an "
            "existing bucket."
        ),
    )
    args = parser.parse_args()
    setup(
        create_bucket=args.create_bucket,
        harden_bucket=args.harden_bucket,
    )


if __name__ == "__main__":
    main()
