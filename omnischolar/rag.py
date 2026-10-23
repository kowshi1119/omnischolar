import hashlib
import os
import re

import chromadb
import fitz
import ollama

from config import CHROMA_DB_PATH, OLLAMA_EMBED_MODEL, OLLAMA_HOST

client = chromadb.PersistentClient(CHROMA_DB_PATH)
_ollama = ollama.Client(host=OLLAMA_HOST)

# ── Embedding model ───────────────────────────────────────────────────────────
# embeddinggemma is multilingual (100+ languages incl. Sinhala/Tamil);
# nomic-embed-text is English-only and kept for existing indexes.
_EMBED_MODEL = OLLAMA_EMBED_MODEL
_LEGACY_COLLECTION = "study_materials"  # nomic-embed-text index from earlier versions
_migrated = False

# ── BM25 sparse index (built lazily from the collection, rebuilt on ingestion) ─
_bm25_index = None
_bm25_docs: list = []
_bm25_metas: list = []

try:
    from rank_bm25 import BM25Okapi as _BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    _BM25Okapi = None


def _collection_name(model: str) -> str:
    # Vectors from different models aren't comparable, so each model gets its own collection
    if model.startswith("nomic-embed-text"):
        return _LEGACY_COLLECTION
    return "study_materials_" + re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_")


def get_collection():
    collection = client.get_or_create_collection(
        name=_collection_name(_EMBED_MODEL),
        metadata={"hnsw:space": "cosine"},
    )
    _migrate_legacy(collection)
    return collection


def _migrate_legacy(collection) -> None:
    """Re-embed chunks from the old nomic index into the current model's collection.

    Chroma stores the chunk text, so students don't have to re-upload their PDFs.
    """
    global _migrated
    if _migrated or collection.name == _LEGACY_COLLECTION:
        return
    _migrated = True
    try:
        legacy = client.get_collection(_LEGACY_COLLECTION)
    except Exception:
        return  # no old index
    if collection.count() or not legacy.count():
        return
    data = legacy.get(include=["documents", "metadatas"])
    for i in range(0, len(data["ids"]), 32):
        docs, metas = data["documents"][i:i + 32], data["metadatas"][i:i + 32]
        collection.upsert(
            ids=data["ids"][i:i + 32], documents=docs, metadatas=metas,
            embeddings=_embed(docs, titles=[m.get("source", "") for m in metas]),
        )


def _embed(texts: list, kind: str = "document", titles: list = None) -> list:
    """Embed a batch of texts in one Ollama call, with the model's task prompt."""
    if not texts:
        return []
    if _EMBED_MODEL.startswith("embeddinggemma"):
        # Prompt formats from the EmbeddingGemma model card
        if kind == "query":
            texts = [f"task: search result | query: {t}" for t in texts]
        else:
            titles = titles or ["none"] * len(texts)
            texts = [f"title: {title or 'none'} | text: {t}" for title, t in zip(titles, texts)]
    return list(_ollama.embed(model=_EMBED_MODEL, input=texts)["embeddings"])


def ingest_pdf(pdf, subject, language, al_stream=None, al_subject=None):
    """Index a PDF into ChromaDB.

    `pdf` may be a path, raw bytes, or a file-like object (e.g. Streamlit's
    UploadedFile). Re-uploading the same file is idempotent (content-hashed IDs).
    """
    if isinstance(pdf, (str, os.PathLike)):
        with open(pdf, "rb") as fh:
            data = fh.read()
        source = os.path.basename(str(pdf))
    elif isinstance(pdf, (bytes, bytearray)):
        data, source = bytes(pdf), "document.pdf"
    else:
        data = pdf.getvalue() if hasattr(pdf, "getvalue") else pdf.read()
        source = getattr(pdf, "name", "document.pdf")

    file_id = hashlib.sha1(data).hexdigest()[:12]
    collection = get_collection()
    chunks, metadatas, ids = [], [], []

    with fitz.open(stream=data, filetype="pdf") as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text()
            for i in range(0, len(text), 700):
                chunk = text[i : i + 800].strip()
                if len(chunk) > 50:
                    chunks.append(chunk)
                    meta = {
                        "page": page_num + 1,
                        "subject": subject,
                        "language": language,
                        "source": source,
                    }
                    if al_stream:
                        meta["al_stream"] = al_stream
                    if al_subject:
                        meta["al_subject"] = al_subject
                    metadatas.append(meta)
                    ids.append(f"{file_id}_{page_num}_{i}")

    if chunks:
        collection.upsert(
            documents=chunks,
            embeddings=_embed(chunks, titles=[source] * len(chunks)),
            metadatas=metadatas,
            ids=ids,
        )
        _rebuild_bm25(collection)
    return len(chunks)


def retrieve_context(query, subject=None, n_results=4, al_subject=None):
    collection = get_collection()
    query_embedding = _embed([query], kind="query")[0]
    # Build filter: prefer al_subject filter for A/L students, fall back to subject
    if al_subject:
        where = {"al_subject": al_subject}
    elif subject:
        where = {"subject": subject}
    else:
        where = None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )
    if not results["documents"] or not results["documents"][0]:
        return "", []

    sources = [_source_label(m) for m in results["metadatas"][0]]
    context = "\n---\n".join(f"[{s}]\n{d}" for s, d in zip(sources, results["documents"][0]))
    return context, list(dict.fromkeys(sources))


def get_retrieval_coverage(subject: str = None) -> dict:
    """Return basic coverage stats for the study_materials collection."""
    try:
        col = get_collection()
        total = col.count()
        return {"total_chunks": total, "subject": subject or "all"}
    except Exception:
        return {"total_chunks": 0, "subject": subject or "all"}


# ── BM25 sparse index ─────────────────────────────────────────────────────────

def build_bm25_index(texts: list, metas: list = None) -> None:
    """Build (or rebuild) in-memory BM25 index from document chunks."""
    global _bm25_index, _bm25_docs, _bm25_metas
    if not _BM25_AVAILABLE or not texts:
        return
    _bm25_docs = list(texts)
    _bm25_metas = list(metas) if metas else [{} for _ in _bm25_docs]
    tokenized = [t.lower().split() for t in _bm25_docs]
    _bm25_index = _BM25Okapi(tokenized)


def _rebuild_bm25(collection=None) -> None:
    try:
        data = (collection or get_collection()).get(include=["documents", "metadatas"])
        build_bm25_index(data["documents"], data["metadatas"])
    except Exception:
        pass


def _source_label(meta: dict) -> str:
    return f"{meta.get('source', 'document')} page {meta.get('page', '?')}"


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
    collection = get_collection()
    if collection.count() == 0:
        return "", []
    where = {"al_subject": al_subject} if al_subject else {"subject": subject} if subject else None
    dense = collection.query(
        query_embeddings=[_embed([query], kind="query")[0]],
        n_results=min(20, collection.count()),
        where=where,
    )
    dense_docs = dense["documents"][0] if dense["documents"] else []
    label = {d: _source_label(m) for d, m in zip(dense_docs, dense["metadatas"][0] if dense_docs else [])}

    # Sparse BM25 retrieval — index is in memory, so rebuild it after a restart
    if _BM25_AVAILABLE and _bm25_index is None:
        _rebuild_bm25(collection)
    sparse_docs: list = []
    if _BM25_AVAILABLE and _bm25_index is not None and _bm25_docs:
        try:
            scores = _bm25_index.get_scores(query.lower().split())
            ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            for i in ranked_idx:
                meta = _bm25_metas[i] or {}
                if where and any(meta.get(k) != v for k, v in where.items()):
                    continue
                sparse_docs.append(_bm25_docs[i])
                label.setdefault(_bm25_docs[i], _source_label(meta))
                if len(sparse_docs) == 20:
                    break
        except Exception:
            sparse_docs = []

    if not sparse_docs:
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

    # Each chunk carries its [file page N] label so the model can cite it
    context = "\n---\n".join(f"[{label[d]}]\n{d}" for d in top_docs)
    sources = list(dict.fromkeys(label[d] for d in top_docs))
    return context, sources


# ── Confidence scoring ────────────────────────────────────────────────────────

def get_confidence_score(query: str, response: str,
                          sources: list,
                          top_reranker_score: float = 0.5,
                          context: str = "") -> str:
    """
    3-band confidence: 'grounded' | 'curriculum' | 'uncertain'
    Research: MetaRAG/HALT-RAG 2025 threshold guidance.
    """
    if not sources:
        return "uncertain"

    # N-gram grounding: fraction of response tokens that appear in source text
    resp_tokens = set(response.lower().split())
    src_tokens = set((context or " ".join(str(s) for s in sources)).lower().split())
    grounding = len(resp_tokens & src_tokens) / max(1, len(resp_tokens))

    if top_reranker_score > 0.6 and grounding > 0.4:
        return "grounded"
    elif top_reranker_score > 0.2 or grounding > 0.2:
        return "curriculum"
    else:
        return "uncertain"
