from config import TOP_K
from services.vector_search import search_documents


def retrieve_context(question: str, top_k: int = TOP_K):
    return search_documents(question, top_k)
