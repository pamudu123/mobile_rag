"""Bulk answer generation as a runnable script. Edit the hardcoded inputs below."""

from __future__ import annotations

import csv
import json
import os
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mobile_rag.answer_generation import GenerationConfig, PROMPT_SHA256, PROMPT_VERSION, generation_identity
from mobile_rag.bulk_answer_generation import (
    RUNTIME_SHA256,
    benchmark_identity,
    load_contexts,
    process_question,
    select_questions,
    validate_checkpoint,
    validate_resume,
    write_record_context,
    write_results,
)
from mobile_rag.context_preparation import ContextBudget
from mobile_rag.environment import openrouter_api_key
from mobile_rag.retrieval import digest, new_run_dir, write_json
from mobile_rag.retrieval_hybrid import HybridRetriever, RetrievalConfig, latest_index

# --- Hardcoded inputs ---
QUESTION_PATH = ROOT / "data/questions/Q_S1.json"
INDEX_DIR = ROOT / "artifacts/03_retrieval_enhanced/20260913_154703"
OUTPUT_ROOT = ROOT / "artifacts/05_2_bulk_answer_generation"
RESUME_RUN_DIR = None

NUMBER_OF_QUESTIONS = None
LIVE = True
MAX_WORKERS = 4
ENABLE_BM25 = True
ENABLE_EMBEDDINGS = True
QUERY_SOURCE = "question"
MAX_OUTPUT_TOKENS = 4096 * 2
TIMEOUT_SECONDS = 120
TOTAL_CHARS = 40000
INSTRUCTION_RESERVE = 7000
ANSWER_RESERVE = 4000


def _resolve_index(config: RetrievalConfig) -> Path:
    path = Path(INDEX_DIR) if INDEX_DIR is not None else latest_index(ROOT, config)
    path = path.resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Index directory does not exist: {path}")
    return path


def main() -> dict:
    if type(MAX_WORKERS) is not int or not 1 <= MAX_WORKERS <= 16:
        raise ValueError("MAX_WORKERS must be between 1 and 16")

    retrieval_config = RetrievalConfig(ENABLE_BM25, ENABLE_EMBEDDINGS)
    retrieval_config.validate()
    generation_config = GenerationConfig(max_output_tokens=MAX_OUTPUT_TOKENS, timeout_seconds=TIMEOUT_SECONDS)
    context_budget = ContextBudget(
        total_chars=TOTAL_CHARS,
        instruction_reserve=INSTRUCTION_RESERVE,
        answer_reserve=ANSWER_RESERVE,
    )
    index_dir = _resolve_index(retrieval_config)
    question_path = Path(QUESTION_PATH).resolve()

    print({
        "question_path": str(question_path),
        "index": str(index_dir),
        "output_root": str(Path(OUTPUT_ROOT).resolve()),
        "number_of_questions": NUMBER_OF_QUESTIONS,
        "live": LIVE,
        "workers": MAX_WORKERS,
        "api_key_available": bool(openrouter_api_key()),
    })

    benchmark = benchmark_identity(question_path)
    selected_questions = select_questions(benchmark["questions"], NUMBER_OF_QUESTIONS)
    if LIVE and not openrouter_api_key():
        raise RuntimeError("LIVE=True requires OPENROUTER_API_KEY; no requests were started.")

    with HybridRetriever(index_dir, retrieval_config):
        pass

    run_config = {
        "retrieval_config": asdict(retrieval_config),
        "dense_manifest_sha256": digest(index_dir / "dense_manifest.json") if ENABLE_EMBEDDINGS else None,
        "run_schema": "bulk-answer-run/v1",
        "dataset": benchmark["dataset"],
        "question_path": benchmark["path"],
        "benchmark_sha256": benchmark["sha256"],
        "available_question_count": benchmark["question_count"],
        "selected_question_count": len(selected_questions),
        "number_of_questions": NUMBER_OF_QUESTIONS,
        "index_dir": str(index_dir),
        "retrieval_database_sha256": digest(index_dir / "retrieval.sqlite"),
        "passage_database_sha256": digest(index_dir / "passage.sqlite"),
        "enhancement_manifest_sha256": digest(index_dir / "enhancement_manifest.json"),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": PROMPT_SHA256,
        "generation_identity": generation_identity(generation_config),
        "runtime_sha256": RUNTIME_SHA256,
        "query_source": QUERY_SOURCE,
        "generation_config": asdict(generation_config),
        "context_budget": asdict(context_budget),
        "live": LIVE,
        "max_workers": MAX_WORKERS,
    }
    print({
        "dataset": benchmark["dataset"],
        "available": benchmark["question_count"],
        "selected": len(selected_questions),
        "benchmark_sha256": benchmark["sha256"],
    })

    if RESUME_RUN_DIR is None:
        run_dir = new_run_dir(Path(OUTPUT_ROOT))
        write_json(run_dir / "run_manifest.json", {**run_config, "created_at_utc": datetime.now(UTC).isoformat()})
    else:
        run_dir = Path(RESUME_RUN_DIR).resolve()
        saved_config = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        validate_resume(saved_config, run_config)

    records_path = run_dir / "records.jsonl"
    contexts_path = run_dir / "contexts.json"
    print("Save folder:", run_dir)

    records_by_key = {}
    if records_path.exists():
        with records_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("dataset") != benchmark["dataset"] or record.get("benchmark_sha256") != benchmark["sha256"]:
                    raise RuntimeError(f"Checkpoint identity mismatch on line {line_number}")
                validate_checkpoint(record, run_config)
                key = record["record_key"]
                if key in records_by_key:
                    raise RuntimeError(f"Duplicate checkpoint record: {key}")
                records_by_key[key] = record

    contexts_by_key = load_contexts(run_dir)
    pending = [
        row for row in selected_questions
        if f"{benchmark['dataset']}:{row['id']}" not in records_by_key
    ]
    print({"already_completed": len(records_by_key), "pending": len(pending), "saved_contexts": len(contexts_by_key)})

    batch_started = time.perf_counter()
    if pending:
        with (
            records_path.open("a", encoding="utf-8", newline="\n") as checkpoint,
            ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool,
        ):
            futures = {
                pool.submit(
                    process_question,
                    row,
                    dataset=benchmark["dataset"],
                    benchmark_sha256=benchmark["sha256"],
                    index_dir=index_dir,
                    live=LIVE,
                    generation_config=generation_config,
                    context_budget=context_budget,
                    retrieval_config=retrieval_config,
                    query_source=QUERY_SOURCE,
                ): row
                for row in pending
            }
            for future in as_completed(futures):
                record = future.result()
                compact = write_record_context(run_dir, record, contexts_by_key)
                checkpoint.write(json.dumps(compact, ensure_ascii=True, sort_keys=True) + "\n")
                checkpoint.flush()
                os.fsync(checkpoint.fileno())
                records_by_key[compact["record_key"]] = compact
                status = compact["pipeline_status"]
                error = compact.get("error") or {}
                detail = error.get("message") or error.get("reason")
                suffix = f" — {detail}" if detail else ""
                print(
                    f"[{len(records_by_key)}/{len(selected_questions)}] "
                    f"{compact['record_key']}: {status}{suffix}"
                )

    batch_seconds = time.perf_counter() - batch_started
    print({"newly_processed": len(pending), "batch_seconds": batch_seconds, "save_folder": str(run_dir)})

    ordered_keys = [f"{benchmark['dataset']}:{row['id']}" for row in selected_questions]
    ordered_records = [records_by_key[key] for key in ordered_keys if key in records_by_key]
    overview = []
    for record in ordered_records:
        row = record["question_record"]
        generated = record.get("generation") or {}
        answer = generated.get("answer") or {}
        context = record.get("context") or {}
        retrieval = record.get("retrieval") or {}
        usage = generated.get("usage") or {}
        overview.append({
            "record_key": record["record_key"],
            "question_id": row.get("id"),
            "category": row.get("category"),
            "topic": row.get("topic"),
            "question": row.get("question"),
            "reference_answer": row.get("answer"),
            "source_of_truth": row.get("source_of_truth"),
            "pipeline_status": record["pipeline_status"],
            "answer_status": answer.get("status"),
            "generated_answer": answer.get("answer"),
            "generated_reason": answer.get("reason"),
            "citations": json.dumps(answer.get("citations"), ensure_ascii=False),
            "retrieval_status": retrieval.get("status"),
            "retrieval_hits": len(retrieval.get("hits", [])),
            "context_status": context.get("status"),
            "context_groups": len(context.get("evidence_groups", [])),
            "context_characters": (context.get("budget") or {}).get("used"),
            "provider": generated.get("provider"),
            "returned_model": generated.get("returned_model"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "generation_latency_ms": generated.get("latency_ms"),
            "pipeline_seconds": record.get("pipeline_seconds"),
            "error": json.dumps(record.get("error"), ensure_ascii=False) if record.get("error") else None,
        })

    if overview:
        with (run_dir / "results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(overview[0]))
            writer.writeheader()
            writer.writerows(overview)
    write_results(run_dir, ordered_records)

    status_counts = Counter(record["pipeline_status"] for record in ordered_records)
    timings = [
        record["pipeline_seconds"] for record in ordered_records
        if isinstance(record.get("pipeline_seconds"), (int, float))
    ]
    missing_keys = [key for key in ordered_keys if key not in records_by_key]
    summary = {
        "run_schema": "bulk-answer-summary/v1",
        "run_dir": str(run_dir),
        "dataset": benchmark["dataset"],
        "benchmark_sha256": benchmark["sha256"],
        "available_questions": benchmark["question_count"],
        "selected_questions": len(selected_questions),
        "saved_records": len(ordered_records),
        "complete": not missing_keys,
        "missing_record_keys": missing_keys,
        "pipeline_status_counts": dict(sorted(status_counts.items())),
        "live": LIVE,
        "max_workers": MAX_WORKERS,
        "last_session_seconds": batch_seconds,
        "pipeline_seconds": {
            "median": statistics.median(timings) if timings else None,
            "p95": sorted(timings)[round((len(timings) - 1) * 0.95)] if timings else None,
            "samples": len(timings),
        },
        "updated_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(run_dir / "summary.json", summary)
    print("Save folder:", run_dir)
    print({
        "contexts": str(contexts_path.resolve()),
        "results_json": str((run_dir / "results.json").resolve()),
        "results_csv": str((run_dir / "results.csv").resolve()),
        "records": str(records_path.resolve()),
        "summary": str((run_dir / "summary.json").resolve()),
    })
    print(summary)
    return summary


if __name__ == "__main__":
    main()
