import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        """Allow service-account environments that only use real env vars."""
        return False


load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT"))
LOCATION = os.getenv("LOCATION", "us-central1")
GENAI_LOCATION = os.getenv("GENAI_LOCATION", "global")

DATASET_ID = os.getenv("DATASET_ID")

DOCUMENTS_TABLE = os.getenv("DOCUMENTS_TABLE")
EMBEDDINGS_TABLE = os.getenv("EMBEDDINGS_TABLE")

BUCKET_NAME = os.getenv("BUCKET_NAME")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-005")

TOP_K = int(os.getenv("TOP_K", 5))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", 10))

# Word-based limits keep chunks below the embedding input limit while retaining
# enough surrounding prose for an IPCC finding to make sense.
CHUNK_SIZE_WORDS = int(os.getenv("CHUNK_SIZE_WORDS", 450))
CHUNK_OVERLAP_WORDS = int(os.getenv("CHUNK_OVERLAP_WORDS", 75))
GCS_PREFIX = os.getenv("GCS_PREFIX", "ar7wg1/fod")


def require_settings(*names: str) -> None:
    """Fail early instead of constructing malformed GCP resource identifiers."""
    missing = [name for name in names if not globals().get(name)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment settings: {joined}")
