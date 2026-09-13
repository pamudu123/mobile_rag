"""Run lexical retrieval comparison without reading benchmark answers."""

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mobile_rag.retrieval import Retriever, build_index, digest, latest_bundle, write_json
from mobile_rag.retrieval_enhanced import build_enhanced
from mobile_rag.retrieval_hybrid import HybridRetriever, RetrievalConfig, build_dense


def run(bundle: Path | None = None, *, baseline_output_root: Path, output_root: Path,
        enable_bm25=True, enable_embeddings=True):
    config = RetrievalConfig(enable_bm25, enable_embeddings)
    config.validate()
    baseline = build_index(bundle or latest_bundle(ROOT), baseline_output_root)
    out = build_enhanced(baseline, output_root)
    if enable_embeddings:
        out = build_dense(out, output_root)
    queries = [
        "What should I remember about bubble CPAP?",
        "severe malnutrition",
        "oxygen therapy",
        "unfindablewordxyz",
    ]
    for name in ("Q_S1", "Q_S2"):
        data = json.loads((ROOT / f"data/questions/{name}.json").read_text(encoding="utf-8"))
        queries.extend(row["question"] for row in data["questions"])
    examples, timings = [], {"baseline": [], "enhanced": []}
    hashes = {n: digest(out / n) for n in ("retrieval.sqlite", "passage.sqlite")}
    with Retriever(out) as base, HybridRetriever(out, config) as enhanced:
        for question in queries:
            a, b = base.search(question), enhanced.search(question)
            timings["baseline"].append(a["search_seconds"] * 1000)
            timings["enhanced"].append(b["search_seconds"] * 1000)
            examples.append(
                {
                    "question": question,
                    "baseline_ids": [h["chunk"]["chunk_id"] for h in a["hits"]],
                    "enhanced_ids": [h["chunk"]["chunk_id"] for h in b["hits"]],
                    "branches": b.get("branches", {}),
                    "status": b["status"],
                }
            )
        sample = enhanced.search(queries[0])
        write_json(out / "example_evidence.json", {"result": sample, "context": enhanced.expand(sample)})
        ablations = {}
        for name, option in (("bm25_only", RetrievalConfig(True, False)),
                             ("embeddings_only", RetrievalConfig(False, True))):
            if option.enable_embeddings and not enable_embeddings:
                continue
            with HybridRetriever(out, option) as alternative:
                ablations[name] = [h["chunk"]["chunk_id"] for h in alternative.search(queries[0])["hits"]]
        write_json(out / "sample_ablations.json", ablations)
    assert all(digest(out / n) == h for n, h in hashes.items())
    summary = {
        "queries": len(queries),
        "retrieval_config": {"enable_bm25": enable_bm25, "enable_embeddings": enable_embeddings},
        "changed_top5": sum(e["baseline_ids"] != e["enhanced_ids"] for e in examples),
        "clinical_accuracy": "not_measured",
        "read_only_hashes_unchanged": True,
        "database_bytes": sum((out / n).stat().st_size for n in hashes),
        "timings_ms": {
            name: {"median": statistics.median(v), "p95": sorted(v)[round((len(v) - 1) * 0.95)]}
            for name, v in timings.items()
        },
    }
    write_json(out / "comparison.json", examples)
    write_json(out / "summary.json", summary)
    print(json.dumps({"output": str(out), **summary}, indent=2))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--baseline-output-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--bm25", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--embeddings", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    run(args.bundle, baseline_output_root=args.baseline_output_root, output_root=args.output_root,
        enable_bm25=args.bm25, enable_embeddings=args.embeddings)
