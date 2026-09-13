import pytest
from test_retrieval import bundle  # noqa: F401

from mobile_rag.retrieval import build_index, digest
from mobile_rag.retrieval_enhanced import EnhancedRetriever, build_enhanced, fuse


def test_rrf_deduplicates_and_breaks_ties():
    ids, scores, evidence = fuse({"a": ["x", "x", "y"], "b": ["y", "x"]})
    assert ids == ["x", "y"]
    assert scores["x"] == pytest.approx(1 / 61 + 1 / 62)
    assert evidence["y"] == {"a": 2, "b": 1}


def test_enhancements_preserve_evidence_and_inputs(bundle):  # noqa: F811
    root, folder = bundle
    base = build_index(folder, root / "base")
    out = build_enhanced(base, root / "enhanced")
    before = digest(out / "passage.sqlite")
    with EnhancedRetriever(out) as retriever:
        result = retriever.search("What should I remember about uniquealpha apple?")
        assert result["focused_terms"] == ["uniquealpha", "apple"]
        assert {"focused", "phrase", "proximity", "passages"} <= result["branches"].keys()
        hit = result["hits"][0]
        assert hit["citation"]["source_passage_ids"] == hit["chunk"]["body_passage_ids"]
        assert hit["matched_passage_id"] in hit["chunk"]["body_passage_ids"]
        qualifiers = retriever.search("not under 5 years without oxygen")
        assert qualifiers["focused_terms"] == ["not", "under", "5", "years", "without", "oxygen"]
        assert "aliases" in retriever.search("CPAP")["branches"]
        assert "aliases" not in retriever.search("CPAP", disabled=("aliases",))["branches"]
        assert retriever.search("!!!")["status"] == "invalid_query"
        assert retriever.search("apple", top_k=True)["status"] == "invalid_query"
        assert retriever.search('" OR * : ( ) NOT apple')["status"] == "ok"
        assert retriever.search("mg")["hits"][0]["chunk"]["retrieval_text"].count("| mg | 12 |") == 150
    assert digest(out / "passage.sqlite") == before
    with (out / "passage.sqlite").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="integrity"):
        EnhancedRetriever(out)
