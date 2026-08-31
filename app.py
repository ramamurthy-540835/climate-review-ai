import os
print(__file__)

from services.storage import list_pdfs, download_pdf
from services.pdf_processor import extract_pdf_text
from services.chunker import chunk_text
from services.bigquery_service import insert_chunks

# Get all PDFs from Cloud Storage
pdfs = list_pdfs()

print("\nAvailable PDFs:\n")

for pdf in pdfs:
    print(pdf)

# Process every PDF
for pdf_name in pdfs:

    print(f"\nProcessing: {pdf_name}")

    pdf_path = download_pdf(pdf_name)

    pages = extract_pdf_text(pdf_path)

    for page in pages:

        chunks = chunk_text(page["content"])

        insert_chunks(
            document_name=os.path.basename(pdf_name),
            page_number=page["page"],
            chunks=chunks
        )

print("\nAll PDFs processed successfully!")