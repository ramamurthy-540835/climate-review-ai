from services.document_service import (
    get_document_names,
    get_document_text,
)

documents = get_document_names()

print("\nAvailable Documents:\n")

for doc in documents:
    print(doc)

print("\n")

text = get_document_text(documents[0])

print(text[:1000])