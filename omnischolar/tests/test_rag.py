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
        lambda texts: [[float(len(t) % 7), float(t.count("e")), 1.0] for t in texts],
    )
    try:
        rag.client.delete_collection("study_materials")
    except Exception:
        pass  # first test: nothing to delete
    rag._bm25_index = None


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
