"""Offline metrics over saved records. No model calls or inferred clinical labels."""

import json
from collections import Counter, defaultdict
from pathlib import Path

from mobile_rag.bulk_answer_generation import load_contexts, load_record_context


def evaluate_records(records, *, annotations=None):
    """Optional annotations map keys to exhaustive relevant_chunk_ids for that question."""
    keys = [row["record_key"] for row in records]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate record keys")
    annotations = annotations or {}
    cohorts = defaultdict(list)
    for record in records:
        generation = record.get("generation") or {}
        identity = {
            "generation": generation.get("generation_identity") or {
                "model": generation.get("model"), "prompt_version": generation.get("prompt_version"),
            },
            "runtime_sha256": record.get("runtime_sha256"), "query_source": record.get("query_source"),
            "retrieval_variant": (record.get("retrieval") or {}).get("retrieval_variant"),
            "retrieval_config": (record.get("retrieval") or {}).get("retrieval_config"),
            "index_identity": record.get("index_identity"),
        }
        cohorts[json.dumps(identity, sort_keys=True)].append(record["record_key"])
    rows = []
    for record in records:
        generation = record.get("generation") or {}
        answer = generation.get("answer") or {}
        retrieval = record.get("retrieval") or {}
        context = record.get("context") or {}
        status = record["pipeline_status"]
        origin = generation.get("abstention_origin")
        if status == "insufficient_evidence" and origin is None:
            origin = "model" if answer.get("status") == "insufficient_evidence" else "context"
        row = {
            "record_key": record["record_key"], "pipeline_status": status,
            "answer_status": answer.get("status"), "abstention_origin": origin,
            "category": (record.get("question_record") or {}).get("category"),
            "topic": (record.get("question_record") or {}).get("topic"),
            "retrieval_hit_count": len(retrieval.get("hits", [])),
            "packed_group_count": len(context.get("evidence_groups", [])),
            "gold_evidence_metrics": None,
        }
        annotation = annotations.get(record["record_key"])
        if annotation is not None:
            ids = annotation["relevant_chunk_ids"]
            if not isinstance(ids, list) or any(not isinstance(cid, str) for cid in ids):
                raise ValueError("relevant_chunk_ids must be a list of strings")
            gold = set(ids)
            retrieved = {hit["chunk"]["chunk_id"] for hit in retrieval.get("hits", [])}
            packed = {group["chunk_id"] for group in context.get("evidence_groups", [])}
            row["gold_evidence_metrics"] = {
                "retrieval_hit": bool(gold & retrieved),
                "retrieval_recall": len(gold & retrieved) / len(gold) if gold else None,
                "packed_precision": len(gold & packed) / len(packed) if packed else None,
                "packed_recall": len(gold & packed) / len(gold) if gold else None,
            }
        rows.append(row)
    unanswerable = [row for row in rows if row["category"] == "Unanswerable"]
    return {
        "schema": "saved-run-evaluation/v1", "records": len(rows),
        "pipeline_status_counts": dict(Counter(row["pipeline_status"] for row in rows)),
        "categories": dict(Counter(row["category"] for row in rows)),
        "unique_topics": len({row["topic"] for row in rows if row["topic"] is not None}),
        "cohorts": [{"identity": json.loads(identity), "record_keys": keys} for identity, keys in cohorts.items()],
        "unanswerable": {
            "count": len(unanswerable),
            "abstentions": sum(row["pipeline_status"] == "insufficient_evidence" for row in unanswerable),
            "answered": sum(row["pipeline_status"] == "answered" for row in unanswerable),
            "technical_or_unexecuted": sum(
                row["pipeline_status"] not in {"answered", "insufficient_evidence"} for row in unanswerable
            ),
        },
        "limitations": ["Clinical correctness and entailment are not inferred from reference string overlap.",
                        "Gold metrics require exhaustive, index-specific relevant_chunk_ids annotations."],
        "questions": rows,
    }


def evaluate_run(run_dir: Path, annotations=None):
    records = [json.loads(line) for line in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
               if line.strip()]
    contexts = load_contexts(run_dir)
    for record in records:
        context = load_record_context(run_dir, record, contexts)
        if context is not None:
            record["context"] = context
    return evaluate_records(records, annotations=annotations)
