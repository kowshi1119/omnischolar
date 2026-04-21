import chromadb
import fitz
import ollama

client = chromadb.PersistentClient("./study_db")


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
        result = ollama.embeddings(model="nomic-embed-text", prompt=chunk)
        embeddings.append(result["embedding"])

    if chunks:
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
    return len(chunks)


def retrieve_context(query, subject=None, n_results=4, al_subject=None):
    collection = get_collection()
    result = ollama.embeddings(model="nomic-embed-text", prompt=query)
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
