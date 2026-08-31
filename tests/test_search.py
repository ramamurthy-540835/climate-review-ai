from services.vector_search import search_documents

results = search_documents(
    "How can cities reduce greenhouse gas emissions?"
)

for i, result in enumerate(results, start=1):

    print("=" * 80)
    print(f"Result {i}")
    print(f"Score: {result['score']:.4f}")
    print(f"Document: {result['document']}")
    print(f"Page: {result['page']}")
    print(result["content"][:500])