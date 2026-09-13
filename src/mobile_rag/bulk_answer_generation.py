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
