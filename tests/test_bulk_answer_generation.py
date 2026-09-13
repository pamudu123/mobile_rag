from test_retrieval import bundle  # noqa: F401

from mobile_rag.answer_generation import GenerationConfig
from mobile_rag.bulk_answer_generation import benchmark_identity, process_question, select_questions
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
    assert record["retrieval"]["hits"] and record["context"]["status"] == "ready"


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
