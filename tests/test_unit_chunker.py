import pytest

from services.chunker import chunk_pages, chunk_text


def test_chunk_pages_keeps_page_metadata_and_natural_boundaries():
    pages = [
        {
            "page": 7,
            "content": (
                "Section heading\n\n"
                "One two three four five.\n\n"
                "Six seven eight nine ten."
            ),
        }
    ]

    chunks = chunk_pages(pages, chunk_size_words=8, overlap_words=2)

    assert len(chunks) == 2
    assert all(chunk.page_start == 7 and chunk.page_end == 7 for chunk in chunks)
    assert chunks[0].content.endswith("five.")
    assert chunks[1].content.startswith("four five.")


def test_chunk_pages_never_crosses_pages():
    pages = [
        {"page": 1, "content": "First page content."},
        {"page": 2, "content": "Second page content."},
    ]

    chunks = chunk_pages(pages, chunk_size_words=20, overlap_words=3)

    assert [chunk.page_start for chunk in chunks] == [1, 2]
    assert "Second" not in chunks[0].content


def test_long_paragraph_splits_on_sentence_boundary():
    pages = [
        {
            "page": 2,
            "content": "Alpha beta gamma. Delta epsilon zeta. Eta theta iota.",
        }
    ]

    chunks = chunk_pages(pages, chunk_size_words=6, overlap_words=1)

    assert chunks[0].content.endswith("zeta.")
    assert chunks[1].content.startswith("zeta.")


@pytest.mark.parametrize(
    "size,overlap",
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_word_chunk_limits(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([], chunk_size_words=size, overlap_words=overlap)


def test_legacy_chunker_rejects_nonadvancing_overlap():
    with pytest.raises(ValueError):
        chunk_text("text", chunk_size=10, overlap=10)
