from google.cloud import storage
import os

BUCKET_NAME = "ipcc-srcities-bucket-1"

client = storage.Client()


def list_pdfs():
    bucket = client.bucket(BUCKET_NAME)

    return [blob.name for blob in bucket.list_blobs()
            if blob.name.endswith(".pdf")]


def download_pdf(blob_name):
    bucket = client.bucket(BUCKET_NAME)

    blob = bucket.blob(blob_name)

    os.makedirs("downloads", exist_ok=True)

    destination = os.path.join("downloads", os.path.basename(blob_name))

    blob.download_to_filename(destination)

    return destination