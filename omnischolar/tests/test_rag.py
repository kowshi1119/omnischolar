import io

import fitz
import pytest

import rag


def _pdf(text: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


class _Upload(io.BytesIO):
    """Mimics Streamlit's UploadedFile (file-like with a .name)."""

    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    # Deterministic 3-d vectors so no Ollama is needed
    monkeypatch.setattr(
        rag, "_embed",
        lambda texts, **kw: [[float(len(t) % 7), float(t.count("e")), 1.0] for t in texts],
    )
    for name in {rag._LEGACY_COLLECTION, rag._collection_name(rag._EMBED_MODEL)}:
        try:
            rag.client.delete_collection(name)
        except Exception:
            pass  # nothing to delete yet
    rag._bm25_index = None
    rag._migrated = False


def test_two_uploads_same_subject_are_both_indexed():
    a = _Upload(_pdf("Photosynthesis converts light energy into chemical energy " * 3), "bio1.pdf")
    b = _Upload(_pdf("Mitochondria are the site of aerobic respiration in cells " * 3), "bio2.pdf")
    assert rag.ingest_pdf(a, "Biology", "English") > 0
    assert rag.ingest_pdf(b, "Biology", "English") > 0
    sources = {m["source"] for m in rag.get_collection().get()["metadatas"]}
    assert sources == {"bio1.pdf", "bio2.pdf"}


def test_reupload_is_idempotent():
    data = _pdf("Newton's second law states force equals mass times acceleration " * 3)
    n = rag.ingest_pdf(_Upload(data, "phy.pdf"), "Physics", "English")
    rag.ingest_pdf(_Upload(data, "phy.pdf"), "Physics", "English")
    assert rag.get_collection().count() == n


def test_hybrid_respects_subject_and_rebuilds_bm25_after_restart():
    rag.ingest_pdf(_Upload(_pdf("enzymes catalyse reactions in living cells " * 3), "b.pdf"), "Biology", "English")
    rag.ingest_pdf(_Upload(_pdf("enzymes appear in this chemistry kinetics text " * 3), "c.pdf"), "Chemistry", "English")
    rag._bm25_index = None  # simulate an app restart
    context, sources = rag.retrieve_context_hybrid("enzymes", subject="Biology")
    assert rag._bm25_index is not None
    assert sources == ["b.pdf page 1"]
    assert "chemistry" not in context


def test_confidence_uses_context_text():
    ctx = "photosynthesis converts light energy into chemical energy"
    assert rag.get_confidence_score("q", ctx, ["x.pdf page 1"], top_reranker_score=0.7, context=ctx) == "grounded"


def test_legacy_nomic_index_is_reembedded_for_new_model(monkeypatch):
    monkeypatch.setattr(rag, "_EMBED_MODEL", "nomic-embed-text")
    rag.ingest_pdf(_Upload(_pdf("Osmosis moves water across a membrane " * 3), "old.pdf"), "Biology", "English")
    legacy_count = rag.get_collection().count()

    monkeypatch.setattr(rag, "_EMBED_MODEL", "embeddinggemma")
    rag._migrated = False
    new = rag.get_collection()
    assert new.name != rag._LEGACY_COLLECTION
    assert new.count() == legacy_count
    assert {m["source"] for m in new.get()["metadatas"]} == {"old.pdf"}
    try:
        rag.client.delete_collection(new.name)
    except Exception:
        pass


def test_context_is_labelled_with_source_page():
    rag.ingest_pdf(_Upload(_pdf("Mitosis produces two identical daughter cells " * 3), "cells.pdf"), "Biology", "English")
    context, _ = rag.retrieve_context_hybrid("mitosis", subject="Biology")
    assert context.startswith("[cells.pdf page 1]")


def test_confidence_counts_a_correct_citation():
    ctx = "[bio.pdf page 3]\nThe Calvin cycle takes place in the stroma of the chloroplast."
    answer = "The Calvin cycle takes place in the stroma. FROM YOUR MATERIAL: [bio.pdf page 3]"
    assert rag.get_confidence_score("q", answer, ["bio.pdf page 3"], context=ctx) == "grounded"
    uncited = "Glycolysis happens in the cytoplasm of every living cell."
    assert rag.get_confidence_score("q", uncited, ["bio.pdf page 3"], context=ctx) != "grounded"
