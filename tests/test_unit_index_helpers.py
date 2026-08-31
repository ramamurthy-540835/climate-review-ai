from scripts.index_papers import batched, chunk_id


def test_chunk_id_is_deterministic_and_page_sensitive():
    first = chunk_id("chapter.pdf", 4, "finding")
    assert first == chunk_id("chapter.pdf", 4, "finding")
    assert first != chunk_id("chapter.pdf", 5, "finding")
    assert len(first) == 64


def test_batched_preserves_order():
    values = list(range(7))

    assert list(batched(values, 3)) == [[0, 1, 2], [3, 4, 5], [6]]
