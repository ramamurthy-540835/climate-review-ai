# RAG architecture

```text
confidential PDFs
      |
      v
private GCS prefix
      |
      v
page extraction -> paragraph/sentence chunks -> BigQuery documents
                                               |
                                               v
Vertex text embeddings -----------------> BigQuery embeddings
                                               |
question -> query embedding -> VECTOR_SEARCH --+
                                               |
                                               v
                                top chunks with page metadata
                                               |
                                               v
                                 grounded Gemini answer + citations
```

Chunking is page-local because expert-review comments need stable page
references. Natural boundaries improve coherence over fixed character slicing;
limited overlap retains context near a boundary. Deterministic IDs couple the
source object name, page, and text so interrupted indexing can resume safely.

The GCS object is the confidential source of truth. BigQuery stores extracted
passages and vectors in separate tables. Retrieval performs one vector search
and joins the nearest IDs to passages, avoiding one BigQuery query per result.

This is dense retrieval. For a larger corpus, add lexical search and reranking
for a hybrid system; for the ten current WG-I draft documents, dense retrieval
with page-aware chunks is a suitable baseline and should be evaluated against a
small set of reviewer questions before tuning chunk size or top-k.
