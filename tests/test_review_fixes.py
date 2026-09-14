import json
import shutil
import sqlite3
import subprocess
import sys
from copy import deepcopy

import pymupdf
import pytest
from test_retrieval import bundle  # noqa: F401

from mobile_rag.answer_generation import GenerationConfig, generation_identity
from mobile_rag.bulk_answer_generation import RESUME_KEYS, validate_checkpoint, validate_resume
from mobile_rag.corpus import build_chunks, build_inventory, export_chunks, validate_inventory
from mobile_rag.evaluation import evaluate_records
from mobile_rag.retrieval import Retriever, artifact_order, build_index, digest, latest_bundle, load_bundle
from mobile_rag.retrieval_enhanced import EnhancedRetriever, build_enhanced


def test_package_entrypoint():
    result = subprocess.run([sys.executable, "-m", "mobile_rag", "--help"], capture_output=True, text=True, check=False)
    assert result.returncode == 0 and "evaluate" in result.stdout


def test_conflicting_transcriptions_fail_before_export(tmp_path):
    pdf = tmp_path / "data/pdf_docs"
    md = tmp_path / "data/md_docs"
    pdf.mkdir(parents=True)
    md.mkdir()
    with pymupdf.open() as document:
        document.new_page()
        document.save(pdf / "Guide.pdf")
    for name in ("a", "b"):
        (md / f"{name}.md").write_text(f"# {name}\n\n| Source | `Guide.pdf` |\n\n{name} advice.", encoding="utf-8")
    inventory = build_inventory(tmp_path)
    assert not validate_inventory(inventory)["passed"]
    assert inventory["run"]["technical_status"] == "failed"
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(inventory), encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        build_chunks(tmp_path, path)
    # Same-content aliases remain allowed.
    (md / "b.md").write_bytes((md / "a.md").read_bytes())
    assert validate_inventory(build_inventory(tmp_path))["passed"]
    (pdf / "Guide.pdf").write_bytes(b"not a pdf")
    assert not validate_inventory(build_inventory(tmp_path))["passed"]


def test_duplicate_documents_cannot_be_exported(bundle):  # noqa: F811
    root, path = bundle
    data = load_bundle(path)
    content = {**data["manifest"], **{name: data[name] for name in ("documents", "passages", "chunks")}}
    content["documents"].append(deepcopy(content["documents"][0]))
    output = root / "must_not_exist"
    with pytest.raises(ValueError, match="unique_document_ids"):
        export_chunks(content, root, output_root=output)
    assert not output.exists()


def test_partial_constructors_close_connections(bundle, monkeypatch):  # noqa: F811
    root, path = bundle
    index = build_enhanced(build_index(path, root / "base"), root / "enhanced")
    original = sqlite3.connect
    opened = []

    def connect(database, *args, **kwargs):
        if "passage.sqlite" in str(database):
            raise sqlite3.OperationalError("Injected passage open failure")
        connection = original(database, *args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)
    with pytest.raises(sqlite3.OperationalError):
        EnhancedRetriever(index)
    assert len(opened) == 2
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")
    # An earlier failure while opening the base tokenizer also closes the base DB.
    opened.clear()

    def fail_scratch(database, *args, **kwargs):
        if database == ":memory:":
            raise sqlite3.OperationalError("Injected scratch open failure")
        return connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", fail_scratch)
    with pytest.raises(sqlite3.OperationalError):
        Retriever(index)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")


def test_passage_filter_precedes_limit(bundle):  # noqa: F811
    root, path = bundle
    index = build_enhanced(build_index(path, root / "base"), root / "enhanced")
    with Retriever(index) as retriever:
        target = retriever.search("uniquealpha")["hits"][0]["chunk"]
        other = next(json.loads(value) for (value,) in retriever.db.execute("SELECT value FROM chunks")
                     if json.loads(value)["document_id"] != target["document_id"])
    db = sqlite3.connect(index / "passage.sqlite")
    with db:
        db.execute("DELETE FROM units")
        db.executemany("INSERT INTO units VALUES (?,?,?,?)",
                       [("", "needle", other["chunk_id"], f"fake{i}") for i in range(200)])
        db.execute("INSERT INTO units VALUES (?,?,?,?)",
                   ("", "needle " + "filler " * 100, target["chunk_id"], target["body_passage_ids"][0]))
    db.close()
    manifest_path = index / "enhancement_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["passage_database_sha256"] = digest(index / "passage.sqlite")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with EnhancedRetriever(index) as retriever:
        result = retriever.search("needle", document_id=target["document_id"])
        assert result["branches"]["passages"] == [target["chunk_id"]]
        assert result["hits"][0]["chunk"]["document_id"] == target["document_id"]


def test_resume_rejects_changed_request_and_legacy_identity():
    current = dict.fromkeys(RESUME_KEYS, "fixture")
    current["generation_identity"] = generation_identity(GenerationConfig())
    validate_resume(current, current)
    for patch in ({"model": "another/model"}, {"temperature": 0.7}, {"max_output_tokens": 99}, {"thinking": False}):
        changed = {**current, "generation_identity": generation_identity(GenerationConfig(**patch))}
        with pytest.raises(ValueError, match="generation_identity"):
            validate_resume(current, changed)
    legacy = {key: value for key, value in current.items() if key != "generation_identity"}
    with pytest.raises(ValueError):
        validate_resume(legacy, current)
    with pytest.raises(ValueError, match="Checkpoint"):
        validate_checkpoint({"dataset": "fixture", "benchmark_sha256": "fixture"}, current)


def test_evaluation_keeps_errors_distinct_and_requires_gold():
    rows = [
        {"record_key": "Q:1", "pipeline_status": "insufficient_evidence", "question_record": {"category": "Unanswerable"},
         "generation": {"answer": None}},
        {"record_key": "Q:2", "pipeline_status": "api_error", "question_record": {"category": "Unanswerable"}},
        {"record_key": "Q:3", "pipeline_status": "answered", "question_record": {"category": "Triage"},
         "retrieval": {"hits": [{"chunk": {"chunk_id": "gold"}}, {"chunk": {"chunk_id": "wrong"}}]},
         "context": {"evidence_groups": [{"chunk_id": "wrong"}]}},
    ]
    assert all(row["gold_evidence_metrics"] is None for row in evaluate_records(rows)["questions"])
    summary = evaluate_records(rows, annotations={"Q:3": {"relevant_chunk_ids": ["gold"]}})
    assert summary["unanswerable"] == {"count": 2, "abstentions": 1, "answered": 0, "technical_or_unexecuted": 1}
    metric = summary["questions"][2]["gold_evidence_metrics"]
    assert metric["retrieval_recall"] == 1 and metric["packed_precision"] == 0
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate_records(rows + rows)


def test_mixed_artifact_names_sort_by_time(tmp_path):
    newer = tmp_path / "20260913_140000" / "manifest.json"
    older = tmp_path / "20260913T130000000000Z" / "manifest.json"
    assert artifact_order(newer) > artifact_order(older)


def test_automatic_bundle_selection_rejects_changed_sources(bundle):  # noqa: F811
    root, folder = bundle
    target = root / "artifacts/02_markdown_chunking/20260913_140000"
    shutil.copytree(folder, target)
    assert latest_bundle(root) == target
    with (root / "data/md_docs/a.md").open("a", encoding="utf-8") as handle:
        handle.write("\nChanged source.\n")
    with pytest.raises(FileNotFoundError, match="current sources"):
        latest_bundle(root)
    # Explicit immutable snapshots are still readable for reproducing past runs.
    assert load_bundle(target)["chunks"]


def test_integrity_failure_is_explicit_under_optimized_python(bundle):  # noqa: F811
    root, folder = bundle
    index = build_index(folder, root / "base")
    script = '''
import sqlite3, sys
from pathlib import Path
from mobile_rag.retrieval_enhanced import build_enhanced
connect = sqlite3.connect
class BadIntegrity(sqlite3.Connection):
    def execute(self, sql, *args):
        if sql == "PRAGMA integrity_check":
            class Result:
                def fetchone(self): return ("injected corruption",)
            return Result()
        return super().execute(sql, *args)
def replacement(*args, **kwargs):
    return connect(*args, **kwargs, factory=BadIntegrity)
sqlite3.connect = replacement
try:
    build_enhanced(Path(sys.argv[1]), Path(sys.argv[2]))
except ValueError as error:
    if "integrity failed" in str(error):
        sys.exit(0)
    raise
sys.exit(1)
'''
    result = subprocess.run([sys.executable, "-O", "-c", script, str(index), str(root / "enhanced")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
