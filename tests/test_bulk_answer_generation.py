import json

from test_retrieval import bundle  # noqa: F401

from mobile_rag.answer_generation import GenerationConfig
from mobile_rag.bulk_answer_generation import (
    CONTEXTS_FILENAME,
    RESULTS_FILENAME,
    benchmark_identity,
    load_contexts,
    load_record_context,
    process_question,
    review_row,
    select_questions,
    write_record_context,
    write_results,
)
from mobile_rag.context_preparation import ContextBudget
from mobile_rag.retrieval import build_index
from mobile_rag.retrieval_enhanced import build_enhanced
from mobile_rag.retrieval_hybrid import RetrievalConfig


def test_benchmark_identity_and_dry_run_record(bundle, tmp_path):  # noqa: F811
    root, chunks = bundle
    question_path = tmp_path / "Q_TEST.json"
    question_path.write_text(
        '{"metadata":{"name":"fixture"},"questions":[{"id":1,"question":"uniquealpha",'
        '"answer":"reference-only","source_of_truth":"fixture"}]}',
        encoding="utf-8",
    )
    benchmark = benchmark_identity(question_path)
    index = build_enhanced(build_index(chunks, root / "base"), root / "enhanced")
    record = process_question(
        benchmark["questions"][0],
        dataset=benchmark["dataset"],
        benchmark_sha256=benchmark["sha256"],
        index_dir=index,
        live=False,
        generation_config=GenerationConfig(),
        context_budget=ContextBudget(),
        retrieval_config=RetrievalConfig(enable_embeddings=False),
    )
    assert record["record_key"] == "Q_TEST:1"
    assert record["question_record"]["answer"] == "reference-only"
    assert "reference-only" not in record["generation"]["request"]["messages"][0]["content"]
    assert record["pipeline_status"] == "dry_run"
    assert record["error"] is None
    assert record["retrieval"]["hits"] and record["context"]["status"] == "ready"

    contexts_by_key = {}
    compact = write_record_context(tmp_path, record, contexts_by_key)
    saved = load_record_context(tmp_path, compact, contexts_by_key)
    assert compact["context_path"] == CONTEXTS_FILENAME
    assert compact["context_key"] == "Q_TEST:1"
    assert "context_text" not in compact["context"]
    assert saved["context_text"] == record["context"]["context_text"]
    assert saved["evidence_groups"][0]["source_passages"][0]["text"]


def test_duplicate_question_ids_rejected(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text('{"questions":[{"id":1,"question":"a"},{"id":1,"question":"b"}]}', encoding="utf-8")
    try:
        benchmark_identity(path)
    except ValueError as error:
        assert "unique" in str(error)
    else:
        raise AssertionError("Duplicate IDs were accepted")


def test_question_count_selection():
    rows = [{"id": value} for value in range(5)]
    assert select_questions(rows, None) == rows
    assert select_questions(rows, 2) == rows[:2]
    assert select_questions(rows, 99) == rows
    for invalid in (0, -1, True, "2"):
        try:
            select_questions(rows, invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid selection accepted: {invalid!r}")


def test_contexts_and_results_saved_as_combined_json(tmp_path):
    first = {
        "record_key": "Q_S1:1",
        "pipeline_status": "answered",
        "question_record": {
            "id": 1,
            "question": "Emergency triage signs?",
            "answer": "Treat emergency signs immediately.",
            "source_of_truth": "WHO Pocket Book",
            "category": "Triage",
            "topic": "Emergency triage signs",
        },
        "generation": {
            "answer": {
                "status": "answered",
                "answer": "Identify emergency signs and treat immediately.",
                "reason": "S1 lists the emergency signs.",
                "citations": ["S1"],
            }
        },
        "context": {
            "status": "ready",
            "context_text": '{"label":"S1","text":"fever and inability to feed"}',
            "budget": {"used": 48},
            "citation_map": {"S1": {"chunk_id": "chunk_a"}},
            "evidence_groups": [
                {
                    "label": "S1",
                    "chunk_id": "chunk_a",
                    "document_id": "doc_a",
                    "origin": "direct",
                    "seed_chunk_id": None,
                    "source_passages": [{"passage_id": "passage_a", "text": "fever and inability to feed"}],
                }
            ],
            "excluded_evidence": [],
            "diagnostics": {"duplicate_passages_removed": 0},
        },
    }
    second = {
        "record_key": "Q_S1:2",
        "pipeline_status": "answered",
        "question_record": {"id": 2, "question": "Second question?", "answer": "Second GT."},
        "generation": {"answer": {"status": "answered", "answer": "Second generated.", "reason": "S1", "citations": ["S1"]}},
        "context": {
            "status": "ready",
            "context_text": '{"label":"S1","text":"sick infant priority"}',
            "evidence_groups": [{"label": "S1", "chunk_id": "chunk_b", "source_passages": [{"passage_id": "passage_b", "text": "sick infant"}]}],
            "citation_map": {"S1": {"chunk_id": "chunk_b"}},
        },
    }
    contexts_by_key = {}
    compact_first = write_record_context(tmp_path, first, contexts_by_key)
    compact_second = write_record_context(tmp_path, second, contexts_by_key)
    context_bundle = json.loads((tmp_path / CONTEXTS_FILENAME).read_text(encoding="utf-8"))
    results_path = write_results(tmp_path, [compact_first, compact_second])
    results = json.loads(results_path.read_text(encoding="utf-8"))

    assert context_bundle["schema"] == "bulk-answer-contexts/v1"
    assert set(context_bundle["contexts"]) == {"Q_S1:1", "Q_S1:2"}
    assert context_bundle["contexts"]["Q_S1:1"]["context_text"] == first["context"]["context_text"]
    assert context_bundle["contexts"]["Q_S1:2"]["evidence_groups"][0]["source_passages"][0]["text"] == "sick infant"
    assert compact_first["context_path"] == CONTEXTS_FILENAME
    assert "context_text" not in compact_first["context"]
    assert load_contexts(tmp_path)["Q_S1:2"]["context_text"] == second["context"]["context_text"]
    assert load_record_context(tmp_path, compact_first)["context_text"] == first["context"]["context_text"]

    row = results["results"][0]
    assert results_path.name == RESULTS_FILENAME
    assert row["question"] == "Emergency triage signs?"
    assert row["gt_answer"] == "Treat emergency signs immediately."
    assert row["generated_answer"] == "Identify emergency signs and treat immediately."
    assert row["context_id"] == "Q_S1:1"
    assert row["chunk_ids"] == ["chunk_a"]
    assert row["error"] is None
    assert review_row(compact_second)["gt_answer"] == "Second GT."


def test_pipeline_error_recorded_on_failed_generation():
    from mobile_rag.bulk_answer_generation import pipeline_error, review_row

    generation = {
        "status": "invalid_response",
        "reason": "Response schema or citation validation failed",
        "error": {
            "status": "invalid_response",
            "reason": "Response schema or citation validation failed",
            "type": "ValidationError",
            "message": "citations: Unknown citation label",
        },
    }
    error = pipeline_error(generation)
    assert error["status"] == "invalid_response"
    assert "Unknown citation label" in error["message"]
    row = review_row({"record_key": "Q_S1:1", "pipeline_status": "invalid_response", "error": error})
    assert row["error"]["type"] == "ValidationError"

