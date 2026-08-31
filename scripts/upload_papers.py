"""Upload confidential IPCC PDFs to a private GCS prefix."""

import argparse
import base64
import hashlib
import sys
from pathlib import Path

# Support the documented direct invocation: python3 scripts/upload_papers.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.cloud import storage

from config import BUCKET_NAME, GCS_PREFIX, PROJECT_ID, require_settings


def local_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return base64.b64encode(digest.digest()).decode("ascii")


def upload_papers(
    papers_dir: Path,
    prefix: str = GCS_PREFIX,
    force: bool = False,
) -> tuple[int, int]:
    require_settings("PROJECT_ID", "BUCKET_NAME")
    paths = sorted(papers_dir.glob("*.pdf"))
    if not paths:
        raise RuntimeError(f"No PDF files found in {papers_dir}")

    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    bucket.reload()
    uploaded = 0
    skipped = 0

    for path in paths:
        object_name = f"{prefix.strip('/')}/{path.name}"
        blob = bucket.blob(object_name)
        if blob.exists(client):
            blob.reload()
            if blob.md5_hash == local_md5(path):
                print(f"Unchanged: gs://{BUCKET_NAME}/{object_name}")
                skipped += 1
                continue
            if not force:
                raise RuntimeError(
                    f"Object already exists with different content: {object_name}. "
                    "Use --force to replace it."
                )
            generation_match = blob.generation
        else:
            generation_match = 0

        blob.metadata = {
            "data-classification": "confidential",
            "review-stage": "first-order-draft",
            "ipcc-cycle": "ar7",
            "working-group": "wg1",
        }
        blob.cache_control = "private, no-store"
        blob.upload_from_filename(
            path,
            content_type="application/pdf",
            if_generation_match=generation_match,
        )
        print(f"Uploaded: gs://{BUCKET_NAME}/{object_name}")
        uploaded += 1

    return uploaded, skipped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers-dir", type=Path, default=Path("papers"))
    parser.add_argument("--prefix", default=GCS_PREFIX)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    uploaded, skipped = upload_papers(args.papers_dir, args.prefix, args.force)
    print(f"Complete: {uploaded} uploaded, {skipped} unchanged.")


if __name__ == "__main__":
    main()
