"""Pure per-question bulk generation logic; artifact saving belongs to the caller."""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mobile_rag.answer_generation import GenerationConfig, generate_answer
from mobile_rag.context_preparation import ContextBudget, prepare_context
from mobile_rag.retrieval_hybrid import HybridRetriever, RetrievalConfig

CONTEXTS_FILENAME = "contexts.json"
RESULTS_FILENAME = "results.json"


def benchmark_identity(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    questions = data.get("questions")
    if not isinstance(questions, list):
        raise TypeError("Question file must contain a questions list")
    required = {"id", "question"}
    for position, row in enumerate(questions):
        if not isinstance(row, dict) or not required <= row.keys() or not isinstance(row["question"], str):
            raise ValueError(f"Invalid question row at position {position}")
    dataset = path.stem
    keys = [f"{dataset}:{row['id']}" for row in questions]
    if len(keys) != len(set(keys)):
        raise ValueError("Question IDs must be unique within the dataset")
    return {
        "dataset": dataset,
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "question_count": len(questions),
        "metadata": data.get("metadata"),
        "questions": questions,
    }


def select_questions(questions: list[dict[str, Any]], number: int | None) -> list[dict[str, Any]]:
    """Select the first N rows; None means every row."""
    if number is not None and (type(number) is not int or number <= 0):
        raise ValueError("number must be a positive integer or None")
    return questions[:] if number is None else questions[:number]


def _write_pretty_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def context_index(context: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep labels and source IDs in the checkpoint; passage text lives in the sidecar JSON."""
    if context is None:
        return None
    return {
        "status": context.get("status"),
        "budget": context.get("budget"),
        "index_identity": context.get("index_identity"),
        "bundle_identity": context.get("bundle_identity"),
        "citation_labels": list((context.get("citation_map") or {}).keys()),
        "evidence_groups": [
            {
                "label": group.get("label"),
                "chunk_id": group.get("chunk_id"),
                "document_id": group.get("document_id"),
                "origin": group.get("origin"),
                "seed_chunk_id": group.get("seed_chunk_id"),
                "source_passage_ids": [passage.get("passage_id") for passage in group.get("source_passages") or []],
            }
            for group in context.get("evidence_groups") or []
        ],
        "excluded_evidence": context.get("excluded_evidence"),
        "diagnostics": context.get("diagnostics"),
    }


def load_contexts(run_dir: Path) -> dict[str, Any]:
    """Load the combined context file, keyed by record key."""
    path = run_dir / CONTEXTS_FILENAME
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("contexts"), dict):
        return dict(data["contexts"])
    if isinstance(data, dict):
        return data
    raise ValueError("contexts.json must be an object keyed by record_key")


def write_contexts(run_dir: Path, contexts_by_key: dict[str, Any]) -> None:
    _write_pretty_json(
        run_dir / CONTEXTS_FILENAME,
        {"schema": "bulk-answer-contexts/v1", "contexts": contexts_by_key},
    )


def write_record_context(
    run_dir: Path,
    record: dict[str, Any],
    contexts_by_key: dict[str, Any],
) -> dict[str, Any]:
    """Upsert this question's context into `contexts.json` and return a compact checkpoint record."""
    compact = dict(record)
    context = record.get("context")
    if not isinstance(context, dict):
        return compact
    record_key = record["record_key"]
    contexts_by_key[record_key] = context
    write_contexts(run_dir, contexts_by_key)
    compact["context_path"] = CONTEXTS_FILENAME
    compact["context_key"] = record_key
    compact["context"] = context_index(context)
    return compact


def load_record_context(
    run_dir: Path,
    record: dict[str, Any],
    contexts_by_key: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Load context from the combined file, an older sidecar path, or an inline package."""
    key = record.get("context_key") or record.get("record_key")
    if contexts_by_key and key in contexts_by_key:
        return contexts_by_key[key]
    relative = record.get("context_path")
    if relative in {None, CONTEXTS_FILENAME}:
        bundle = load_contexts(run_dir)
        if key in bundle:
            return bundle[key]
    if relative and relative != CONTEXTS_FILENAME:
        path = run_dir / relative
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    context = record.get("context")
    return context if isinstance(context, dict) and "context_text" in context else None


def review_row(record: dict[str, Any]) -> dict[str, Any]:
    """Compact review fields: question, generated answer, ground-truth answer, and context IDs."""
    row = record.get("question_record") or {}
    generated = record.get("generation") or {}
    answer = generated.get("answer") or {}
    context = record.get("context") or {}
    groups = context.get("evidence_groups") or []
    labels = context.get("citation_labels")
    if labels is None:
        labels = list((context.get("citation_map") or {}).keys())
    return {
        "record_key": record.get("record_key"),
        "question_id": row.get("id"),
        "category": row.get("category"),
        "topic": row.get("topic"),
        "question": row.get("question"),
        "gt_answer": row.get("answer"),
        "source_of_truth": row.get("source_of_truth"),
        "generated_answer": answer.get("answer"),
        "answer_status": answer.get("status"),
        "generated_reason": answer.get("reason"),
        "citations": answer.get("citations"),
        "context_id": record.get("context_key") or record.get("record_key"),
        "context_labels": labels,
        "chunk_ids": [group.get("chunk_id") for group in groups],
        "pipeline_status": record.get("pipeline_status"),
    }


def write_results(run_dir: Path, records: list[dict[str, Any]]) -> Path:
    path = run_dir / RESULTS_FILENAME
    _write_pretty_json(path, {"schema": "bulk-answer-results/v1", "results": [review_row(record) for record in records]})
    return path


def process_question(
    row: dict[str, Any],
    *,
    dataset: str,
    benchmark_sha256: str,
    index_dir: Path,
    live: bool,
    generation_config: GenerationConfig,
    context_budget: ContextBudget,
    retrieval_config: RetrievalConfig | None = None,
) -> dict[str, Any]:
    """Run one isolated retrieval-to-generation pipeline without writing files."""
    started = datetime.now(UTC).isoformat()
    start = time.perf_counter()
    record: dict[str, Any] = {
        "record_schema": "bulk-answer/v1",
        "record_key": f"{dataset}:{row['id']}",
        "dataset": dataset,
        "benchmark_sha256": benchmark_sha256,
        "question_record": dict(row),
        "started_at_utc": started,
        "live_requested": live,
        "retrieval": None,
        "context_expansion": None,
        "context": None,
        "generation": None,
        "pipeline_status": "running",
    }
    try:
        with HybridRetriever(index_dir, retrieval_config) as retriever:
            retrieval = retriever.search(row["question"])
            expansion = retriever.expand(retrieval)
            context = prepare_context(retriever, retrieval, expansion, context_budget)
        generation = generate_answer(context, config=generation_config, live=live)
        record.update(
            retrieval=retrieval,
            context_expansion=expansion,
            context=context,
            generation=generation,
            pipeline_status=generation["status"],
            index_identity=retrieval.get("index_identity"),
            bundle_identity=retrieval.get("bundle_identity"),
        )
    except Exception as exc:  # noqa: BLE001 - retain a record for every unexpected worker failure.
        record.update(
            pipeline_status="worker_error",
            error={"type": type(exc).__name__, "message": str(exc)[:1000]},
        )
    record["completed_at_utc"] = datetime.now(UTC).isoformat()
    record["pipeline_seconds"] = time.perf_counter() - start
    return record
