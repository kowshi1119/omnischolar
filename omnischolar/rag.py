import chromadb
import fitz
import ollama
import os

client = chromadb.PersistentClient("./study_db")

# ── Embedding model (EmbeddingGemma when available, falls back via env var) ──
# To switch: set OLLAMA_EMBED_MODEL=embedding-gemma:1b in .env after pulling
_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# ── BM25 sparse index (rebuilt on each ingestion) ─────────────────────────────
_bm25_index = None
_bm25_docs: list = []

try:
    from rank_bm25 import BM25Okapi as _BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    _BM25Okapi = None


def get_collection():
    return client.get_or_create_collection(
        name="study_materials",
        metadata={"hnsw:space": "cosine"},
    )


def ingest_pdf(pdf_path, subject, language, al_stream=None, al_subject=None):
    collection = get_collection()
    doc = fitz.open(pdf_path)
    chunks, metadatas, ids = [], [], []

    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        for i in range(0, len(text), 700):
            chunk = text[i : i + 800].strip()
            if len(chunk) > 50:
                chunks.append(chunk)
                meta = {
                    "page": page_num + 1,
                    "subject": subject,
                    "language": language,
                    "source": pdf_path,
                }
                if al_stream:
                    meta["al_stream"] = al_stream
                if al_subject:
                    meta["al_subject"] = al_subject
                metadatas.append(meta)
                ids.append(f"{subject}_{page_num}_{i}")

    embeddings = []
    for chunk in chunks:
        result = ollama.embeddings(model=_EMBED_MODEL, prompt=chunk)
        embeddings.append(result["embedding"])

    if chunks:
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        # Rebuild BM25 index with all documents in collection
        try:
            all_docs = collection.get()["documents"]
            build_bm25_index(all_docs)
        except Exception:
            pass
    return len(chunks)


def retrieve_context(query, subject=None, n_results=4, al_subject=None):
    collection = get_collection()
    result = ollama.embeddings(model=_EMBED_MODEL, prompt=query)
    # Build filter: prefer al_subject filter for A/L students, fall back to subject
    if al_subject:
        where = {"al_subject": al_subject}
    elif subject:
        where = {"subject": subject}
    else:
        where = None
    results = collection.query(
        query_embeddings=[result["embedding"]],
        n_results=n_results,
        where=where,
    )
    if not results["documents"] or not results["documents"][0]:
        return "", []

    context = "\n---\n".join(results["documents"][0])
    sources = [
        f"{metadata['source']} page {metadata['page']}"
        for metadata in results["metadatas"][0]
    ]
    return context, sources


def get_retrieval_coverage(subject: str = None) -> dict:
    """Return basic coverage stats for the study_materials collection."""
    try:
        col = get_collection()
        total = col.count()
        return {"total_chunks": total, "subject": subject or "all"}
    except Exception:
        return {"total_chunks": 0, "subject": subject or "all"}


# ── BM25 sparse index ─────────────────────────────────────────────────────────

def build_bm25_index(texts: list) -> None:
    """Build (or rebuild) in-memory BM25 index from document chunks."""
    global _bm25_index, _bm25_docs
    if not _BM25_AVAILABLE or not texts:
        return
    _bm25_docs = list(texts)
    tokenized = [t.lower().split() for t in _bm25_docs]
    _bm25_index = _BM25Okapi(tokenized)


# ── Hybrid retrieval: dense + BM25 + Reciprocal Rank Fusion ──────────────────

def retrieve_context_hybrid(query: str, subject: str = None,
                             n_results: int = 5,
                             al_subject: str = None) -> tuple:
    """
    Hybrid BM25 + dense retrieval with Reciprocal Rank Fusion (C=60).
    Research: ~49% reduction in retrieval failures vs dense-only.
    Falls back to pure dense when BM25 index is unavailable.
    Returns: (context: str, sources: list)
    """
    # Dense retrieval (existing ChromaDB path)
    dense_context, sources = retrieve_context(
        query, subject=subject, n_results=20, al_subject=al_subject
    )
    dense_docs = [d for d in dense_context.split("\n---\n") if d.strip()] if dense_context else []

    # Sparse BM25 retrieval
    sparse_docs: list = []
    if _BM25_AVAILABLE and _bm25_index and _bm25_docs:
        try:
            scores = _bm25_index.get_scores(query.lower().split())
            top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:20]
            sparse_docs = [_bm25_docs[i] for i in top_idx]
        except Exception:
            sparse_docs = []

    if not sparse_docs:
        # Pure dense fallback: just trim to n_results
        top_docs = dense_docs[:n_results]
    else:
        # Reciprocal Rank Fusion (C=60 per Cormack et al.)
        def _rrf(rank: int, C: int = 60) -> float:
            return 1.0 / (C + rank + 1)

        doc_scores: dict = {}
        for rank, doc in enumerate(dense_docs):
            doc_scores[doc] = doc_scores.get(doc, 0.0) + _rrf(rank)
        for rank, doc in enumerate(sparse_docs):
            doc_scores[doc] = doc_scores.get(doc, 0.0) + _rrf(rank)

        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        top_docs = [doc for doc, _ in ranked[:n_results]]

    context = "\n---\n".join(top_docs)
    return context, sources


# ── Confidence scoring ────────────────────────────────────────────────────────

def get_confidence_score(query: str, response: str,
                          sources: list,
                          top_reranker_score: float = 0.5) -> str:
    """
    3-band confidence: 'grounded' | 'curriculum' | 'uncertain'
    Research: MetaRAG/HALT-RAG 2025 threshold guidance.
    """
    if not sources:
        return "uncertain"

    # N-gram grounding: fraction of response tokens that appear in source text
    resp_tokens = set(response.lower().split())
    src_tokens = set(" ".join(str(s) for s in sources).lower().split())
    grounding = len(resp_tokens & src_tokens) / max(1, len(resp_tokens))

    if top_reranker_score > 0.6 and grounding > 0.4:
        return "grounded"
    elif top_reranker_score > 0.2 or grounding > 0.2:
        return "curriculum"
    else:
        return "uncertain"
