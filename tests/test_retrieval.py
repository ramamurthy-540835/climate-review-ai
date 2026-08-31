from services.retrieval_service import retrieve_context

question = "How can cities reduce greenhouse gas emissions?"

results = retrieve_context(question)

print()

for i, result in enumerate(results, start=1):

    print("=" * 80)

    print(f"Result {i}")

    print(f"Document : {result['document']}")

    print(f"Chunk    : {result['chunk']}")

    print(f"Distance : {result['distance']}")

    print()

    print(result["content"][:500])

    print()