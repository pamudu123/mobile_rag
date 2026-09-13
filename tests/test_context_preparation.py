from copy import deepcopy

import pytest
from test_retrieval import bundle  # noqa: F401

from mobile_rag.context_preparation import ContextBudget, prepare_context
from mobile_rag.retrieval import Retriever, build_index


def test_packing_contract(bundle):  # noqa: F811
    root, folder = bundle
    index = build_index(folder, root / "indexes")
    with Retriever(index) as retriever:
        result = retriever.search("uniquealpha")
        expansion = retriever.expand(result)
        budget = ContextBudget(100000, 0, 0)
        packed = prepare_context(retriever, result, expansion, budget)
        assert packed["status"] == "ready"
        assert packed == prepare_context(retriever, result, expansion, budget)
        assert packed["diagnostics"]["duplicate_passages_removed"] > 0
        owners = {}
        for group in packed["evidence_groups"]:
            original = {p["passage_id"]: p for p in retriever.resolve(group["chunk_id"])["passages"]}
            assert group["label"] in packed["citation_map"]
            for entry in group["source_passages"]:
                key = (group["document_id"], entry["passage_id"])
                if "text" in entry:
                    assert key not in owners
                    assert entry["text"] == original[entry["passage_id"]]["text"]
                    owners[key] = group["label"]
                else:
                    assert owners[key] == entry["reference"]
        table = prepare_context(retriever, retriever.search("mg"), budget=budget)
        assert table["context_text"].count("| mg | 12 |") == 150
        size = len(table["context_text"]) + len(table["question"])
        assert prepare_context(retriever, retriever.search("mg"), budget=ContextBudget(size, 0, 0))["status"] == "ready"
        assert (
            prepare_context(retriever, retriever.search("mg"), budget=ContextBudget(size - 1, 0, 0))["status"]
            == "budget_blocked"
        )
        duplicate = deepcopy(result)
        duplicate["hits"] *= 2
        doubled = prepare_context(retriever, duplicate, budget=budget)
        assert len(doubled["evidence_groups"]) == 1
        assert doubled["excluded_evidence"][0]["reason"] == "duplicate_chunk"
        same_text = prepare_context(retriever, retriever.search("apple"), budget=budget)
        assert len({g["document_id"] for g in same_text["evidence_groups"]}) == 2
        assert prepare_context(retriever, retriever.search("nonexistentxyz"))["status"] == "empty"
        assert prepare_context(retriever, retriever.search("!!!"))["status"] == "invalid_evidence"
        for mutation in ("text", "identity", "citation"):
            bad = deepcopy(result)
            if mutation == "text":
                bad["hits"][0]["passages"][0]["text"] = "invented"
            elif mutation == "identity":
                bad["bundle_identity"] = "other"
            else:
                bad["hits"][0]["citation"]["source_passage_ids"] = []
            rejected = prepare_context(retriever, bad)
            assert rejected["status"] == "invalid_evidence"
            assert not rejected["context_text"]
        with pytest.raises(ValueError):
            prepare_context(retriever, result, budget=ContextBudget(-1))


def test_full_request_budget_accounts_for_prompt_growth(bundle, monkeypatch):  # noqa: F811
    import json

    from mobile_rag import answer_generation as generation

    root, folder = bundle
    config = generation.GenerationConfig(model="test/" + "x" * 100)
    with Retriever(build_index(folder, root / "indexes")) as retriever:
        result = retriever.search("uniquealpha")
        packed = prepare_context(retriever, result, generation_config=config)
        assert generation.generate_answer(packed, config=config)["status"] == "dry_run"
        exact = len(json.dumps(generation.make_request(packed, config), ensure_ascii=False))
        budget = ContextBudget(exact + 4000, 1, 4000)
        fitted = prepare_context(retriever, result, budget=budget, generation_config=config)
        assert generation.generate_answer(fitted, config=config)["status"] == "dry_run"
        monkeypatch.setattr(generation, "INSTRUCTIONS", generation.INSTRUCTIONS + "x" * budget.total_chars)
        blocked = prepare_context(retriever, result, budget=budget, generation_config=config)
        assert blocked["status"] == "budget_blocked"
        assert not blocked["evidence_groups"]
