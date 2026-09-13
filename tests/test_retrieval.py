import json
import re

import pytest

from mobile_rag.corpus import build_chunks, build_inventory, export_chunks, export_inventory
from mobile_rag.retrieval import Retriever, build_index, digest, load_bundle, new_run_dir


@pytest.fixture
def bundle(tmp_path):
    (tmp_path / "data/pdf_docs").mkdir(parents=True)
    md = tmp_path / "data/md_docs"
    md.mkdir()
    (md / "a.md").write_text(
        "# Shared\n\nuniquealpha apple\n\n" + "longcontext " * 120 + "\n\n## Other\n\nbanana\n", encoding="utf-8"
    )
    (md / "b.md").write_text(
        "# Shared\n\napple\n\n### Table\n\n| unit | value |\n| --- | --- |\n" + "| mg | 12 |\n" * 150, encoding="utf-8"
    )
    inv = export_inventory(build_inventory(tmp_path), tmp_path, output_root=tmp_path / "inventory_exports")
    output = export_chunks(
        build_chunks(tmp_path, inv / "corpus_manifest.json"), tmp_path, output_root=tmp_path / "chunk_exports"
    )
    return tmp_path, output


def test_search_readonly_provenance_and_query_safety(bundle):
    root, folder = bundle
    out = build_index(folder, root / "indexes")
    before = digest(out / "retrieval.sqlite")
    with Retriever(out) as retriever:
        hit = retriever.search("uniquealpha")["hits"][0]
        assert "uniquealpha" in hit["chunk"]["retrieval_text"]
        assert hit["citation"]["source_passage_ids"] == hit["chunk"]["body_passage_ids"]
        assert retriever.search("uniquealpha banana", mode="AND")["status"] == "no_matches"
        assert retriever.search("uniquealpha banana", mode="OR")["status"] == "ok"
        assert retriever.search('" OR * : ( ) NOT apple')["status"] in {"ok", "no_matches"}
        assert retriever.search("!!!")["status"] == "invalid_query"
        assert retriever.search("x" * 2001)["status"] == "invalid_query"
        assert retriever.search(" ".join(f"t{i}" for i in range(65)))["status"] == "invalid_query"
        assert retriever.search("unfindableword")["status"] == "no_matches"
        assert retriever.search("apple", document_id="absent")["status"] == "invalid_query"
        assert retriever.search("apple", top_k=True)["status"] == "invalid_query"
        doc_id = hit["chunk"]["document_id"]
        assert all(h["chunk"]["document_id"] == doc_id for h in retriever.search("apple", document_id=doc_id)["hits"])
        expanded = retriever.expand(retriever.search("uniquealpha"))
        assert any("longcontext" in h["chunk"]["retrieval_text"] for h in expanded["neighbors"])
        assert not retriever.expand(retriever.search("uniquealpha"), 0)["neighbors"]
        table = retriever.search("mg")["hits"][0]
        assert table["chunk"]["retrieval_text"].count("| mg | 12 |") == 150
    assert digest(out / "retrieval.sqlite") == before
    # Stored evidence does not need any source files at query time.
    isolated = root / "isolated"
    isolated.mkdir()
    for name in ("index_manifest.json", "retrieval.sqlite"):
        (isolated / name).write_bytes((out / name).read_bytes())
    with Retriever(isolated) as retriever:
        assert retriever.search("uniquealpha")["hits"][0]["passages"]


def test_new_run_dir_uses_compact_timestamp(tmp_path):
    first, second = new_run_dir(tmp_path), new_run_dir(tmp_path)
    assert re.fullmatch(r"\d{8}_\d{6}", first.name)
    assert re.fullmatch(r"\d{8}_\d{6}(?:_\d+)?", second.name)
    assert first != second


def test_rebuild_deterministic_and_tampering_rejected(bundle):
    root, folder = bundle
    first, second = build_index(folder, root / "indexes"), build_index(folder, root / "indexes")
    with Retriever(first) as a, Retriever(second) as b:
        ar, br = a.search("apple"), b.search("apple")
        assert [(h["chunk"]["chunk_id"], h["raw_bm25"]) for h in ar["hits"]] == [
            (h["chunk"]["chunk_id"], h["raw_bm25"]) for h in br["hits"]
        ]
    path = folder / "chunks.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        load_bundle(folder)
    manifest = first / "index_manifest.json"
    value = json.loads(manifest.read_text())
    value["database_sha256"] = "incorrect"
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="integrity"):
        Retriever(first)


def test_unicode_jsonl_and_equal_score_ties(tmp_path):
    (tmp_path / "data/pdf_docs").mkdir(parents=True)
    md = tmp_path / "data/md_docs"
    md.mkdir()
    for name, word in (("a", "red"), ("b", "tan")):
        (md / f"{name}.md").write_text(f"# Same\n\napple café\u2028{word}\n", encoding="utf-8")
    inv = export_inventory(build_inventory(tmp_path), tmp_path, output_root=tmp_path / "inventory_exports")
    folder = export_chunks(
        build_chunks(tmp_path, inv / "corpus_manifest.json"), tmp_path, output_root=tmp_path / "chunk_exports"
    )
    out = build_index(folder, tmp_path / "indexes")
    with Retriever(out) as retriever:
        hits = retriever.search("café")["hits"]
        assert len(hits) == 2
        assert hits[0]["raw_bm25"] == hits[1]["raw_bm25"]
        ids = [h["chunk"]["chunk_id"] for h in hits]
        assert ids == sorted(ids)
        source_tail = (md / "a.md").read_bytes().decode("utf-8").split("\u2028")[1]
        assert retriever.search("red")["hits"][0]["chunk"]["retrieval_text"].endswith(source_tail)


def test_rehashed_but_invalid_citation_rejected(bundle):
    _, folder = bundle
    path = folder / "citation_targets.jsonl"
    values = [json.loads(line) for line in path.read_text().split("\n") if line.strip()]
    values[0]["source_passage_ids"] = ["invented"]
    path.write_text("\n".join(json.dumps(v) for v in values) + "\n")
    manifest_path = folder / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["output_sha256"][path.name] = digest(path)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Citation/source"):
        load_bundle(folder)
