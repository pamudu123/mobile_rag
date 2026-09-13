import json

import numpy as np
import pytest
from test_retrieval import bundle  # noqa: F401

from mobile_rag.context_preparation import prepare_context
from mobile_rag.retrieval import build_index
from mobile_rag.retrieval_enhanced import build_enhanced
from mobile_rag.retrieval_hybrid import HybridRetriever, RetrievalConfig, build_dense


class FakeEncoder:
    def __init__(self):
        self.identity = {"model": "test-only", "dimensions": 384}

    def windows(self, text):
        yield text, 0, len(text)

    def encode(self, texts, *, query=False):
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        for i, text in enumerate(texts):
            vectors[i, 0 if "uniquealpha" in text or "semanticmissingword" in text else 1] = 1
        return vectors


@pytest.fixture
def hybrid_bundle(bundle):  # noqa: F811
    root, chunks = bundle
    lexical = build_enhanced(build_index(chunks, root / "base"), root / "lexical")
    encoder = FakeEncoder()
    return lexical, build_dense(lexical, root / "dense", encoder=encoder), encoder


def test_dense_finds_evidence_without_any_lexical_match(hybrid_bundle):
    _, path, encoder = hybrid_bundle
    with HybridRetriever(path, encoder=encoder) as r:
        result = r.search("semanticmissingword")
        assert result["branches"]["bm25"] == []
        assert result["branches"]["embeddings"]
        assert "uniquealpha" in result["hits"][0]["chunk"]["retrieval_text"]
        assert result["hits"][0]["branch_ranks"] == {"embeddings": 1}
        assert result["question"] == "semanticmissingword"
        assert prepare_context(r, result, r.expand(result))["status"] == "ready"


def test_switches_disable_execution_and_missing_assets_fail_closed(hybrid_bundle, monkeypatch):
    lexical, path, encoder = hybrid_bundle

    def unexpected(*args, **kwargs):
        raise AssertionError("Disabled path executed")

    monkeypatch.setattr("mobile_rag.retrieval_hybrid.get_encoder", unexpected)
    with HybridRetriever(lexical, RetrievalConfig(enable_embeddings=False)) as r:
        assert set(r.search("uniquealpha")["branches"]) == {"bm25"}
    with pytest.raises(ValueError, match="dense index missing"):
        HybridRetriever(lexical)
    monkeypatch.setattr("mobile_rag.retrieval_hybrid.EnhancedRetriever", unexpected)
    with HybridRetriever(path, RetrievalConfig(enable_bm25=False), encoder=encoder) as r:
        assert set(r.search("uniquealpha")["branches"]) == {"embeddings"}


def test_configuration_and_filtering(hybrid_bundle):
    _, path, encoder = hybrid_bundle
    for config in (RetrievalConfig(False, False), RetrievalConfig(1, True), RetrievalConfig(candidate_limit=0)):
        with pytest.raises(ValueError):
            config.validate()
    with HybridRetriever(path, encoder=encoder) as r:
        first = r.search("uniquealpha")
        doc = first["hits"][0]["document"]["document_id"]
        filtered = r.search("uniquealpha", document_id=doc)
        assert all(h["document"]["document_id"] == doc for h in filtered["hits"])
        assert r.search("uniquealpha", document_id="missing")["status"] == "invalid_query"
        assert r.search("!!!")["status"] == "invalid_query"
        assert r.search("apple", top_k=True)["status"] == "invalid_query"
        assert len({h["chunk"]["chunk_id"] for h in first["hits"]}) == len(first["hits"])
        assert first["hits"] == r.search("uniquealpha")["hits"]


def test_dense_tampering_and_encoder_mismatch(hybrid_bundle):
    _, path, encoder = hybrid_bundle
    changed = FakeEncoder()
    changed.identity = {"model": "different"}
    with pytest.raises(ValueError, match="encoder differs"):
        HybridRetriever(path, encoder=changed)
    units = path / "embedding_units.json"
    units.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        HybridRetriever(path, encoder=encoder)


def test_saved_embeddings_are_reused_on_reopen(hybrid_bundle):
    _, path, _ = hybrid_bundle

    class QueryOnlyEncoder(FakeEncoder):
        def windows(self, text):
            raise AssertionError("Query-time retrieval must not rebuild document windows")

        def encode(self, texts, *, query=False):
            assert query, "Query-time retrieval must not re-embed documents"
            return super().encode(texts, query=query)

    for _ in range(2):
        with HybridRetriever(path, RetrievalConfig(False, True), encoder=QueryOnlyEncoder()) as r:
            assert r.search("semanticmissingword")["hits"]
