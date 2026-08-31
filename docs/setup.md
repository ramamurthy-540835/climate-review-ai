# AR7 Working Group I RAG setup

The PDFs in this project are confidential First Order Draft review material.
Use a dedicated private bucket and restrict the runtime service account to the
minimum GCS, BigQuery, and Vertex AI permissions needed.

## 1. Authenticate and configure

```bash
gcloud auth application-default login
cp .env.example .env
```

Edit `.env`. Use new AR7-specific BigQuery table names rather than the older
Cities report tables. Never place reviewer portal credentials in `.env`.

Required IAM capabilities:

- read/write objects in the configured bucket
- create/query/update the configured BigQuery dataset and tables
- invoke Vertex AI embedding and Gemini models

## 2. Create or validate private cloud resources

For an existing bucket:

```bash
python scripts/setup_gcp.py
```

To create `BUCKET_NAME` when it does not exist:

```bash
python scripts/setup_gcp.py --create-bucket
```

New buckets enforce public-access prevention and uniform bucket-level access.
For an existing bucket that lacks those controls, setup stops without changing
it. After checking the impact on existing object ACLs, hardening is explicit:

```bash
python scripts/setup_gcp.py --harden-bucket
```

Prefer a dedicated bucket for confidential draft material.

## 3. Upload the PDFs

```bash
python scripts/upload_papers.py --papers-dir papers
```

Uploads use `gs://BUCKET_NAME/ar7wg1/fod/` by default, set confidential
metadata, disable caching, and use generation preconditions. Identical objects
are skipped. Replacement requires the explicit `--force` flag.

## 4. Chunk and index

```bash
python scripts/index_papers.py
```

The indexer:

- extracts text in reading order and repairs common PDF line wrapping
- chunks within each page on paragraph and sentence boundaries
- uses 450-word chunks with 75-word overlap by default
- stores page numbers and a GCS source URI with every chunk
- creates deterministic SHA-256 IDs, making reruns resumable
- embeds documents with the `RETRIEVAL_DOCUMENT` task type

If a PDF changed or old chunks exist, replacement is explicit:

```bash
python scripts/index_papers.py --replace
```

## 5. Verify

```bash
pytest
uvicorn api:app --reload --port 8080
```

Ask a question in the UI and verify that returned sources name an AR7 WG-I
document and page. Answers must treat the content as draft text, remain
policy-relevant but not policy-prescriptive, and avoid long reproduction.

## Confidentiality controls

- Do not commit `papers/*.pdf`; it is ignored by Git.
- Do not make the API or PDF route publicly accessible.
- Use authenticated Cloud Run ingress/IAM for any deployment.
- Do not log extracted content, prompts, answers, or reviewer credentials.
- Remove the draft objects and derived chunks when access is no longer required.
