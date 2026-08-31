import re

import pymupdf


def _normalize_text(text: str) -> str:
    """Repair common PDF line wrapping while preserving paragraph boundaries."""
    text = text.replace("\u00ad", "").replace("\u00a0", " ")
    text = re.sub(r"(?<=\w)-\n(?=[a-z])", "", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)

    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def extract_pdf_text(pdf_path):
    """
    Extract text page by page from a PDF.
    Returns a list of dictionaries:
    [
        {
            "page": 1,
            "content": "..."
        },
        ...
    ]
    """

    document = pymupdf.open(pdf_path)

    pages = []

    for page_number in range(len(document)):
        page = document.load_page(page_number)

        text = _normalize_text(page.get_text("text", sort=True))

        pages.append({
            "page": page_number + 1,
            "content": text
        })

    document.close()

    return pages